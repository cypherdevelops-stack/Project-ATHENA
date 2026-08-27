from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class StrategyRiskState:
    """Risk state tracking for individual strategies."""
    strategy_name: str
    daily_loss_pct: float = 0.0
    loss_streak: int = 0
    consecutive_wins: int = 0
    last_loss_time: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    session_locked: bool = False
    max_daily_loss_pct: float = 2.0
    max_loss_streak: int = 3
    cooldown_minutes: int = 30


class PortfolioGovernor:
    """
    Portfolio-level risk and governance layer sitting ABOVE both strategy engines.
    
    This layer is responsible for:
    1. Account-level risk tracking and enforcement
    2. Strategy state management (not strategy candidate generation)
    3. Position conflict resolution when both engines have candidates
    4. Resource allocation between strategies
    5. Guardian-level safety enforcement
    
    IMPORTANT: This is NOT a strategy in itself. It enforces constraints that both
    strategies must respect, but it doesn't generate trades or favors one strategy over another.
    """

    def __init__(self, *, account, risk_policy: dict | None = None):
        self.account = account
        self.risk_policy = risk_policy or {}

        # Strategy-specific risk states
        self.scalping_risk = StrategyRiskState(
            strategy_name="SCALPING",
            max_daily_loss_pct=self.risk_policy.get('scalping_max_daily_loss_pct', 2.0),
            max_loss_streak=self.risk_policy.get('scalping_max_loss_streak', 3),
            cooldown_minutes=self.risk_policy.get('scalping_cooldown_minutes', 30),
        )
        self.day_trading_risk = StrategyRiskState(
            strategy_name="DAY_TRADING",
            max_daily_loss_pct=self.risk_policy.get('day_trading_max_daily_loss_pct', 3.0),
            max_loss_streak=self.risk_policy.get('day_trading_max_loss_streak', 2),
            cooldown_minutes=self.risk_policy.get('day_trading_cooldown_minutes', 60),
        )

        # Portfolio-level (account-wide) limits
        self.portfolio_max_daily_loss_pct = self.risk_policy.get('portfolio_max_daily_loss_pct', 5.0)
        self.portfolio_daily_loss_pct = 0.0
        self.total_positions_open = 0

    def evaluate_portfolio_state(self, current_equity: float, daily_pl: float = 0.0) -> dict:
        """
        Evaluate if the portfolio can accept new trades from any strategy.
        
        This returns the constraints that both engines must respect.
        """
        daily_loss_pct = (abs(daily_pl) / current_equity * 100) if current_equity > 0 else 0
        self.portfolio_daily_loss_pct = daily_loss_pct
        account_guardian_state = self.account.guardian_state() if self.account else "OK"

        portfolio_allows_execution = (
            account_guardian_state not in {'HALT', 'ACCOUNT_LOCK', 'DAILY_LOCK'}
            and daily_loss_pct < self.portfolio_max_daily_loss_pct
            and self.account.enabled
            and self.account.terminal_connected
            and self.account.trade_allowed
        )

        return {
            'portfolio_allows_execution': portfolio_allows_execution,
            'daily_loss_pct': daily_loss_pct,
            'guardian_state': account_guardian_state,
            'account_equity': current_equity,
            'reason': self._compute_block_reason(
                guardian_state=account_guardian_state,
                daily_loss_pct=daily_loss_pct,
                account_enabled=self.account.enabled if self.account else False,
                terminal_connected=self.account.terminal_connected if self.account else False,
                trade_allowed=self.account.trade_allowed if self.account else False,
            ),
        }

    @staticmethod
    def _compute_block_reason(guardian_state: str, daily_loss_pct: float, 
                               account_enabled: bool, terminal_connected: bool, 
                               trade_allowed: bool) -> str:
        if not account_enabled:
            return "Account disabled"
        if not terminal_connected or not trade_allowed:
            return "Terminal connection lost or trade not allowed"
        if guardian_state == 'HALT':
            return "Guardian halt"
        if guardian_state == 'ACCOUNT_LOCK':
            return "Account locked"
        if guardian_state == 'DAILY_LOCK':
            return "Daily loss limit hit"
        return "OK"

    def update_strategy_risk_state(self, strategy: str, *, win: bool = False, loss_pct: float = 0.0) -> None:
        """
        Update risk state for a specific strategy after a trade closes.
        
        This allows each strategy to have independent risk tracking,
        but they're all constrained by portfolio-level limits.
        """
        risk_state = self.scalping_risk if strategy == "SCALPING" else self.day_trading_risk

        if win:
            risk_state.consecutive_wins += 1
            risk_state.loss_streak = 0
        else:
            risk_state.loss_streak += 1
            risk_state.consecutive_wins = 0
            risk_state.daily_loss_pct += loss_pct
            risk_state.last_loss_time = datetime.now(timezone.utc)

    def get_strategy_risk_state(self, strategy: str) -> StrategyRiskState:
        """Get the current risk state for a strategy."""
        return self.scalping_risk if strategy == "SCALPING" else self.day_trading_risk

    def is_strategy_available(self, strategy: str) -> bool:
        """
        Check if a strategy is available for execution based on its own risk state.
        
        Portfolio-level limits are checked separately in evaluate_portfolio_state().
        """
        risk_state = self.get_strategy_risk_state(strategy)

        # Check daily loss limit for this strategy
        if risk_state.daily_loss_pct >= risk_state.max_daily_loss_pct:
            risk_state.session_locked = True
            return False

        # Check loss streak
        if risk_state.loss_streak >= risk_state.max_loss_streak:
            risk_state.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=risk_state.cooldown_minutes)

        # Check if in cooldown
        if risk_state.cooldown_until and risk_state.cooldown_until > datetime.now(timezone.utc):
            return False

        # Clear cooldown if expired
        if risk_state.cooldown_until and risk_state.cooldown_until <= datetime.now(timezone.utc):
            risk_state.cooldown_until = None

        return True

    def can_scalping_and_day_trading_coexist(self, scalping_candidate: dict | None, 
                                               day_candidate: dict | None) -> bool:
        """
        Determine if both strategies can have active positions simultaneously.
        
        This prevents portfolio conflicts (e.g., scalping short while day trading long on same symbol).
        Returns True if they can safely coexist, False if one must be blocked.
        """
        if not scalping_candidate or not day_candidate:
            return True  # Only one or zero candidates, no conflict

        scalp_direction = scalping_candidate.get('direction')
        day_direction = day_candidate.get('direction')

        # Conflict: opposite directions on same symbol
        if scalp_direction and day_direction and scalp_direction != day_direction:
            return False  # Cannot have scalp long + day short simultaneously

        return True

    def resolve_position_conflict(self, scalping_candidate: dict | None, 
                                    day_candidate: dict | None) -> tuple[str, str]:
        """
        If there's a conflict between scalping and day trading, decide which takes priority.
        
        Returns: (recommended_strategy, reason)
        - "SCALPING": Scalping has priority
        - "DAY_TRADING": Day trading has priority
        - "BOTH": Both can coexist
        - "NEITHER": Neither should execute
        """
        if not scalping_candidate and not day_candidate:
            return "NEITHER", "No candidates from either strategy"

        if not day_candidate:
            return "SCALPING", "Only scalping candidate available"

        if not scalping_candidate:
            return "DAY_TRADING", "Only day trading candidate available"

        # Check if they conflict
        can_coexist = self.can_scalping_and_day_trading_coexist(scalping_candidate, day_candidate)
        if can_coexist:
            return "BOTH", "Strategies can coexist on this symbol"

        # Conflict resolution: prioritize based on strategy state and strength
        scalp_score = scalping_candidate.get('score', 0)
        day_score = day_candidate.get('score', 0)
        scalp_setup_active = scalping_candidate.get('setup', {}).get('active', False)
        day_status = day_candidate.get('decisionState', 'OBSERVE')

        # Scalping ready + setup active takes priority over developing day trade
        if scalp_setup_active and day_status == 'DEVELOPING':
            return "SCALPING", "Scalping setup ready, day trade still developing"

        # Day trade ready takes priority over scalping waiting
        if day_status in {'RISK_APPROVED', 'READY'} and not scalp_setup_active:
            return "DAY_TRADING", "Day trade confirmed, scalping still waiting"

        # Otherwise, score-based
        if scalp_score > day_score:
            return "SCALPING", f"Scalping score higher ({scalp_score} vs {day_score})"
        else:
            return "DAY_TRADING", f"Day trading score higher ({day_score} vs {scalp_score})"

    def reset_daily_state(self) -> None:
        """Reset strategy risk states at start of new trading day."""
        self.scalping_risk.daily_loss_pct = 0.0
        self.scalping_risk.loss_streak = 0
        self.scalping_risk.consecutive_wins = 0
        self.scalping_risk.session_locked = False
        self.scalping_risk.cooldown_until = None

        self.day_trading_risk.daily_loss_pct = 0.0
        self.day_trading_risk.loss_streak = 0
        self.day_trading_risk.consecutive_wins = 0
        self.day_trading_risk.session_locked = False
        self.day_trading_risk.cooldown_until = None

        self.portfolio_daily_loss_pct = 0.0
