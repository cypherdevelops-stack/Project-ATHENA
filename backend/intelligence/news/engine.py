from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .classifier import classify_event
from .config import news_settings
from .conflict import assess_conflict
from .contracts import InstrumentNewsState, NewsEvent, NewsIntelligence
from .deduplication import cluster_events
from .entities import extract_entities
from .impact import asset_score, event_impact, relative_currency_strength
from .lifecycle import advance_event_state
from .normalizer import normalize_event
from .providers.json_feed import JsonFeedProvider
from .providers.economic_calendar import EconomicCalendarProvider
from .relationships import relationship_map
from .risk import assess_news_risk
from .sentiment import FinancialSentimentModel, analyze_sentiment


class NewsEngine:
    def __init__(self, provider=None, *, calendar_provider=None, sentiment_model: FinancialSentimentModel | None = None, settings: dict | None = None):
        self.settings = {**news_settings(), **(settings or {})}
        self.relationships = relationship_map(self.settings.get('relationships'))
        self.provider = provider
        if self.provider is None and self.settings.get('feed_url'):
            self.provider = JsonFeedProvider(
                self.settings['feed_url'], timeout=self.settings['timeout'],
                api_key=self.settings.get('api_key'), api_key_header=self.settings.get('api_key_header', 'Authorization'),
            )
        self.calendar_provider = calendar_provider
        self.sentiment_model = sentiment_model
        if self.calendar_provider is None and self.settings.get('calendar_url'):
            self.calendar_provider = EconomicCalendarProvider(
                self.settings['calendar_url'], timeout=self.settings['timeout'],
                api_key=self.settings.get('api_key'), api_key_header=self.settings.get('api_key_header', 'Authorization'),
            )

    def analyze(self, *, symbol: str, technical_direction: str | None = None, regime: str = 'UNKNOWN', now: datetime | None = None) -> NewsIntelligence:
        now = now or datetime.now(timezone.utc)
        if self.provider is None:
            return self._unavailable('News provider is not configured.')
        try:
            raw_items = self.provider.fetch_latest(symbols=[symbol])
            if self.calendar_provider is not None:
                raw_items += self.calendar_provider.fetch_events(start=now, end=now + timedelta(hours=24))
            events = [normalize_event(item, source_reliability=float(item.get('source_reliability', 0.7))) for item in raw_items]
            events = [extract_entities(classify_event(event)) for event in events if event.headline]
            events = cluster_events(events)
            events = [advance_event_state(event, now=now, post_event_minutes=self.settings['post_event_blackout_minutes']) for event in events]
        except Exception as error:
            return self._unavailable(f'News provider unavailable: {error}')
        if not events:
            locked = bool(self.settings['fail_closed'])
            return NewsIntelligence(True, 'WAIT', 0.0, 'NEUTRAL', 0.0, locked, 'No headlines were available.', events=())

        scored = [(event, analyze_sentiment(event, self.sentiment_model)) for event in events]
        total_weight = sum(event_impact(event, relevance=1.0 if symbol.upper() in event.affected_assets else 0.55, confidence=result.confidence, now=now) for event, result in scored)
        weighted_score = sum(result.score * event_impact(event, relevance=1.0 if symbol.upper() in event.affected_assets else 0.55, confidence=result.confidence, now=now) for event, result in scored) / (total_weight or 1.0)
        label = 'BULLISH' if weighted_score > 0.15 else 'BEARISH' if weighted_score < -0.15 else 'MIXED'
        confidence = min(1.0, sum(result.confidence * event.source_reliability for event, result in scored) / len(scored))
        risk, risk_allowed, risk_codes = assess_news_risk(
            events,
            now=now,
            before_minutes=self.settings['pre_event_blackout_minutes'],
            after_minutes=self.settings['post_event_blackout_minutes'],
            fail_closed=False,
        )
        state = 'BLOCK' if not risk_allowed else 'PASS'
        instruments = {symbol.upper(): self._instrument_state(symbol, scored, technical_direction, risk, risk_allowed, risk_codes, now)}
        from .adaptive import get_adaptive_advice
        category = scored[0][0].category
        adaptive = get_adaptive_advice(symbol=symbol, category=category, regime=regime).as_dict()
        entity_pressure = self._entity_pressure(scored)
        return NewsIntelligence(True, state, round(weighted_score, 4), label, round(confidence, 4), not risk_allowed, self._reason(risk, risk_codes), tuple(events), instruments, adaptive, entity_pressure)

    @staticmethod
    def _entity_pressure(scored) -> dict[str, float]:
        values: dict[str, list[float]] = {}
        for event, sentiment in scored:
            for entity, score in relative_currency_strength(event, sentiment).items():
                values.setdefault(entity, []).append(score)
        return {entity: round(sum(scores) / len(scores), 4) for entity, scores in values.items()}

    def _instrument_state(self, symbol, scored, technical_direction, risk, risk_allowed, risk_codes, now):
        relevant = [(event, result) for event, result in scored if symbol.upper() in event.affected_assets or asset_score(event, result, symbol, self.relationships)[1] > 0.2]
        if not relevant:
            return InstrumentNewsState(symbol=symbol.upper(), event_risk=risk, execution_allowed=risk_allowed, reason_codes=tuple(risk_codes))
        weights = [event_impact(event, relevance=asset_score(event, result, symbol, self.relationships)[1], confidence=result.confidence, now=now) for event, result in relevant]
        score = sum(asset_score(event, result, symbol, self.relationships)[0] * weight for (event, result), weight in zip(relevant, weights)) / (sum(weights) or 1.0)
        bias = 'BULLISH' if score > 0.15 else 'BEARISH' if score < -0.15 else 'NEUTRAL'
        alignment, conflict = assess_conflict(technical_direction=technical_direction, fundamental_score=score)
        codes = list(risk_codes)
        if conflict:
            codes.append('TECHNICAL_FUNDAMENTAL_CONFLICT')
        elif alignment == 'ALIGNED':
            codes.append('TECHNICAL_FUNDAMENTAL_ALIGNED')
        return InstrumentNewsState(symbol.upper(), bias, bias, round(min(1.0, abs(score)), 4), round(score, 4), round(max(weights), 4), risk, alignment, conflict, 'BLOCK' if conflict or not risk_allowed else 'WAIT_FOR_TECHNICAL_CONFIRMATION', risk_allowed and not conflict, tuple(dict.fromkeys(codes)), tuple(event.event_id for event, _ in relevant))

    @staticmethod
    def _reason(risk: str, codes: tuple[str, ...]) -> str:
        if risk in {'HIGH', 'CRITICAL'}:
            return f'{risk} news risk: {", ".join(codes)}.'
        return 'News intelligence is available; execution remains governed by technical and portfolio controls.'

    @staticmethod
    def _unavailable(reason: str) -> NewsIntelligence:
        return NewsIntelligence(False, 'DEGRADED', 0.0, 'UNCERTAIN', 0.0, True, reason)
