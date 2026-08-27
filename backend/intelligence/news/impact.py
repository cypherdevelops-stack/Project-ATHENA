from __future__ import annotations

from datetime import datetime, timezone
import math

from .contracts import NewsEvent
from .sentiment import SentimentResult

IMPORTANCE_WEIGHT = {'LOW': 0.2, 'MEDIUM': 0.45, 'HIGH': 0.75, 'CRITICAL': 1.0}
CURRENCY_DIRECTION = {
    'XAUUSD': {'USD': -1, 'XAUUSD': 1},
    'EURUSD': {'USD': -1, 'EUR': 1},
    'GBPUSD': {'USD': -1, 'GBP': 1},
    'USDJPY': {'USD': 1, 'JPY': -1},
}


def recency_weight(event: NewsEvent, *, now: datetime | None = None, half_life_hours: float = 6.0) -> float:
    now = now or datetime.now(timezone.utc)
    age_hours = max(0.0, (now - event.timestamp).total_seconds() / 3600)
    return math.pow(0.5, age_hours / half_life_hours)


def event_impact(event: NewsEvent, *, relevance: float, confidence: float, now: datetime | None = None) -> float:
    return max(0.0, min(1.0, IMPORTANCE_WEIGHT.get(event.importance, 0.2) * event.source_reliability * relevance * confidence * recency_weight(event, now=now)))


def asset_score(event: NewsEvent, sentiment: SentimentResult, symbol: str) -> tuple[float, float]:
    symbol = symbol.upper()
    mapping = CURRENCY_DIRECTION.get(symbol, {})
    directional = sum(sentiment.score * direction for entity, direction in mapping.items() if entity in event.entities or entity in event.affected_assets)
    relevance = 1.0 if symbol in event.affected_assets else 0.55 if any(entity in mapping for entity in event.entities) else 0.2
    return max(-1.0, min(1.0, directional)), relevance
