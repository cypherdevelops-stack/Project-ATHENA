from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean


@dataclass(frozen=True)
class RegimeContext:
    regime: str
    confidence: float
    htf_bias: str
    macd: str
    volatility: str
    structure: str
    price: float | None = None
    ema50: float | None = None
    ema200: float | None = None
    macd_value: float | None = None
    macd_signal: float | None = None
    reason: str = ''
    structure_reason: str = ''
    macd_reason: str = ''
    volatility_reason: str = ''

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload['macdValue'] = payload.pop('macd_value')
        payload['macdSignal'] = payload.pop('macd_signal')
        payload['ema50'] = payload.pop('ema50')
        payload['ema200'] = payload.pop('ema200')
        payload['structureReason'] = payload.pop('structure_reason')
        payload['macdReason'] = payload.pop('macd_reason')
        payload['volatilityReason'] = payload.pop('volatility_reason')
        return payload


def _ema(values: list[float], period: int) -> float:
    multiplier = 2 / (period + 1)
    result = values[0]
    for value in values[1:]:
        result = (value - result) * multiplier + result
    return result


def _macd(values: list[float]) -> tuple[float, float]:
    fast = []
    slow = []
    for index in range(len(values)):
        window = values[:index + 1]
        fast.append(_ema(window, min(12, len(window))))
        slow.append(_ema(window, min(26, len(window))))
    macd_values = [fast[index] - slow[index] for index in range(len(values))]
    return macd_values[-1], _ema(macd_values, min(9, len(macd_values)))


def evaluate_regime(candles: list[dict], timeframe: str = 'H1') -> RegimeContext:
    """Classify a higher-timeframe regime using deterministic price statistics."""
    if len(candles) < 200:
        return RegimeContext(
            regime='UNKNOWN', confidence=0.0, htf_bias='NEUTRAL', macd='UNKNOWN',
            volatility='UNKNOWN', structure='UNKNOWN',
            reason=f'{timeframe} regime requires at least 200 candles; received {len(candles)}.',
            structure_reason='Insufficient candle history to compare price with EMA50 and EMA200.',
            macd_reason='Insufficient candle history to calculate a reliable MACD relationship.',
            volatility_reason='Insufficient candle history to compare recent and baseline ranges.',
        )

    closes = [float(candle['close']) for candle in candles]
    ranges = [max(0.0, float(candle['high']) - float(candle['low'])) for candle in candles]
    price = closes[-1]
    ema50 = _ema(closes, 50)
    ema200 = _ema(closes, 200)
    macd_value, macd_signal = _macd(closes)
    macd_state = 'BULLISH' if macd_value > macd_signal else 'BEARISH' if macd_value < macd_signal else 'NEUTRAL'

    baseline_range = mean(ranges[-100:])
    recent_range = mean(ranges[-20:])
    volatility_ratio = recent_range / baseline_range if baseline_range else 0.0
    volatility = 'HIGH' if volatility_ratio >= 1.5 else 'LOW' if volatility_ratio <= 0.65 else 'NORMAL'

    bullish_structure = price > ema50 > ema200
    bearish_structure = price < ema50 < ema200
    structure = 'BULLISH' if bullish_structure else 'BEARISH' if bearish_structure else 'RANGING'
    structure_reason = (
        f'Price {price:.2f} is above EMA50 {ema50:.2f}, which is above EMA200 {ema200:.2f}.'
        if bullish_structure else f'Price {price:.2f} is below EMA50 {ema50:.2f}, which is below EMA200 {ema200:.2f}.'
        if bearish_structure else f'Price {price:.2f} is between EMA50 {ema50:.2f} and EMA200 {ema200:.2f}; the averages are not aligned for a trend.'
    )
    macd_reason = f'MACD {macd_value:.4f} is {"above" if macd_value > macd_signal else "below" if macd_value < macd_signal else "equal to"} signal {macd_signal:.4f}.'
    volatility_reason = f'Recent average range {recent_range:.2f} is {volatility_ratio:.2f}x the 100-candle baseline {baseline_range:.2f}; NORMAL is between 0.65x and 1.50x.'
    if bullish_structure and macd_state == 'BULLISH':
        regime = 'TRENDING_BULLISH'
        htf_bias = 'BUY'
    elif bearish_structure and macd_state == 'BEARISH':
        regime = 'TRENDING_BEARISH'
        htf_bias = 'SELL'
    else:
        regime = 'VOLATILE' if volatility == 'HIGH' else 'RANGING'
        htf_bias = 'NEUTRAL'

    confirmations = sum((bullish_structure or bearish_structure, macd_state in {'BULLISH', 'BEARISH'}, volatility == 'NORMAL'))
    confidence = round(min(0.95, 0.5 + confirmations * 0.15), 2)
    return RegimeContext(
        regime=regime, confidence=confidence, htf_bias=htf_bias, macd=macd_state,
        volatility=volatility, structure=structure, price=price, ema50=ema50,
        ema200=ema200, macd_value=macd_value, macd_signal=macd_signal,
        reason='Deterministic H1 EMA alignment, MACD relationship, and range volatility.',
        structure_reason=structure_reason, macd_reason=macd_reason, volatility_reason=volatility_reason,
    )
