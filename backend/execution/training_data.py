from __future__ import annotations

from backend.smc.detector import detect_features, detect_setup_evidence

from .xgboost_engine import build_feature_vector


def _setup_missing(*, direction: str, evidence: dict, in_poi: bool) -> list[str]:
    bullish = direction == 'BUY'
    checks = [
        ('LIQUIDITY_SWEEP', evidence['sell_side_liquidity_swept'] if bullish else evidence['buy_side_liquidity_swept']),
        ('DISPLACEMENT', evidence['bullish_displacement'] if bullish else evidence['bearish_displacement']),
        ('MSS', evidence['bullish_mss'] if bullish else evidence['bearish_mss']),
        ('POI_RETEST', in_poi),
    ]
    return [name for name, passed in checks if not passed]


def _label_future(*, direction: str, future: list[dict], entry: float, stop_loss: float, take_profit: float) -> int:
    for candle in future:
        stop_hit = candle['low'] <= stop_loss if direction == 'BUY' else candle['high'] >= stop_loss
        target_hit = candle['high'] >= take_profit if direction == 'BUY' else candle['low'] <= take_profit
        if stop_hit and target_hit:
            return 0
        if target_hit:
            return 1
        if stop_hit:
            return 0
    return 0


def build_training_dataset(*, m1_candles: list[dict], m5_candles: list[dict] | None = None, horizon: int = 12) -> tuple[list[list[float]], list[int]]:
    """Create leakage-resistant samples from candles and forward outcome labels."""
    if horizon < 1:
        raise ValueError('horizon must be at least 1.')
    samples, labels = [], []
    m5_candles = m5_candles or m1_candles
    for index in range(7, len(m1_candles) - horizon):
        history = m1_candles[:index + 1]
        features = detect_features(history, 'M1')
        pois = features.get('orderBlocks', []) + features.get('fairValueGaps', [])
        if not pois:
            continue
        poi = pois[-1]
        direction = 'BUY' if poi['direction'] == 'BULLISH' else 'SELL'
        entry = history[-1]['close']
        width = max(poi['upperBound'] - poi['lowerBound'], 1e-9)
        stop_loss = poi['lowerBound'] - width * 0.5 if direction == 'BUY' else poi['upperBound'] + width * 0.5
        take_profit = poi['upperBound'] + width * 2 if direction == 'BUY' else poi['lowerBound'] - width * 2
        in_poi = poi['lowerBound'] <= entry <= poi['upperBound']
        evidence = detect_setup_evidence(history)
        context = {
            **evidence,
            'm1_structure': features.get('structure'),
            'session_aligned': True,
            'spread_ok': True,
            'volatility': 'NORMAL',
            'correlation_allowed': True,
        }
        candidate = {
            'direction': direction,
            'regimeContext': detect_features(m5_candles[:min(len(m5_candles), index + 1)], 'M5').get('structure'),
            'entryZone': {'lower': poi['lowerBound'], 'upper': poi['upperBound']},
            'currentPrice': entry,
            'strength': poi.get('strength', 0),
            'score': 0,
            'setup': {'missing': _setup_missing(direction=direction, evidence=evidence, in_poi=in_poi)},
        }
        samples.append(build_feature_vector(candidate=candidate, context=context))
        labels.append(_label_future(direction=direction, future=m1_candles[index + 1:index + 1 + horizon], entry=entry, stop_loss=stop_loss, take_profit=take_profit))
    return samples, labels
