from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime


NEWS_CATEGORIES = frozenset({
    'ECONOMIC_DATA', 'CENTRAL_BANK', 'INTEREST_RATES', 'INFLATION', 'EMPLOYMENT',
    'GDP', 'PMI', 'RETAIL_SALES', 'TRADE', 'GOVERNMENT', 'GEOPOLITICAL',
    'WAR_CONFLICT', 'ENERGY', 'COMMODITIES', 'BANKING', 'FINANCIAL_MARKETS',
    'CORPORATE', 'REGULATORY', 'CRYPTO', 'OTHER',
})
NEWS_RISK_LEVELS = frozenset({'CLEAR', 'LOW', 'MODERATE', 'HIGH', 'CRITICAL'})


@dataclass(frozen=True)
class NewsEvent:
    event_id: str
    timestamp: datetime
    source: str
    source_reliability: float
    headline: str
    summary: str = ''
    body: str | None = None
    category: str = 'OTHER'
    entities: tuple[str, ...] = ()
    affected_assets: tuple[str, ...] = ()
    importance: str = 'LOW'
    published_at: datetime | None = None
    event_state: str = 'DETECTED'
    event_cluster_id: str | None = None
    forecast: float | None = None
    actual: float | None = None
    previous: float | None = None

    def as_dict(self) -> dict:
        value = asdict(self)
        for key in ('timestamp', 'published_at'):
            if value[key] is not None:
                value[key] = value[key].isoformat()
        return value


@dataclass(frozen=True)
class InstrumentNewsState:
    symbol: str
    fundamental_bias: str = 'UNCERTAIN'
    sentiment: str = 'UNCERTAIN'
    sentiment_confidence: float = 0.0
    news_pressure: float = 0.0
    impact_score: float = 0.0
    event_risk: str = 'CLEAR'
    technical_alignment: str = 'UNCERTAIN'
    technical_conflict: bool = False
    recommended_action: str = 'WAIT'
    execution_allowed: bool = False
    reason_codes: tuple[str, ...] = ()
    active_events: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class NewsIntelligence:
    provider_available: bool
    state: str
    score: float
    label: str
    confidence: float
    news_locked: bool
    reason: str
    events: tuple[NewsEvent, ...] = ()
    instruments: dict[str, InstrumentNewsState] = field(default_factory=dict)

    def for_symbol(self, symbol: str) -> InstrumentNewsState:
        return self.instruments.get(symbol.upper(), InstrumentNewsState(symbol=symbol.upper()))

    def as_dict(self) -> dict:
        return {
            'provider_available': self.provider_available,
            'state': self.state,
            'score': self.score,
            'label': self.label,
            'confidence': self.confidence,
            'news_locked': self.news_locked,
            'reason': self.reason,
            'events': [event.as_dict() for event in self.events],
            'instruments': {symbol: state.as_dict() for symbol, state in self.instruments.items()},
        }
