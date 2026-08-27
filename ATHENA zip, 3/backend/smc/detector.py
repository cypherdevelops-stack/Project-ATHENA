from __future__ import annotations

from statistics import mean


def _swing_indices(candles: list[dict], side: str) -> list[int]:
    indices = []
    for index in range(2, len(candles) - 2):
        values = [candles[position][side] for position in range(index - 2, index + 3)]
        center = candles[index][side]
        if center == max(values) if side == 'high' else center == min(values):
            indices.append(index)
    return indices


def _body(candle: dict) -> float:
    return abs(candle['close'] - candle['open'])


def detect_features(candles: list[dict], timeframe: str) -> dict:
    if len(candles) < 5:
        return {'timeframe': timeframe, 'status': 'INSUFFICIENT_DATA', 'structure': 'UNKNOWN', 'events': [], 'orderBlocks': [], 'fairValueGaps': []}
    highs = _swing_indices(candles, 'high')
    lows = _swing_indices(candles, 'low')
    events = []
    structure = 'UNKNOWN'
    if highs and candles[-1]['close'] > candles[highs[-1]]['high']:
        structure = 'BULLISH'
        events.append({'type': 'BOS', 'direction': 'BULLISH', 'time': candles[-1]['time'], 'level': candles[highs[-1]]['high']})
    elif lows and candles[-1]['close'] < candles[lows[-1]]['low']:
        structure = 'BEARISH'
        events.append({'type': 'BOS', 'direction': 'BEARISH', 'time': candles[-1]['time'], 'level': candles[lows[-1]]['low']})
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

    order_blocks = []
    average_body = mean(_body(candle) for candle in candles[-20:])
    for index in range(max(1, len(candles) - 20), len(candles)):
        candle = candles[index]
        following = candles[index + 1] if index + 1 < len(candles) else None
        if not following or _body(following) < average_body * 1.5:
            continue
        direction = 'BULLISH' if following['close'] > following['open'] and candle['close'] < candle['open'] else 'BEARISH' if following['close'] < following['open'] and candle['close'] > candle['open'] else None
        if direction:
            order_blocks.append({'type': 'OB', 'direction': direction, 'time': candle['time'], 'lowerBound': candle['low'], 'upperBound': candle['high'], 'strength': round(min(1, _body(following) / (average_body * 3 or 1)), 3)})

    fair_value_gaps = []
    for index in range(2, len(candles)):
        left, right = candles[index - 2], candles[index]
        if right['low'] > left['high']:
            fair_value_gaps.append({'type': 'FVG', 'direction': 'BULLISH', 'time': right['time'], 'lowerBound': left['high'], 'upperBound': right['low'], 'strength': round(min(1, (right['low'] - left['high']) / (average_body or 1)), 3)})
        elif right['high'] < left['low']:
            fair_value_gaps.append({'type': 'FVG', 'direction': 'BEARISH', 'time': right['time'], 'lowerBound': right['high'], 'upperBound': left['low'], 'strength': round(min(1, (left['low'] - right['high']) / (average_body or 1)), 3)})

    return {'timeframe': timeframe, 'status': 'READY', 'structure': structure, 'events': events, 'orderBlocks': order_blocks, 'fairValueGaps': fair_value_gaps}


def detect_setup_evidence(candles: list[dict]) -> dict:
    """Detect objective sweep, displacement, and structure evidence from closed candles."""
    evidence = {
        'sell_side_liquidity_swept': False,
        'buy_side_liquidity_swept': False,
        'bullish_displacement': False,
        'bearish_displacement': False,
        'bullish_mss': False,
        'bearish_mss': False,
    }
    if len(candles) < 7:
        return evidence

    completed = candles[:-1]
    current = candles[-1]
    highs = _swing_indices(completed, 'high')
    lows = _swing_indices(completed, 'low')
    recent_high = completed[highs[-1]]['high'] if highs else None
    recent_low = completed[lows[-1]]['low'] if lows else None
    if recent_low is not None and current['low'] < recent_low < current['close']:
        evidence['sell_side_liquidity_swept'] = True
    if recent_high is not None and current['high'] > recent_high > current['close']:
        evidence['buy_side_liquidity_swept'] = True

    average_body = mean(_body(candle) for candle in completed[-20:])
    displacement = _body(current) >= average_body * 1.5 if average_body else False
    if displacement and current['close'] > current['open']:
        evidence['bullish_displacement'] = True
    if displacement and current['close'] < current['open']:
        evidence['bearish_displacement'] = True
    if recent_high is not None and current['close'] > recent_high:
        evidence['bullish_mss'] = True
    if recent_low is not None and current['close'] < recent_low:
        evidence['bearish_mss'] = True
    return evidence


def detect_entry_confirmation(*, candles: list[dict], poi: dict, direction: str) -> dict:
    """Detect POI-specific rejection, micro MSS, and momentum on the latest candle."""
    result = {'in_poi': False, 'rejection': False, 'micro_mss': False, 'momentum': False, 'entry_confirmation': False}
    if len(candles) < 3:
        return result
    current, previous = candles[-1], candles[-2]
    lower, upper = float(poi['lowerBound']), float(poi['upperBound'])
    result['in_poi'] = lower <= current['close'] <= upper or (current['low'] <= upper and current['high'] >= lower)
    body = _body(current)
    candle_range = max(current['high'] - current['low'], 0.0)
    average_body = mean(_body(candle) for candle in candles[-min(20, len(candles)): -1])
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
