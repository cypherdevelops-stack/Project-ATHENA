from __future__ import annotations

from collections.abc import Mapping


REQUIRED_CANDLE_FIELDS = ('open', 'close', 'high', 'low', 'time')


def normalize_candles(candles: list[dict]) -> list[dict]:
    """Return numeric candle values while preserving the public candle shape."""
    normalized = []
    for candle in candles:
        if not isinstance(candle, Mapping):
            raise ValueError('Each candle must be a mapping.')
        missing = [field for field in REQUIRED_CANDLE_FIELDS if field not in candle]
        if missing:
            raise ValueError(f'Candle is missing required fields: {", ".join(missing)}')
        normalized.append({
            **candle,
            'open': float(candle['open']),
            'close': float(candle['close']),
            'high': float(candle['high']),
            'low': float(candle['low']),
        })
    return normalized
