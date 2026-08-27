from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from .contracts import NewsEvent


def parse_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def normalize_event(item: dict, *, source_reliability: float = 0.7) -> NewsEvent:
    headline = str(item.get('headline') or item.get('title') or '').strip()
    summary = str(item.get('summary') or item.get('description') or '').strip()
    source = str(item.get('source') or 'unknown').strip()
    published_at = parse_datetime(item['published_at']) if item.get('published_at') else None
    timestamp = published_at or parse_datetime(item.get('timestamp'))
    event_id = str(item.get('event_id') or item.get('id') or hashlib.sha256(f'{source}:{headline}:{timestamp.isoformat()}'.encode()).hexdigest()[:20])
    return NewsEvent(
        event_id=event_id,
        timestamp=timestamp,
        source=source,
        source_reliability=max(0.0, min(1.0, float(item.get('source_reliability', source_reliability)))),
        headline=headline,
        summary=summary,
        body=item.get('body'),
        importance=str(item.get('importance') or 'LOW').upper(),
        published_at=published_at,
        forecast=_number(item.get('forecast')),
        actual=_number(item.get('actual')),
        previous=_number(item.get('previous')),
    )


def _number(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
