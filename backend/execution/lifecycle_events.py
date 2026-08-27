from __future__ import annotations

from typing import Any
from uuid import UUID

from backend.execution.models import ExecutionLifecycleEvent
from backend.stream.event_bus import ScalpEvent, scalp_event_bus


def publish_lifecycle_event(*, account, decision_id: UUID, event_type: str, state: str,
                            symbol: str, payload: dict[str, Any] | None = None) -> dict:
    """Persist and broadcast one execution lifecycle transition."""
    data = {
        'decisionId': str(decision_id),
        'state': state,
        **(payload or {}),
    }
    event = ExecutionLifecycleEvent.objects.create(
        account=account,
        decision_id=decision_id,
        event_type=event_type,
        state=state,
        symbol=symbol,
        payload=data,
    )
    scalp_event_bus.publish(ScalpEvent(type=event_type, symbol=symbol, data=data))
    return {
        'id': event.pk,
        'type': event_type,
        'symbol': symbol,
        'data': data,
        'timestamp': event.created_at.isoformat(),
    }