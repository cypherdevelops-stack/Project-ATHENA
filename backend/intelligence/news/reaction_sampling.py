from __future__ import annotations

from datetime import datetime, timezone

from .models import NewsMarketSample, NewsReactionObservation
from .reaction import assess_market_reaction


def capture_market_sample(*, news_snapshot, phase: str, quote: dict, volatility: str = 'UNKNOWN', metadata: dict | None = None, captured_at: datetime | None = None) -> NewsMarketSample:
    if phase not in {'PRE', 'POST'}:
        raise ValueError('Market sample phase must be PRE or POST.')
    sample = NewsMarketSample.objects.create(
        news_snapshot=news_snapshot,
        phase=phase,
        captured_at=captured_at or datetime.now(timezone.utc),
        bid=_number(quote.get('bid')),
        ask=_number(quote.get('ask')),
        spread=_number(quote.get('spread')),
        volatility=volatility,
        metadata=metadata or {},
    )
    _update_reaction(news_snapshot=news_snapshot, volatility=volatility)
    return sample


def _update_reaction(*, news_snapshot, volatility: str) -> None:
    pre = news_snapshot.market_samples.filter(phase='PRE').order_by('-captured_at').first()
    post = news_snapshot.market_samples.filter(phase='POST').order_by('-captured_at').first()
    if not pre or not post:
        return
    news = news_snapshot.full_payload.get('news') or {}
    reaction = assess_market_reaction(
        expected_score=float(news.get('score', 0) or 0),
        before_price=_mid(pre),
        after_price=_mid(post),
        spread=post.spread,
        volatility=volatility,
    )
    observation = news_snapshot.reaction_observations.order_by('-observed_at').first()
    if observation is None:
        observation = NewsReactionObservation(news_snapshot=news_snapshot, symbol=news_snapshot.symbol)
    observation.expected_direction = reaction.expected_direction
    observation.actual_direction = reaction.actual_direction
    observation.reaction_state = reaction.state
    observation.price_change = reaction.price_change
    observation.volatility = reaction.volatility
    observation.spread = reaction.spread
    observation.outcome_context = {'reason': reaction.reason, 'preSampleId': pre.pk, 'postSampleId': post.pk}
    observation.save()


def _mid(sample: NewsMarketSample) -> float | None:
    if sample.bid is None or sample.ask is None:
        return sample.ask or sample.bid
    return (sample.bid + sample.ask) / 2


def _number(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None