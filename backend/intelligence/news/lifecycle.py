from __future__ import annotations

from datetime import datetime, timezone

from .contracts import NewsEvent


def advance_event_state(event: NewsEvent, *, now: datetime | None = None, post_event_minutes: int = 10) -> NewsEvent:
    now = now or datetime.now(timezone.utc)
    event_time = event.timestamp if event.timestamp.tzinfo else event.timestamp.replace(tzinfo=timezone.utc)
    age_seconds = (now - event_time).total_seconds()
    if age_seconds < 0:
        state = 'RELEVANT'
    elif age_seconds <= post_event_minutes * 60:
        state = 'REACTING'
    elif age_seconds <= 24 * 60 * 60:
        state = 'DECAYING'
    else:
        state = 'EXPIRED'
    return NewsEvent(**{**event.__dict__, 'event_state': state})
