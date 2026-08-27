from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Generator

from backend.accounts.models import Account
from backend.execution.models import OrchestrationSnapshot
from backend.execution.portfolio_governor import PortfolioGovernor


@dataclass
class OrchestrationBacktestResult:
    """Result of orchestration backtesting analysis."""
    total_snapshots: int
    date_range: tuple[datetime, datetime]
    
    # Decision metrics
    scalp_approvals: int
    day_trading_develops: int
    observe_decisions: int
    blocked_decisions: int
    
    # Regime breakdown
    regime_distribution: dict[str, int]
    
    # Scalping performance
    avg_scalping_score: float
    scalping_approval_rate: float  # % of time scalping was ready
    scalping_by_regime: dict[str, float]  # approval % by regime
    
    # Day trading performance
    avg_day_trading_score: float
    day_trading_develop_rate: float  # % of time day trading was developing
    day_trading_by_regime: dict[str, float]  # develop % by regime
    
    # Portfolio utilization
    avg_portfolio_drawdown: float
    risk_blocked_rate: float  # % of time risk was not available
    
    # Conflicts
    total_conflicts: int
    conflict_rate: float  # % of snapshots with opposite directions
    
    # Orchestration efficiency
    avg_ml_probability: float
    decision_distribution: dict[str, int]
    
    def summary(self) -> str:
        """Generate summary report."""
        lines = [
            f"\n{'='*70}",
            f"ORCHESTRATION BACKTEST RESULTS",
            f"{'='*70}",
            f"\nDate Range: {self.date_range[0].strftime('%Y-%m-%d %H:%M:%S')} - {self.date_range[1].strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Snapshots: {self.total_snapshots}",
            f"\nDECISIONS",
            f"  Scalp Approvals:    {self.scalp_approvals:6d} ({self.scalping_approval_rate:5.1f}%)",
            f"  Day Trading Dev:    {self.day_trading_develops:6d} ({self.day_trading_develop_rate:5.1f}%)",
            f"  Observe:            {self.observe_decisions:6d} ({100*self.observe_decisions/self.total_snapshots:5.1f}%)",
            f"  Blocked:            {self.blocked_decisions:6d} ({100*self.blocked_decisions/self.total_snapshots:5.1f}%)",
            f"\nREGIME DISTRIBUTION",
        ]
        for regime, count in sorted(self.regime_distribution.items()):
            pct = 100 * count / self.total_snapshots if self.total_snapshots > 0 else 0
            lines.append(f"  {regime:20s}: {count:6d} ({pct:5.1f}%)")
        
        lines.extend([
            f"\nSCALPING ENGINE",
            f"  Avg Score:          {self.avg_scalping_score:6.1f}/100",
            f"  Approval Rate:      {self.scalping_approval_rate:5.1f}%",
            f"  By Regime:",
        ])
        for regime, rate in sorted(self.scalping_by_regime.items()):
            lines.append(f"    {regime:18s}: {rate:5.1f}%")
        
        lines.extend([
            f"\nDAY TRADING ENGINE",
            f"  Avg Score:          {self.avg_day_trading_score:6.1f}/100",
            f"  Develop Rate:       {self.day_trading_develop_rate:5.1f}%",
            f"  By Regime:",
        ])
        for regime, rate in sorted(self.day_trading_by_regime.items()):
            lines.append(f"    {regime:18s}: {rate:5.1f}%")
        
        lines.extend([
            f"\nPORTFOLIO",
            f"  Avg Drawdown:       {self.avg_portfolio_drawdown:6.2f}%",
            f"  Risk Blocked:       {self.risk_blocked_rate:5.1f}%",
            f"\nCONFLICTS",
            f"  Total Conflicts:    {self.total_conflicts:6d}",
            f"  Conflict Rate:      {self.conflict_rate:5.1f}%",
            f"\nML ADVISORY",
            f"  Avg Probability:    {self.avg_ml_probability:5.1f}%",
            f"\nDECISION DISTRIBUTION",
        ])
        for decision, count in sorted(self.decision_distribution.items(), key=lambda x: x[1], reverse=True):
            pct = 100 * count / self.total_snapshots if self.total_snapshots > 0 else 0
            lines.append(f"  {decision:25s}: {count:6d} ({pct:5.1f}%)")
        
        lines.append(f"{'='*70}\n")
        return '\n'.join(lines)


