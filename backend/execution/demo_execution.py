from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from backend.execution.live_engine import LiveExecutionError, send_live_order
from backend.execution.automation_policy import AutomationPolicyError, enforce_automation_policy
from backend.execution.models import LiveExecutionAttempt
from backend.execution.lifecycle_events import publish_lifecycle_event
from backend.execution.intent_service import persist_execution_intent
from backend.execution.models import ExecutionIntent
from backend.execution.risk_engine import assess_risk
from backend.execution.trade_setup import build_trade_setup


class DemoExecutionError(ValueError):
    pass


def execute_confirmed_demo_decision(*, account, snapshot, confirmation: bool, idempotency_key: str, max_slippage: float = 0.0, mt5_module=None, execution_mode: str = 'CONFIRMATION_REQUIRED') -> dict:
    """Submit one explicitly confirmed orchestration decision to a demo MT5 account."""
    if confirmation is not True:
        raise DemoExecutionError('Explicit demo-order confirmation is required.')
    if account.account_type != account.AccountType.DEMO:
        raise DemoExecutionError('Confirmed execution is restricted to demo accounts.')
    if not idempotency_key:
        raise DemoExecutionError('An idempotency key is required.')

    existing = LiveExecutionAttempt.objects.filter(decision_id=snapshot.decision_id).first()
    if existing:
        return _payload(existing, duplicate=True)
    existing = LiveExecutionAttempt.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return _payload(existing, duplicate=True)

    orchestration = snapshot.full_payload.get('orchestration') or {}
    decision = orchestration.get('decision') or {}
    strategy = decision.get('strategy')
    action = decision.get('action', orchestration.get('status', 'OBSERVE'))
    if not action.endswith('_APPROVED') or strategy not in {'SCALPING', 'DAY_TRADING'}:
        raise DemoExecutionError(f'Decision {action} is not approved for execution.')
    decision_timestamp = snapshot.timestamp
    expires_at = (decision.get('expiresAt') or orchestration.get('expiresAt'))
    if expires_at:
        expires_at = timezone.datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    try:
        enforce_automation_policy(
            account=account,
            strategy=strategy,
            setup={},
            decision_timestamp=decision_timestamp,
            expires_at=expires_at,
            required_mode=execution_mode,
        )
    except AutomationPolicyError as error:
        raise DemoExecutionError(str(error)) from error
    candidates_key = 'scalping' if strategy == 'SCALPING' else 'dayTrading'
    intent = ExecutionIntent.objects.filter(decision_id=snapshot.decision_id).first()
    if intent and (intent.account_id != account.pk or intent.status not in {'QUEUED', 'REJECTED'}):
        raise DemoExecutionError(f'Execution intent is not available: {intent.status}.')
    candidate = None
    candidates = (snapshot.full_payload.get(candidates_key) or {}).get('candidates') or []
    candidate = candidate or next((item for item in candidates if item.get('direction')), None)
    if intent:
        setup = intent.setup
    elif not candidate or not candidate.get('entryZone'):
        raise DemoExecutionError('Approved decision has no executable candidate.')
    if not intent:
        entry_zone = candidate['entryZone']
        entry = (float(entry_zone['lower']) + float(entry_zone['upper'])) / 2
        width = max(float(entry_zone['upper']) - float(entry_zone['lower']), 1e-9)
        stop_loss = entry - width * 0.5 if candidate['direction'] == 'BUY' else entry + width * 0.5
        take_profit = entry + width * 2 if candidate['direction'] == 'BUY' else entry - width * 2
        risk = assess_risk(account=account, direction=candidate['direction'], entry=entry, stop_loss=stop_loss, take_profit=take_profit)
        setup = build_trade_setup(candidate=candidate, risk=risk)
        if not risk.get('approved') or setup.get('state') != 'RISK_APPROVED':
            raise DemoExecutionError(risk.get('reason', 'Risk approval failed.'))
        intent = persist_execution_intent(account=account, snapshot=snapshot, decision=decision, setup=setup)
    try:
        enforce_automation_policy(
            account=account,
            strategy=strategy,
            setup=setup,
            required_mode=execution_mode,
        )
    except AutomationPolicyError as error:
        raise DemoExecutionError(str(error)) from error

    request_payload = {
        'symbol': account.broker_symbol,
        'direction': setup['direction'],
        'entry': setup['entry'],
        'stopLoss': setup['stopLoss'],
        'takeProfit2': setup['takeProfit2'],
        'volume': setup['volume'],
        'maxSlippage': max_slippage,
    }
    try:
        with transaction.atomic():
            attempt = LiveExecutionAttempt.objects.create(
                account=account,
                intent=intent,
                decision_id=snapshot.decision_id,
                idempotency_key=idempotency_key,
                strategy=strategy,
                status='SUBMITTING',
                setup=setup,
                request_payload=request_payload,
            )
            intent.status = 'SUBMITTING'
            intent.save(update_fields=['status'])
        publish_lifecycle_event(
            account=account,
            decision_id=snapshot.decision_id,
            event_type='EXECUTION_SUBMITTING',
            state='SUBMITTING',
            symbol=account.broker_symbol,
            payload={'strategy': strategy, 'idempotencyKey': idempotency_key},
        )
    except IntegrityError:
        attempt = LiveExecutionAttempt.objects.filter(
            decision_id=snapshot.decision_id,
        ).first() or LiveExecutionAttempt.objects.get(idempotency_key=idempotency_key)
        return _payload(attempt, duplicate=True)

    try:
        broker_result = send_live_order(
            account=account,
            setup=setup,
            requested_price=setup.get('entry'),
            max_slippage=max_slippage,
            idempotency_key=idempotency_key,
            mt5_module=mt5_module,
            required_mode=execution_mode,
        )
    except LiveExecutionError as error:
        attempt.status = 'REJECTED'
        attempt.reason = str(error)
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=['status', 'reason', 'completed_at'])
        intent.status = 'REJECTED'
        intent.invalidation_reason = str(error)
        intent.save(update_fields=['status', 'invalidation_reason'])
        publish_lifecycle_event(
            account=account,
            decision_id=snapshot.decision_id,
            event_type='ORDER_REJECTED',
            state='REJECTED',
            symbol=account.broker_symbol,
            payload={'reason': str(error), 'idempotencyKey': idempotency_key},
        )
        raise

    attempt.status = broker_result.get('status', 'REJECTED')
    attempt.order_ticket = broker_result.get('order')
    attempt.deal_ticket = broker_result.get('deal')
    attempt.broker_response = broker_result
    attempt.reason = '' if attempt.status == 'ACCEPTED' else 'Broker rejected the order.'
    attempt.completed_at = timezone.now()
    attempt.save(update_fields=['status', 'order_ticket', 'deal_ticket', 'broker_response', 'reason', 'completed_at'])
    intent.status = attempt.status
    intent.save(update_fields=['status'])
    event_type = 'ORDER_ACCEPTED' if attempt.status == 'ACCEPTED' else 'ORDER_REJECTED'
    publish_lifecycle_event(
        account=account,
        decision_id=snapshot.decision_id,
        event_type=event_type,
        state=attempt.status,
        symbol=account.broker_symbol,
        payload={
            'order': attempt.order_ticket,
            'deal': attempt.deal_ticket,
            'reason': attempt.reason,
            'brokerResponse': broker_result,
        },
    )
    return _payload(attempt)

def execute_automatic_decision(*, account, snapshot, max_slippage: float = 0.0, mt5_module=None) -> dict:
    """Submit one fresh, policy-approved automatic decision from the worker."""
    return execute_confirmed_demo_decision(
        account=account,
        snapshot=snapshot,
        confirmation=True,
        idempotency_key=f'auto-{snapshot.decision_id}',
        max_slippage=max_slippage,
        mt5_module=mt5_module,
        execution_mode='AUTOMATIC',
    )

def _payload(attempt: LiveExecutionAttempt, duplicate=False) -> dict:
    return {
        'status': attempt.status,
        'decisionId': str(attempt.decision_id),
        'idempotencyKey': attempt.idempotency_key,
        'strategy': attempt.strategy,
        'order': attempt.order_ticket,
        'deal': attempt.deal_ticket,
        'reason': attempt.reason,
        'duplicate': duplicate,
    }
