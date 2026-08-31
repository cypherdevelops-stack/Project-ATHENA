from __future__ import annotations

from statistics import mean


def candle_body(candle: dict) -> float:
    return abs(candle['close'] - candle['open'])


def detect_zones(candles: list[dict]) -> tuple[list[dict], list[dict]]:
    average_body = mean(candle_body(candle) for candle in candles[-20:])
    order_blocks = []
    for index in range(max(1, len(candles) - 20), len(candles)):
        candle = candles[index]
        following = candles[index + 1] if index + 1 < len(candles) else None
        if not following or candle_body(following) < average_body * 1.5:
            continue
        direction = (
            'BULLISH' if following['close'] > following['open'] and candle['close'] < candle['open']
            else 'BEARISH' if following['close'] < following['open'] and candle['close'] > candle['open']
            else None
        )
        if direction:
            order_blocks.append({
                'type': 'OB',
                'direction': direction,
                'time': candle['time'],
                'lowerBound': candle['low'],
                'upperBound': candle['high'],
                'strength': round(min(1, candle_body(following) / (average_body * 3 or 1)), 3),
            })

    fair_value_gaps = []
    for index in range(2, len(candles)):
        left, right = candles[index - 2], candles[index]
        if right['low'] > left['high']:
            fair_value_gaps.append({
                'type': 'FVG',
                'direction': 'BULLISH',
                'time': right['time'],
                'lowerBound': left['high'],
                'upperBound': right['low'],
                'strength': round(min(1, (right['low'] - left['high']) / (average_body or 1)), 3),
            })
        elif right['high'] < left['low']:
            fair_value_gaps.append({
                'type': 'FVG',
                'direction': 'BEARISH',
                'time': right['time'],
                'lowerBound': right['high'],
                'upperBound': left['low'],
                'strength': round(min(1, (left['low'] - right['high']) / (average_body or 1)), 3),
            })
    return order_blocks, fair_value_gaps
