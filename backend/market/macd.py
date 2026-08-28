from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from statistics import mean


@dataclass(frozen=True)
class MACDConfig:
    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9
    divergence_lookback: int = 40
    momentum_lookback: int = 3
    minimum_swing_separation: int = 2
    minimum_divergence_strength: float = 0.01


@dataclass(frozen=True)
class MACDAnalysis:
    direction: str
    zero_line: str
    signal_relationship: str
    signal_crossover: str
    histogram_state: str
    momentum: str
    divergence: str
    divergence_strength: float
    exhaustion: str
    confidence: float
    macd: float | None = None
    signal: float | None = None
    histogram: float | None = None
    reason: str = ''
    observations: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload['signalRelationship'] = payload.pop('signal_relationship')
        payload['signalCrossover'] = payload.pop('signal_crossover')
        payload['histogramState'] = payload.pop('histogram_state')
        payload['divergenceStrength'] = payload.pop('divergence_strength')
        payload['observations'] = list(payload['observations'])
        return payload


def _ema(values: list[float], period: int) -> list[float]:
    multiplier = 2 / (period + 1)
    result = values[0]
    output = [result]
    for value in values[1:]:
        result = (value - result) * multiplier + result
        output.append(result)
    return output


def _local_extreme(values: list[float], index: int, mode: str) -> bool:
    if index < 1 or index >= len(values) - 1:
        return False
    if mode == 'HIGH':
        return values[index] >= values[index - 1] and values[index] > values[index + 1]
    return values[index] <= values[index - 1] and values[index] < values[index + 1]


