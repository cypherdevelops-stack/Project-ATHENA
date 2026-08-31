from __future__ import annotations

from .swings import swing_indices


def detect_liquidity_sweeps(candles: list[dict]) -> dict:
    evidence = {
        'sell_side_liquidity_swept': False,
        'buy_side_liquidity_swept': False,
    }
    completed = candles[:-1]
    current = candles[-1]
    highs = swing_indices(completed, 'high')
    lows = swing_indices(completed, 'low')
    recent_high = completed[highs[-1]]['high'] if highs else None
    recent_low = completed[lows[-1]]['low'] if lows else None
    if recent_low is not None and current['low'] < recent_low < current['close']:
        evidence['sell_side_liquidity_swept'] = True
    if recent_high is not None and current['high'] > recent_high > current['close']:
        evidence['buy_side_liquidity_swept'] = True
    return evidence
