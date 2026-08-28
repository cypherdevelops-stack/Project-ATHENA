from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MarketReaction:
    expected_direction: str
    actual_direction: str
    state: str
    price_change: float | None
    volatility: str
    spread: float | None
    reason: str

    def as_dict(self) -> dict:
        return asdict(self)


def assess_market_reaction(*, expected_score: float, before_price: float | None, after_price: float | None, spread: float | None = None, volatility: str = 'UNKNOWN') -> MarketReaction:
    expected = 'UP' if expected_score > 0.15 else 'DOWN' if expected_score < -0.15 else 'FLAT'
    if before_price is None or after_price is None or before_price == 0:
        return MarketReaction(expected, 'UNKNOWN', 'UNCONFIRMED', None, volatility, spread, 'Pre- and post-event prices are required.')
    change = (after_price - before_price) / abs(before_price)
    actual = 'UP' if change > 0.0001 else 'DOWN' if change < -0.0001 else 'FLAT'
    if expected == 'FLAT' or actual == 'FLAT':
        state = 'MIXED' if expected != actual else 'CONFIRMED'
    else:
        state = 'CONFIRMED' if expected == actual else 'CONTRARY'
    return MarketReaction(expected, actual, state, round(change, 8), volatility, spread, f'Expected {expected}; observed {actual} price reaction.')