from __future__ import annotations

from statistics import mean


def _rate_value(rate, field: str, default=0):
    if isinstance(rate, dict):
        return rate.get(field, default)
    try:
        return rate[field]
    except (IndexError, KeyError, TypeError, ValueError):
        return default


def normalize_candles(rates) -> list[dict]:
    return [
        {
            'time': int(_rate_value(rate, 'time')),
            'open': float(_rate_value(rate, 'open')),
            'high': float(_rate_value(rate, 'high')),
            'low': float(_rate_value(rate, 'low')),
            'close': float(_rate_value(rate, 'close')),
            'volume': int(_rate_value(rate, 'tick_volume')),
        }
        for rate in ([] if rates is None else rates)
    ]


def classify_regime(candles: list[dict]) -> dict:
    if len(candles) < 20:
        return {'state': 'UNKNOWN', 'confidence': 0.0, 'reason': 'At least 20 candles are required.'}
    closes = [candle['close'] for candle in candles]
    ranges = [candle['high'] - candle['low'] for candle in candles]
    short_mean = mean(closes[-10:])
    long_mean = mean(closes[-20:])
    average_range = mean(ranges[-20:])
    displacement = abs(closes[-1] - closes[-20])
    trend_ratio = displacement / (sum(abs(closes[index] - closes[index - 1]) for index in range(len(closes) - 19, len(closes))) or 1)
    volatility_ratio = (mean(ranges[-5:]) / average_range) if average_range else 0
    if volatility_ratio >= 1.8:
        state = 'VOLATILE'
    elif trend_ratio >= 0.55 and abs(short_mean - long_mean) >= average_range * 0.25:
        state = 'TRENDING_UP' if short_mean > long_mean else 'TRENDING_DOWN'
    else:
        state = 'RANGING'
    confidence = min(1.0, max(0.0, 0.5 * trend_ratio + 0.5 * min(1.0, abs(short_mean - long_mean) / (average_range or 1))))
    return {'state': state, 'confidence': round(confidence, 3), 'reason': 'Deterministic OHLC range, displacement, and moving-average comparison.'}


def build_market_context(mt5, symbol: str, timeframe_name: str = 'M15', candle_count: int = 100) -> dict:
    timeframe = getattr(mt5, f'TIMEFRAME_{timeframe_name}', getattr(mt5, 'TIMEFRAME_M15', 15))
    tick = mt5.symbol_info_tick(symbol)
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, candle_count)
    candles = normalize_candles(rates)
    regime = classify_regime(candles)
    return {
        'symbol': symbol,
        'bid': float(getattr(tick, 'bid', 0) or 0) if tick else None,
        'ask': float(getattr(tick, 'ask', 0) or 0) if tick else None,
        'timeframe': timeframe_name,
        'candleCount': len(candles),
        'latestCandle': candles[-1] if candles else None,
        'regime': regime,
        'status': 'HEALTHY' if candles else 'UNAVAILABLE',
    }
