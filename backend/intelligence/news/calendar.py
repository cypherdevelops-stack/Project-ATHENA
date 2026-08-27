from __future__ import annotations

from datetime import datetime


def event_is_in_window(event_time: datetime, *, now: datetime, before_minutes: int, after_minutes: int) -> bool:
    seconds = (event_time - now).total_seconds()
    return -after_minutes * 60 <= seconds <= before_minutes * 60


def calendar_event_state(event: dict, *, now: datetime) -> str:
    event_time = event.get('event_time') or event.get('timestamp')
    if not isinstance(event_time, datetime):
        return 'UNKNOWN'
    if event_time <= now:
        return 'ACTIVE'
    return 'SCHEDULED'
