from __future__ import annotations

from statistics import mean

from .zones import candle_body


def detect_entry_confirmation(*, candles: list[dict], poi: dict, direction: str) -> dict:
    result = {'in_poi': False, 'rejection': False, 'micro_mss': False, 'momentum': False, 'entry_confirmation': False}
    if len(candles) < 3:
        return result
    current, previous = candles[-1], candles[-2]
    lower, upper = float(poi['lowerBound']), float(poi['upperBound'])
    result['in_poi'] = lower <= current['close'] <= upper or (current['low'] <= upper and current['high'] >= lower)
    body = candle_body(current)
    candle_range = max(current['high'] - current['low'], 0.0)
    average_body = mean(candle_body(candle) for candle in candles[-min(20, len(candles)): -1])
    bullish = direction == 'BUY'
    if bullish:
        lower_wick = min(current['open'], current['close']) - current['low']
        result['rejection'] = result['in_poi'] and current['close'] > current['open'] and lower_wick >= max(body * 0.5, candle_range * 0.15)
        result['micro_mss'] = current['close'] > previous['high']
        result['momentum'] = current['close'] > current['open'] and body >= average_body * 1.2 if average_body else False
    else:
        upper_wick = current['high'] - max(current['open'], current['close'])
        result['rejection'] = result['in_poi'] and current['close'] < current['open'] and upper_wick >= max(body * 0.5, candle_range * 0.15)
        result['micro_mss'] = current['close'] < previous['low']
        result['momentum'] = current['close'] < current['open'] and body >= average_body * 1.2 if average_body else False
    result['entry_confirmation'] = all(result[key] for key in ('in_poi', 'rejection', 'micro_mss', 'momentum'))
    return result


def advance_poi_state(poi: dict, current_price: float) -> dict:
    lower, upper = poi['lowerBound'], poi['upperBound']
    state = poi.get('state', 'DETECTED')
    if poi['direction'] == 'BULLISH':
        if current_price < lower:
            state, reason = 'INVALIDATED', 'PRICE_CLOSED_BELOW_ZONE'
        elif lower <= current_price <= upper:
            state, reason = 'REACTED', None
        else:
            state, reason = state if state not in {'DETECTED', 'REACTED'} else 'MONITORING', None
    else:
        if current_price > upper:
            state, reason = 'INVALIDATED', 'PRICE_CLOSED_ABOVE_ZONE'
        elif lower <= current_price <= upper:
            state, reason = 'REACTED', None
        else:
            state, reason = state if state not in {'DETECTED', 'REACTED'} else 'MONITORING', None
    return {**poi, 'state': state, 'invalidationReason': reason}
