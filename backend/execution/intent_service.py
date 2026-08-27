from __future__ import annotations

from datetime import datetime

from backend.execution.models import ExecutionIntent


def persist_execution_intent(*, account, snapshot, decision: dict, setup: dict) -> ExecutionIntent:
    """Persist one canonical orchestrator command for the Executioner."""
    expires_at = setup.get('expiresAt')
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    intent, _ = ExecutionIntent.objects.update_or_create(
        decision_id=snapshot.decision_id,
        defaults={
            'account': account,
            'snapshot': snapshot,
            'strategy': decision['strategy'],
            'direction': decision['direction'],
            'symbol': setup.get('symbol') or account.broker_symbol,
            'setup': setup,
            'status': 'QUEUED',
            'expires_at': expires_at,
        },
    )
    return intent


def intent_payload(intent: ExecutionIntent) -> dict:
    return {
        'intentId': intent.pk,
        'decisionId': str(intent.decision_id),
        'strategy': intent.strategy,
        'direction': intent.direction,
        'symbol': intent.symbol,
        'status': intent.status,
        'setup': intent.setup,
        'createdAt': intent.created_at.isoformat(),
        'expiresAt': intent.expires_at.isoformat() if intent.expires_at else None,
    }