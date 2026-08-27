from __future__ import annotations

from django.utils import timezone
from backend.accounts.models import Account
from backend.execution.models import OrchestratorAlert, OrchestrationSnapshot
from backend.execution.orchestration_ws import OrchestrationNotificationMixin


class AlertLevel:
    """Alert severity levels."""
    INFO = 'INFO'
    WARNING = 'WARNING'
    CRITICAL = 'CRITICAL'


class AlertType:
    """Alert type constants."""
    DECISION_CHANGED = 'DECISION_CHANGED'
    RISK_THRESHOLD_BREACHED = 'RISK_THRESHOLD_BREACHED'
    STRATEGY_LOCKED = 'STRATEGY_LOCKED'
    PORTFOLIO_BLOCKED = 'PORTFOLIO_BLOCKED'
    CONFLICT_DETECTED = 'CONFLICT_DETECTED'
    REGIME_CHANGED = 'REGIME_CHANGED'
    SETUP_CONFIRMED = 'SETUP_CONFIRMED'
    SETUP_INVALIDATED = 'SETUP_INVALIDATED'


class OrchestratorAlertManager(OrchestrationNotificationMixin):
    """
    Manages orchestrator alerts and notifications.
    
    Tracks:
    - Decision changes
    - Risk threshold breaches
    - Strategy locks
    - Portfolio blocks
    - Conflict detection
    - Regime changes
    
    Usage:
    ```python
    manager = OrchestratorAlertManager(account)
    manager.alert_decision_changed(
        old_decision='OBSERVE',
        new_decision='SCALP_LONG_APPROVED',
        reason='Scalping setup confirmed'
    )
    ```
    """
    
    def __init__(self, account: Account, symbol: str = 'XAUUSD'):
        self.account = account
        self.symbol = symbol
        self._last_decision: str | None = None
        self._last_regime: str | None = None
        self._last_scalping_status: str | None = None
        self._last_day_trading_status: str | None = None
    
    async def check_and_alert(self, current_orchestration: dict, current_snapshot: OrchestrationSnapshot | None = None) -> list[OrchestratorAlert]:
        """
        Check for alert conditions and create alerts as needed.
        
        Returns list of new alerts created.
        """
        alerts_created = []
        decision = current_orchestration.get('decision', {})
        current_decision = decision.get('action', 'OBSERVE')
        
        # Check decision change
        if self._last_decision and self._last_decision != current_decision:
            alert = await self.alert_decision_changed(
                old_decision=self._last_decision,
                new_decision=current_decision,
                reason=decision.get('reason', ''),
                snapshot=current_snapshot,
            )
            alerts_created.append(alert)
        
        self._last_decision = current_decision
        
        # Check regime change
        regime = current_orchestration.get('market_regime', 'UNKNOWN')
        if self._last_regime and self._last_regime != regime:
            alert = await self.alert_regime_changed(
                old_regime=self._last_regime,
                new_regime=regime,
                snapshot=current_snapshot,
            )
            alerts_created.append(alert)
        
        self._last_regime = regime
        
        # Check scalping status change
        scalping_status = current_orchestration.get('scalping_engine', {}).get('status', 'OBSERVE')
        if self._last_scalping_status and self._last_scalping_status != scalping_status:
            if scalping_status == 'READY':
                alert = await self.alert_setup_confirmed(
                    strategy='SCALPING',
                    direction=current_orchestration.get('scalping_engine', {}).get('direction'),
                    snapshot=current_snapshot,
                )
                alerts_created.append(alert)
        
        self._last_scalping_status = scalping_status
        
        # Check day trading status change
        day_status = current_orchestration.get('day_trading_engine', {}).get('status', 'OBSERVE')
        if self._last_day_trading_status and self._last_day_trading_status != day_status:
            if day_status == 'DEVELOPING':
                alert = await self.alert_setup_confirmed(
                    strategy='DAY_TRADING',
                    direction=current_orchestration.get('day_trading_engine', {}).get('direction'),
                    snapshot=current_snapshot,
                )
                alerts_created.append(alert)
        
        self._last_day_trading_status = day_status
        
        # Check portfolio block
        portfolio = current_orchestration.get('portfolio', {})
        if not portfolio.get('risk_available', True):
            if current_decision == 'BLOCKED':
                alert = await self.alert_portfolio_blocked(
                    reason='Risk limit reached',
                    snapshot=current_snapshot,
                )
                alerts_created.append(alert)
        
        return alerts_created
    
    async def alert_decision_changed(
        self,
        old_decision: str,
        new_decision: str,
        reason: str,
        snapshot: OrchestrationSnapshot | None = None,
    ) -> OrchestratorAlert:
        """Alert when orchestrator decision changes."""
        severity = AlertLevel.INFO if new_decision == 'OBSERVE' else AlertLevel.WARNING
        
        alert = OrchestratorAlert.objects.create(
            account=self.account,
            severity=severity,
            alert_type=AlertType.DECISION_CHANGED,
            title=f'Decision Changed: {old_decision} → {new_decision}',
            message=reason,
            symbol=self.symbol,
            related_snapshot=snapshot,
            data={
                'old_decision': old_decision,
                'new_decision': new_decision,
            },
        )
        
        # Send via WebSocket
        await self.send_orchestration_alert(
            self.symbol,
            severity,
            AlertType.DECISION_CHANGED,
            alert.title,
            alert.message,
        )
        
        return alert
    
    async def alert_risk_threshold_breached(
        self,
        threshold_type: str,
        current_value: float,
        threshold: float,
        snapshot: OrchestrationSnapshot | None = None,
    ) -> OrchestratorAlert:
        """Alert when risk threshold is breached."""
        alert = OrchestratorAlert.objects.create(
            account=self.account,
            severity=AlertLevel.CRITICAL,
            alert_type=AlertType.RISK_THRESHOLD_BREACHED,
            title=f'{threshold_type} Threshold Breached',
            message=f'{threshold_type}: {current_value:.2f}% (threshold: {threshold:.2f}%)',
            symbol=self.symbol,
            related_snapshot=snapshot,
            data={
                'threshold_type': threshold_type,
                'current_value': current_value,
                'threshold': threshold,
            },
        )
        
        await self.send_orchestration_alert(
            self.symbol,
            AlertLevel.CRITICAL,
            AlertType.RISK_THRESHOLD_BREACHED,
            alert.title,
            alert.message,
        )
        
        return alert
    
    async def alert_strategy_locked(
        self,
        strategy: str,
        reason: str,
        snapshot: OrchestrationSnapshot | None = None,
    ) -> OrchestratorAlert:
        """Alert when a strategy enters locked state."""
        alert = OrchestratorAlert.objects.create(
            account=self.account,
            severity=AlertLevel.WARNING,
            alert_type=AlertType.STRATEGY_LOCKED,
            title=f'{strategy} Strategy Locked',
            message=reason,
            symbol=self.symbol,
            related_snapshot=snapshot,
            data={
                'strategy': strategy,
            },
        )
        
        await self.send_orchestration_alert(
            self.symbol,
            AlertLevel.WARNING,
            AlertType.STRATEGY_LOCKED,
            alert.title,
            alert.message,
        )
        
        return alert
    
    async def alert_portfolio_blocked(
        self,
        reason: str,
        snapshot: OrchestrationSnapshot | None = None,
    ) -> OrchestratorAlert:
        """Alert when portfolio is blocked."""
        alert = OrchestratorAlert.objects.create(
            account=self.account,
            severity=AlertLevel.CRITICAL,
            alert_type=AlertType.PORTFOLIO_BLOCKED,
            title='Portfolio Blocked',
            message=reason,
            symbol=self.symbol,
            related_snapshot=snapshot,
        )
        
        await self.send_orchestration_alert(
            self.symbol,
            AlertLevel.CRITICAL,
            AlertType.PORTFOLIO_BLOCKED,
            alert.title,
            alert.message,
        )
        
        return alert
    
    async def alert_conflict_detected(
        self,
        scalping_direction: str,
        day_trading_direction: str,
        resolution: str,
        snapshot: OrchestrationSnapshot | None = None,
    ) -> OrchestratorAlert:
        """Alert when conflicting directions detected."""
        alert = OrchestratorAlert.objects.create(
            account=self.account,
            severity=AlertLevel.WARNING,
            alert_type=AlertType.CONFLICT_DETECTED,
            title=f'Conflict: Scalping {scalping_direction} vs Day {day_trading_direction}',
            message=f'Resolved by: {resolution}',
            symbol=self.symbol,
            related_snapshot=snapshot,
            data={
                'scalping_direction': scalping_direction,
                'day_trading_direction': day_trading_direction,
                'resolution': resolution,
            },
        )
        
        await self.send_orchestration_alert(
            self.symbol,
            AlertLevel.WARNING,
            AlertType.CONFLICT_DETECTED,
            alert.title,
            alert.message,
        )
        
        return alert
    
    async def alert_regime_changed(
        self,
        old_regime: str,
        new_regime: str,
        snapshot: OrchestrationSnapshot | None = None,
    ) -> OrchestratorAlert:
        """Alert when market regime changes."""
        alert = OrchestratorAlert.objects.create(
            account=self.account,
            severity=AlertLevel.INFO,
            alert_type=AlertType.REGIME_CHANGED,
            title=f'Regime Changed: {old_regime} → {new_regime}',
            message=f'Market structure has shifted',
            symbol=self.symbol,
            related_snapshot=snapshot,
            data={
                'old_regime': old_regime,
                'new_regime': new_regime,
            },
        )
        
        await self.send_regime_change(self.symbol, new_regime)
        
        return alert
    
    async def alert_setup_confirmed(
        self,
        strategy: str,
        direction: str | None,
        snapshot: OrchestrationSnapshot | None = None,
    ) -> OrchestratorAlert:
        """Alert when a setup is confirmed and ready."""
        alert = OrchestratorAlert.objects.create(
            account=self.account,
            severity=AlertLevel.WARNING,
            alert_type=AlertType.SETUP_CONFIRMED,
            title=f'{strategy} Setup Confirmed',
            message=f'{strategy} {direction} setup is ready',
            symbol=self.symbol,
            related_snapshot=snapshot,
            data={
                'strategy': strategy,
                'direction': direction,
            },
        )
        
        await self.send_orchestration_alert(
            self.symbol,
            AlertLevel.WARNING,
            AlertType.SETUP_CONFIRMED,
            alert.title,
            alert.message,
        )
        
        return alert
    
    @staticmethod
    def get_recent_alerts(account: Account, limit: int = 10) -> list[OrchestratorAlert]:
        """Fetch recent alerts for an account."""
        return list(
            OrchestratorAlert.objects.filter(account=account)
            .order_by('-timestamp')[:limit]
        )
    
    @staticmethod
    def get_unread_alerts(account: Account) -> list[OrchestratorAlert]:
        """Fetch unread alerts for an account."""
        return list(
            OrchestratorAlert.objects.filter(account=account, is_read=False)
            .order_by('-timestamp')
        )
    
    @staticmethod
    def mark_alert_as_read(alert: OrchestratorAlert) -> None:
        """Mark an alert as read."""
        alert.is_read = True
        alert.save()
    
    @staticmethod
    def mark_all_alerts_as_read(account: Account) -> int:
        """Mark all alerts for an account as read."""
        count, _ = OrchestratorAlert.objects.filter(
            account=account,
            is_read=False
        ).update(is_read=True)
        return count
