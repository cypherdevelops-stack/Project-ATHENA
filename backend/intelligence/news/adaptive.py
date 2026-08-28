from __future__ import annotations

from dataclasses import dataclass

from .models import AdaptiveNewsStatistic, NewsIntelligenceSnapshot


@dataclass(frozen=True)
class AdaptiveNewsAdvice:
    symbol: str
    status: str
    expected_reaction: str
    confidence: float
    sample_count: int
    confirmation_rate: float
    reason: str

    def as_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'status': self.status,
            'expected_reaction': self.expected_reaction,
            'confidence': self.confidence,
            'sample_count': self.sample_count,
            'confirmation_rate': self.confirmation_rate,
            'reason': self.reason,
        }


def get_adaptive_advice(*, symbol: str, category: str, regime: str, source_class: str = 'unknown', minimum_samples: int = 5) -> AdaptiveNewsAdvice:
    statistic = AdaptiveNewsStatistic.objects.filter(
        symbol=symbol.upper(), category=category, regime=regime, source_class=source_class,
    ).first()
    if statistic is None or statistic.observations < minimum_samples:
        count = statistic.observations if statistic else 0
        return AdaptiveNewsAdvice(symbol.upper(), 'INSUFFICIENT_HISTORY', 'UNKNOWN', 0.0, count, 0.0, f'{minimum_samples} time-ordered observations are required.')
    confirmation_rate = statistic.confirmed_reactions / statistic.observations
    expected = 'UP' if statistic.mean_price_change > 0 else 'DOWN' if statistic.mean_price_change < 0 else 'FLAT'
    return AdaptiveNewsAdvice(symbol.upper(), 'ADVISORY', expected, round(confirmation_rate, 4), statistic.observations, round(confirmation_rate, 4), 'Historical reaction statistics are advisory and do not authorize execution.')


def record_reaction_outcome(*, snapshot: NewsIntelligenceSnapshot, regime: str = 'UNKNOWN') -> list[AdaptiveNewsStatistic]:
    """Update statistics only from a completed reaction observation."""
    observation = snapshot.reaction_observations.order_by('-observed_at').first()
    if observation is None or observation.reaction_state not in {'CONFIRMED', 'CONTRARY'}:
        return []
    events = snapshot.events or [{}]
    categories = {str(event.get('category', 'OTHER')) for event in events}
    updated = []
    for category in categories:
        statistic, _ = AdaptiveNewsStatistic.objects.get_or_create(
            symbol=snapshot.symbol,
            category=category,
            regime=regime,
            source_class='aggregate',
        )
        old_count = statistic.observations
        statistic.observations += 1
        if observation.reaction_state == 'CONFIRMED':
            statistic.confirmed_reactions += 1
        else:
            statistic.contrary_reactions += 1
        if observation.price_change is not None:
            statistic.mean_price_change = ((statistic.mean_price_change * old_count) + observation.price_change) / statistic.observations
        statistic.mean_sentiment_confidence = ((statistic.mean_sentiment_confidence * old_count) + snapshot.sentiment_confidence) / statistic.observations
        statistic.last_observed_at = observation.observed_at
        statistic.save()
        updated.append(statistic)
    return updated