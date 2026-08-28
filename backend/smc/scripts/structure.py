from __future__ import annotations

from .swings import swing_indices


def detect_structure(candles: list[dict]) -> tuple[str, list[dict]]:
    highs = swing_indices(candles, 'high')
    lows = swing_indices(candles, 'low')
    events = []
    structure = 'UNKNOWN'
    prior_candles = candles[:-1]
    prior_high = max((candle['high'] for candle in prior_candles), default=None)
    prior_low = min((candle['low'] for candle in prior_candles), default=None)
    bullish_break = (
        highs and candles[-1]['close'] > candles[highs[-1]]['high']
    ) or (not highs and prior_high is not None and candles[-1]['close'] > prior_high)
    bearish_break = (
        lows and candles[-1]['close'] < candles[lows[-1]]['low']
    ) or (not lows and prior_low is not None and candles[-1]['close'] < prior_low)
    if bullish_break:
        structure = 'BULLISH'
        level = candles[highs[-1]]['high'] if highs else prior_high
        events.append({'type': 'BOS', 'direction': 'BULLISH', 'time': candles[-1]['time'], 'level': level})
    elif bearish_break:
        structure = 'BEARISH'
        level = candles[lows[-1]]['low'] if lows else prior_low
        events.append({'type': 'BOS', 'direction': 'BEARISH', 'time': candles[-1]['time'], 'level': level})
    elif len(highs) >= 2 and len(lows) >= 2:
        higher_high = candles[highs[-1]]['high'] > candles[highs[-2]]['high']
        higher_low = candles[lows[-1]]['low'] > candles[lows[-2]]['low']
        lower_high = candles[highs[-1]]['high'] < candles[highs[-2]]['high']
        lower_low = candles[lows[-1]]['low'] < candles[lows[-2]]['low']
        if higher_high and higher_low:
            structure = 'BULLISH'
        elif lower_high and lower_low:
            structure = 'BEARISH'
        else:
            structure = 'RANGE'
    return structure, events