class MACDAnalyzer:
    """Derive contextual MACD evidence; never emits a trade decision."""

    def __init__(self, config: MACDConfig | None = None):
        self.config = config or MACDConfig()
        if (
            self.config.fast_period <= 0
            or self.config.slow_period <= self.config.fast_period
            or self.config.signal_period <= 0
            or self.config.momentum_lookback <= 0
            or self.config.divergence_lookback < self.config.minimum_swing_separation * 2
            or self.config.minimum_swing_separation <= 0
            or not 0 <= self.config.minimum_divergence_strength <= 1
        ):
            raise ValueError('MACD periods must be positive and slow_period must exceed fast_period.')

    def analyze_candles(self, candles: list[dict]) -> MACDAnalysis:
        return self.analyze([float(candle['close']) for candle in candles])

    def analyze(self, closes: list[float]) -> MACDAnalysis:
        minimum = self.config.slow_period + self.config.signal_period
        if len(closes) < minimum:
            return MACDAnalysis(
                direction='UNKNOWN', zero_line='UNKNOWN', signal_relationship='UNKNOWN',
                signal_crossover='NONE', histogram_state='UNKNOWN', momentum='UNKNOWN',
                divergence='NONE', divergence_strength=0.0, exhaustion='NONE', confidence=0.0,
                reason=f'MACD requires at least {minimum} closes; received {len(closes)}.',
                observations=('Insufficient history: no MACD market interpretation is available.',),
            )
        if any(not isfinite(value) for value in closes):
            raise ValueError('MACD closes must contain only finite numbers.')

        fast = _ema(closes, self.config.fast_period)
        slow = _ema(closes, self.config.slow_period)
        macd_values = [fast[index] - slow[index] for index in range(len(closes))]
        signal_values = _ema(macd_values, self.config.signal_period)
        histogram_values = [macd_values[index] - signal_values[index] for index in range(len(closes))]
        macd = macd_values[-1]
        signal = signal_values[-1]
        histogram = histogram_values[-1]
        momentum_start = max(0, len(histogram_values) - self.config.momentum_lookback - 1)
        previous_histogram = histogram_values[momentum_start]
        relationship = 'BULLISH' if macd > signal else 'BEARISH' if macd < signal else 'NEUTRAL'
        direction = relationship
        zero_line = 'ABOVE' if macd > 0 else 'BELOW' if macd < 0 else 'AT'
        crossover = (
            'BULLISH' if macd > signal and macd_values[-2] <= signal_values[-2]
            else 'BEARISH' if macd < signal and macd_values[-2] >= signal_values[-2]
            else 'NONE'
        )
        histogram_polarity = 'POSITIVE' if histogram > 0 else 'NEGATIVE' if histogram < 0 else 'ZERO'
        histogram_expanding = abs(histogram) > abs(previous_histogram)
        histogram_state = (
            f'{histogram_polarity}_EXPANDING' if histogram_expanding and histogram != 0
            else f'{histogram_polarity}_CONTRACTING' if histogram != 0 and abs(histogram) < abs(previous_histogram)
            else 'ZERO'
        )
        if histogram == 0 or histogram == previous_histogram:
            momentum = 'STABLE'
        elif histogram_expanding:
            momentum = 'ACCELERATING'
        else:
            momentum = 'DECELERATING'
        divergence, strength = self._divergence(closes, macd_values)
        exhaustion = 'NONE'
        if divergence == 'BEARISH' and direction == 'BULLISH':
            exhaustion = 'BULLISH_EXHAUSTION_RISK'
        elif divergence == 'BULLISH' and direction == 'BEARISH':
            exhaustion = 'BEARISH_EXHAUSTION_RISK'
        confidence = round(min(1.0, 0.35 + (0.2 if direction != 'NEUTRAL' else 0) + (0.15 if zero_line != 'AT' else 0) + strength * 0.3), 3)
        observations = [
            f'Momentum is {direction.lower()} because MACD is {"above" if macd > signal else "below" if macd < signal else "equal to"} its signal line.',
            f'MACD is {zero_line.lower()} zero, so the broader momentum bias is {"positive" if macd > 0 else "negative" if macd < 0 else "neutral"}.',
            f'The histogram is {histogram_state.lower().replace("_", " ")}; momentum is {momentum.lower()}.',
        ]
        if crossover != 'NONE':
            observations.append(f'A {crossover.lower()} signal-line crossover occurred on the latest completed candle.')
        if divergence != 'NONE':
            observations.append(f'{divergence.title()} divergence is present with strength {strength:.2f}; this is exhaustion evidence, not reversal confirmation.')
        if exhaustion != 'NONE':
            observations.append(f'{exhaustion.replace("_", " ").title()} requires structure, liquidity, and price-action confirmation.')
        return MACDAnalysis(
            direction=direction, zero_line=zero_line, signal_relationship=relationship,
            signal_crossover=crossover, histogram_state=histogram_state,
            momentum=momentum, divergence=divergence, divergence_strength=round(strength, 3),
            exhaustion=exhaustion, confidence=confidence, macd=macd, signal=signal,
            histogram=histogram,
            reason=' '.join(observations),
            observations=tuple(observations),
        )

    def _divergence(self, closes: list[float], macd_values: list[float]) -> tuple[str, float]:
        lookback = min(self.config.divergence_lookback, len(closes) - 1)
        start = len(closes) - lookback - 1
        price_window = closes[start:]
        macd_window = macd_values[start:]
        highs = [index for index in range(1, len(price_window) - 1) if _local_extreme(price_window, index, 'HIGH')]
        lows = [index for index in range(1, len(price_window) - 1) if _local_extreme(price_window, index, 'LOW')]
        if len(highs) >= 2:
            first, second = highs[-2:]
            if second - first >= self.config.minimum_swing_separation and price_window[second] > price_window[first] and macd_window[second] < macd_window[first]:
                strength = self._strength(price_window[first], price_window[second], macd_window[first], macd_window[second])
                if strength >= self.config.minimum_divergence_strength:
                    return 'BEARISH', strength
        if len(lows) >= 2:
            first, second = lows[-2:]
            if second - first >= self.config.minimum_swing_separation and price_window[second] < price_window[first] and macd_window[second] > macd_window[first]:
                strength = self._strength(price_window[first], price_window[second], macd_window[first], macd_window[second])
                if strength >= self.config.minimum_divergence_strength:
                    return 'BULLISH', strength
        return 'NONE', 0.0

    @staticmethod
    def _strength(first_price: float, second_price: float, first_macd: float, second_macd: float) -> float:
        price_scale = max(abs(first_price), abs(second_price), 1e-9)
        macd_scale = max(abs(first_macd), abs(second_macd), 1e-9)
        return min(1.0, mean((abs(second_price - first_price) / price_scale, abs(second_macd - first_macd) / macd_scale)))