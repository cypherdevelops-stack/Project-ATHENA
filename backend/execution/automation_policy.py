from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone

from backend.execution.models import LiveExecutionAttempt


class AutomationPolicyError(ValueError):
    pass


def enforce_automation_policy(*, account, strategy: str, setup: dict, decision_timestamp: datetime | None = None,
                              expires_at: datetime | None = None, required_mode: str = 'CONFIRMATION_REQUIRED') -> None:
    """Fail closed when an account's server-side execution policy rejects an order."""
    if not getattr(account, 'live_execution_enabled', False):
        raise AutomationPolicyError('Live execution is disabled by the account policy.')
    mode = getattr(account, 'live_execution_mode', 'DISABLED')
    if mode != required_mode:
        requested_label = 'confirmed' if required_mode == 'CONFIRMATION_REQUIRED' else required_mode.lower()
        raise AutomationPolicyError(f'Account execution mode {mode} does not allow {requested_label} orders.')
    if strategy not in set(getattr(account, 'allowed_strategies', []) or []):
        raise AutomationPolicyError(f'{strategy} is not enabled by the account execution policy.')
    allowed_instruments = getattr(account, 'allowed_instruments', []) or []
    canonical_asset = getattr(account, 'canonical_asset', '')
    if allowed_instruments and canonical_asset not in allowed_instruments:
        raise AutomationPolicyError(f'{canonical_asset or "The symbol"} is not enabled by the account execution policy.')

    now = timezone.now()
    freshness = int(getattr(account, 'require_fresh_decision_seconds', 60) or 0)
    if decision_timestamp is not None:
        if timezone.is_naive(decision_timestamp):
            decision_timestamp = timezone.make_aware(decision_timestamp)
        if freshness and now - decision_timestamp > timedelta(seconds=freshness):
            raise AutomationPolicyError('The orchestration decision is too old for this account policy.')
    if expires_at is not None:
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at)
        if now >= expires_at:
            raise AutomationPolicyError('The orchestration decision has expired.')

    today = timezone.localdate()
    attempts = LiveExecutionAttempt.objects.filter(
        account=account,
        created_at__date=today,
        status__in=('SUBMITTING', 'ACCEPTED'),
    )
    max_orders = int(getattr(account, 'max_live_orders_per_day', 0) or 0)
    if max_orders and attempts.count() >= max_orders:
        raise AutomationPolicyError('The account daily live-order limit has been reached.')

    risk_amount = Decimal(str(setup.get('riskAmount', 0) or 0))
    max_risk = Decimal(str(getattr(account, 'max_live_risk_per_day', 0) or 0))
    if max_risk and sum((Decimal(str(item.setup.get('riskAmount', 0) or 0)) for item in attempts), Decimal()) + risk_amount > max_risk:
        raise AutomationPolicyError('The account daily live-risk limit would be exceeded.')

    max_value = Decimal(str(getattr(account, 'max_order_value', 0) or 0))
    order_value = Decimal(str(setup.get('entry', 0) or 0)) * Decimal(str(setup.get('volume', 0) or 0))
    if max_value and order_value > max_value:
        raise AutomationPolicyError('The order value exceeds the account policy limit.')