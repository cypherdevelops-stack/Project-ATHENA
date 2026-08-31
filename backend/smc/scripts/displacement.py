from __future__ import annotations

from statistics import mean

from .swings import swing_indices
from .zones import candle_body


def detect_displacement_and_mss(candles: list[dict]) -> dict:
    completed = candles[:-1]
    current = candles[-1]
    highs = swing_indices(completed, 'high')
    lows = swing_indices(completed, 'low')
    recent_high = completed[highs[-1]]['high'] if highs else None
    recent_low = completed[lows[-1]]['low'] if lows else None
    average_body = mean(candle_body(candle) for candle in completed[-20:])
    displacement = candle_body(current) >= average_body * 1.5 if average_body else False
    return {
        'bullish_displacement': displacement and current['close'] > current['open'],
        'bearish_displacement': displacement and current['close'] < current['open'],
        'bullish_mss': recent_high is not None and current['close'] > recent_high,
        'bearish_mss': recent_low is not None and current['close'] < recent_low,
    }