class OrchestratorBacktester:
    """
    Backtest orchestrator performance on historical snapshots.
    
    Usage:
    ```python
    backtester = OrchestratorBacktester(account)
    result = backtester.backtest(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )
    print(result.summary())
    ```
    """
    
    def __init__(self, account: Account):
        self.account = account
    
    def backtest(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        max_snapshots: int | None = None,
    ) -> OrchestrationBacktestResult:
        """
        Run backtest on orchestration snapshots.
        
        Args:
            start_date: Start datetime for backtest window
            end_date: End datetime for backtest window
            max_snapshots: Limit number of snapshots to analyze
        
        Returns:
            OrchestrationBacktestResult with metrics
        """
        # Query snapshots
        query = OrchestrationSnapshot.objects.filter(account=self.account)
        
        if start_date:
            query = query.filter(timestamp__gte=start_date)
        if end_date:
            query = query.filter(timestamp__lte=end_date)
        
        snapshots = list(query.order_by('timestamp')[:max_snapshots] if max_snapshots else query.order_by('timestamp'))
        
        if not snapshots:
            return OrchestrationBacktestResult(
                total_snapshots=0,
                date_range=(None, None),
                scalp_approvals=0,
                day_trading_develops=0,
                observe_decisions=0,
                blocked_decisions=0,
                regime_distribution={},
                avg_scalping_score=0,
                scalping_approval_rate=0,
                scalping_by_regime={},
                avg_day_trading_score=0,
                day_trading_develop_rate=0,
                day_trading_by_regime={},
                avg_portfolio_drawdown=0,
                risk_blocked_rate=0,
                total_conflicts=0,
                conflict_rate=0,
                avg_ml_probability=0,
                decision_distribution={},
            )
        
        # Aggregate metrics
        total = len(snapshots)
        scalp_approvals = sum(1 for s in snapshots if s.decision.startswith('SCALP'))
        day_develops = sum(1 for s in snapshots if s.decision.startswith('DAY'))
        observes = sum(1 for s in snapshots if s.decision == 'OBSERVE')
        blocked = sum(1 for s in snapshots if s.decision == 'BLOCKED')
        
        # Regime distribution
        regime_dist = {}
        for s in snapshots:
            regime = s.regime
            regime_dist[regime] = regime_dist.get(regime, 0) + 1
        
        # Scalping metrics
        avg_scalp_score = sum(s.scalping_score for s in snapshots) / total if total > 0 else 0
        scalp_approval_rate = 100 * scalp_approvals / total if total > 0 else 0
        scalp_by_regime = {}
        for regime in regime_dist.keys():
            regime_snapshots = [s for s in snapshots if s.regime == regime]
            regime_scalp_approvals = sum(1 for s in regime_snapshots if s.decision.startswith('SCALP'))
            scalp_by_regime[regime] = 100 * regime_scalp_approvals / len(regime_snapshots) if regime_snapshots else 0
        
        # Day trading metrics
        avg_day_score = sum(s.day_trading_score for s in snapshots) / total if total > 0 else 0
        day_develop_rate = 100 * day_develops / total if total > 0 else 0
        day_by_regime = {}
        for regime in regime_dist.keys():
            regime_snapshots = [s for s in snapshots if s.regime == regime]
            regime_day_develops = sum(1 for s in regime_snapshots if s.decision.startswith('DAY'))
            day_by_regime[regime] = 100 * regime_day_develops / len(regime_snapshots) if regime_snapshots else 0
        
        # Portfolio metrics
        avg_drawdown = sum(s.daily_drawdown_pct for s in snapshots) / total if total > 0 else 0
        risk_blocked = sum(1 for s in snapshots if not s.risk_available)
        risk_blocked_rate = 100 * risk_blocked / total if total > 0 else 0
        
        # Conflicts (opposite directions)
        conflicts = 0
        for s in snapshots:
            if (s.scalping_direction and s.day_trading_direction and
                s.scalping_direction != s.day_trading_direction):
                conflicts += 1
        conflict_rate = 100 * conflicts / total if total > 0 else 0
        
        # ML probability
        avg_ml_prob = sum(s.ml_probability for s in snapshots) / total if total > 0 else 0
        
        # Decision distribution
        decision_dist = {}
        for s in snapshots:
            decision_dist[s.decision] = decision_dist.get(s.decision, 0) + 1
        
        return OrchestrationBacktestResult(
            total_snapshots=total,
            date_range=(snapshots[0].timestamp, snapshots[-1].timestamp),
            scalp_approvals=scalp_approvals,
            day_trading_develops=day_develops,
            observe_decisions=observes,
            blocked_decisions=blocked,
            regime_distribution=regime_dist,
            avg_scalping_score=avg_scalp_score,
            scalping_approval_rate=scalp_approval_rate,
            scalping_by_regime=scalp_by_regime,
            avg_day_trading_score=avg_day_score,
            day_trading_develop_rate=day_develop_rate,
            day_trading_by_regime=day_by_regime,
            avg_portfolio_drawdown=avg_drawdown,
            risk_blocked_rate=risk_blocked_rate,
            total_conflicts=conflicts,
            conflict_rate=conflict_rate,
            avg_ml_probability=avg_ml_prob * 100,  # Convert to percentage
            decision_distribution=decision_dist,
        )
    
    def compare_periods(
        self,
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime,
    ) -> tuple[OrchestrationBacktestResult, OrchestrationBacktestResult, str]:
        """
        Compare orchestrator performance across two time periods.
        
        Returns:
            (result1, result2, comparison_text)
        """
        result1 = self.backtest(start_date=period1_start, end_date=period1_end)
        result2 = self.backtest(start_date=period2_start, end_date=period2_end)
        
        lines = [
            f"\n{'='*70}",
            f"ORCHESTRATION COMPARISON",
            f"{'='*70}",
            f"\nPeriod 1: {period1_start.strftime('%Y-%m-%d')} to {period1_end.strftime('%Y-%m-%d')}",
            f"Period 2: {period2_start.strftime('%Y-%m-%d')} to {period2_end.strftime('%Y-%m-%d')}",
            f"\nMETRIC                          PERIOD 1    PERIOD 2    CHANGE",
            f"{'-'*70}",
        ]
        
        # Compare key metrics
        metrics = [
            ('Scalp Approval Rate', result1.scalping_approval_rate, result2.scalping_approval_rate, '%'),
            ('Day Trading Develop Rate', result1.day_trading_develop_rate, result2.day_trading_develop_rate, '%'),
            ('Avg Scalping Score', result1.avg_scalping_score, result2.avg_scalping_score, ''),
            ('Avg Day Trading Score', result1.avg_day_trading_score, result2.avg_day_trading_score, ''),
            ('Portfolio Avg Drawdown', result1.avg_portfolio_drawdown, result2.avg_portfolio_drawdown, '%'),
            ('Risk Blocked Rate', result1.risk_blocked_rate, result2.risk_blocked_rate, '%'),
            ('Conflict Rate', result1.conflict_rate, result2.conflict_rate, '%'),
            ('Avg ML Probability', result1.avg_ml_probability, result2.avg_ml_probability, '%'),
        ]
        
        for name, val1, val2, unit in metrics:
            change = val2 - val1
            change_str = f"{change:+.2f}" if unit else f"{change:+.1f}"
            lines.append(f"{name:30s} {val1:8.1f}{unit:2s} {val2:8.1f}{unit:2s} {change_str:8s}")
        
        lines.append(f"{'='*70}\n")
        
        return result1, result2, '\n'.join(lines)
