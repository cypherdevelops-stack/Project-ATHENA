from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class StrategyCandidate:
    """Unified representation of a strategy candidate from any engine."""
    strategy: str  # "SCALPING" or "DAY_TRADING"
    direction: str  # "BUY" or "SELL"
    confidence: float  # 0-100 score
    status: str  # "READY", "DEVELOPING", "BLOCKED", "OBSERVE"
    evidence: dict  # Strategy-specific evidence
    decision_state: str  # "RISK_APPROVED", "CANDIDATE", "WAITING", "OBSERVE"
    entry_zone: Optional[dict] = None
    stop_loss: Optional[float] = None
    take_profit1: Optional[float] = None
    take_profit2: Optional[float] = None
    timeframe: str = "M1"  # Primary timeframe
    priority: int = 0  # Higher = more important


@dataclass
class PortfolioState:
    """Portfolio-level state shared by all strategies."""
    regime: str  # "TRENDING_BULLISH", "TRENDING_BEARISH", "VOLATILE", "RANGING"
    risk_available: bool
    daily_drawdown_pct: float
    account_equity: float
    news_locked: bool
    correlation_allowed: bool
    execution_allowed: bool
    market_open: bool
    news_sentiment: dict
    momentum_map: dict


class StrategyOrchestrator:
    """
    Central coordinator that manages the relationship between strategy engines
    without creating direct dependencies between them.

    Architectural principles:
    1. Shared intelligence, separate execution logic
    2. Every strategy interprets the shared ATHENA market context independently
    3. Strategy candidates flow into the orchestrator, never between engines
    4. Portfolio governance layer arbitrates between candidates
    5. One unified output stream
    """

    def __init__(self):
        self._last_regime: Optional[str] = None
        self._scalping_candidate: Optional[StrategyCandidate] = None
        self._day_candidate: Optional[StrategyCandidate] = None
        self._portfolio_state: Optional[PortfolioState] = None

    def set_portfolio_state(self, regime: str, state: dict, momentum_map: dict | None = None) -> None:
        """Set the shared portfolio context available to all strategies."""
        self._last_regime = regime
        self._portfolio_state = PortfolioState(
            regime=regime,
            risk_available=state.get('risk_allowed', True),
            daily_drawdown_pct=state.get('daily_drawdown_pct', 0),
            account_equity=state.get('account_equity', 0),
            news_locked=state.get('news_locked', False),
            correlation_allowed=state.get('correlation_allowed', True),
            execution_allowed=state.get('execution_allowed', True),
            market_open=state.get('market_open', True),
            news_sentiment=state.get('news_sentiment', {}),
            momentum_map=momentum_map or state.get('momentumMap', {}),
        )

    def ingest_scalping_candidate(self, candidate: dict, ml_probability: float = 0.0) -> None:
        """
        Scalping engine feeds its candidate.

        Scalping provides:
        - M5/M1 microstructure evidence
        - Entry zones and POI retests
        - XGBoost advisory probability
        """
        if not candidate or candidate.get('decisionState') == 'OBSERVE':
            self._scalping_candidate = None
            return

        direction = candidate.get('direction')
        entry_zone = candidate.get('entryZone')
        setup = candidate.get('setup', {})

        self._scalping_candidate = StrategyCandidate(
            strategy="SCALPING",
            direction=direction,
            confidence=candidate.get('score', 0),
            status="READY" if setup.get('active') else "WAITING",
            evidence={
                'setup_state': setup.get('state'),
                'missing_requirements': setup.get('missing', []),
                'gates': candidate.get('gates', []),
                'ml_probability': ml_probability,
                'htf_bias': self._portfolio_state.regime if self._portfolio_state else "UNKNOWN",
            },
            decision_state=candidate.get('decisionState', 'OBSERVE'),
            entry_zone=entry_zone,
            timeframe="M1",
            priority=2 if setup.get('active') else 1,
        )

    def ingest_day_trading_candidate(self, candidate: dict) -> None:
        """
        Day trading engine feeds its candidate.

        Day trading provides:
        - HTF bias and structural context
        - Pullback detection
        - Directional probability for longer horizon
        """
        if not candidate or candidate.get('decisionState') == 'OBSERVE':
            self._day_candidate = None
            return

        direction = candidate.get('direction')
        confidence = candidate.get('score', 0)

        self._day_candidate = StrategyCandidate(
            strategy="DAY_TRADING",
            direction=direction,
            confidence=confidence,
            status=candidate.get('status', 'DEVELOPING'),
            evidence={
                'setup_state': candidate.get('setup_state'),
                'timeframe_structure': candidate.get('htf_structure'),
                'pullback_detected': candidate.get('pullback_detected', False),
                'poi_confirmation': candidate.get('poi_confirmation'),
            },
            decision_state=candidate.get('decisionState', 'OBSERVE'),
            timeframe="H1",
            priority=3,  # Lower priority (longer horizon, less frequent)
        )

    def orchestrate_execution(self) -> dict:
        """
        Produce unified execution orchestration output.
        
        Returns the single source of truth for what ATHENA is seeing
        and what should execute next.
        """
        if not self._portfolio_state:
            return {
                'status': 'OBSERVE',
                'reason': 'Portfolio state not initialized',
                'market_regime': 'UNKNOWN',
                'day_engine': {'status': 'OBSERVE'},
                'scalping_engine': {'status': 'OBSERVE'},
                'portfolio': {'risk_available': False},
                'decision': 'WAIT',
            }

        # Core orchestration logic:
        # 1. Can execution proceed at portfolio level?
        portfolio_allows_execution = (
            self._portfolio_state.risk_available
            and self._portfolio_state.market_open
            and not self._portfolio_state.news_locked
            and self._portfolio_state.execution_allowed
        )

        # 2. Which strategy has the stronger candidate?
        candidates = []
        if self._scalping_candidate and self._scalping_candidate.status == "READY":
            candidates.append(self._scalping_candidate)
        if self._day_candidate and self._day_candidate.status in {"READY", "DEVELOPING"}:
            candidates.append(self._day_candidate)

        # 3. Sort by priority and confidence
        candidates.sort(key=lambda c: (c.priority, c.confidence), reverse=True)

        # 4. Determine execution decision
        recommended_strategy = None
        execution_decision = "OBSERVE"
        execution_reason = "No ready candidates"

        if candidates and portfolio_allows_execution:
            recommended_strategy = candidates[0]
            if recommended_strategy.strategy == "SCALPING" and recommended_strategy.status == "READY":
                execution_decision = "SCALP_LONG_APPROVED" if recommended_strategy.direction == "BUY" else "SCALP_SHORT_APPROVED"
                execution_reason = f"Microstructure confirmed, ML probability: {recommended_strategy.evidence.get('ml_probability', 0):.0%}"
            elif recommended_strategy.strategy == "DAY_TRADING":
                execution_decision = f"DAY_{recommended_strategy.direction}_DEVELOPING"
                execution_reason = "HTF pullback forming"
        elif not portfolio_allows_execution:
            if not self._portfolio_state.market_open:
                execution_reason = "Market closed"
            elif self._portfolio_state.news_locked:
                execution_reason = "News event locked"
            elif not self._portfolio_state.execution_allowed:
                execution_reason = "Execution unavailable"
            elif not self._portfolio_state.risk_available:
                execution_reason = "Risk limit reached"

        return {
            'status': execution_decision,
            'reason': execution_reason,
            'market_regime': self._portfolio_state.regime,
            'day_engine': {
                'status': self._day_candidate.status if self._day_candidate else 'OBSERVE',
                'direction': self._day_candidate.direction if self._day_candidate else None,
                'confidence': self._day_candidate.confidence if self._day_candidate else 0,
                'evidence': self._day_candidate.evidence if self._day_candidate else {},
            },
            'scalping_engine': {
                'status': self._scalping_candidate.status if self._scalping_candidate else 'OBSERVE',
                'direction': self._scalping_candidate.direction if self._scalping_candidate else None,
                'confidence': self._scalping_candidate.confidence if self._scalping_candidate else 0,
                'entry_zone': self._scalping_candidate.entry_zone if self._scalping_candidate else None,
                'evidence': self._scalping_candidate.evidence if self._scalping_candidate else {},
            },
            'portfolio': {
                'risk_available': self._portfolio_state.risk_available,
                'daily_drawdown_pct': self._portfolio_state.daily_drawdown_pct,
                'account_equity': self._portfolio_state.account_equity,
            },
            'news': self._portfolio_state.news_sentiment,
            'momentumMap': self._portfolio_state.momentum_map,
            'decision': {
                'strategy': recommended_strategy.strategy if recommended_strategy else None,
                'action': execution_decision,
                'reason': execution_reason,
                'reasonCodes': self._decision_reason_codes(execution_decision, portfolio_allows_execution),
            },
        }

    @staticmethod
    def _decision_reason_codes(decision: str, portfolio_allows_execution: bool) -> list[str]:
        if not portfolio_allows_execution:
            return ['PORTFOLIO_EXECUTION_BLOCKED']
        if decision == 'OBSERVE':
            return ['NO_READY_CANDIDATE']
        if decision.endswith('_DEVELOPING'):
            return ['DAY_SETUP_DEVELOPING']
        return ['ORCHESTRATED_CANDIDATE_SELECTED']

    def get_unified_context(self) -> dict:
        """
        Produce ATHENA market context for each strategy to interpret independently.

        The orchestrator exposes shared facts only; it never forwards one
        strategy's interpretation as another strategy's input.
        """
        if not self._portfolio_state:
            return {}

        return {
            'regime': self._portfolio_state.regime,
            'news_locked': self._portfolio_state.news_locked,
            'market_open': self._portfolio_state.market_open,
            'correlation_allowed': self._portfolio_state.correlation_allowed,
            'execution_allowed': self._portfolio_state.execution_allowed,
            'account_equity': self._portfolio_state.account_equity,
            'daily_drawdown_pct': self._portfolio_state.daily_drawdown_pct,
            'risk_available': self._portfolio_state.risk_available,
            'news_sentiment': self._portfolio_state.news_sentiment,
            'momentumMap': self._portfolio_state.momentum_map,
        }

    def reset(self) -> None:
        """Clear all candidates and state (e.g., on market close or session end)."""
        self._scalping_candidate = None
        self._day_candidate = None
        self._last_regime = None
        self._portfolio_state = None
