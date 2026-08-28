from __future__ import annotations

from dataclasses import dataclass

from .macd import MACDAnalyzer


DEFAULT_TIMEFRAMES = ('H4', 'H1', 'M15', 'M5')


@dataclass(frozen=True)
class MomentumMap:
    timeframes: dict
    alignment: str
    interpretation: str
    confidence: float
    directional_scores: dict

    def as_dict(self) -> dict:
        return {
            'timeframes': self.timeframes,
            'alignment': self.alignment,
            'interpretation': self.interpretation,
            'confidence': self.confidence,
            'directionalScores': self.directional_scores,
        }


def build_momentum_map(
    candles_by_timeframe: dict[str, list[dict]],
    *,
    structure_by_timeframe: dict[str, str] | None = None,
    timeframes: tuple[str, ...] = DEFAULT_TIMEFRAMES,
    analyzer: MACDAnalyzer | None = None,
) -> MomentumMap:
    """Analyze configured timeframes without converting momentum into a trade signal."""
    analyzer = analyzer or MACDAnalyzer()
    structures = structure_by_timeframe or {}
    analyses = {
        timeframe: analyzer.analyze_candles(candles_by_timeframe.get(timeframe, [])).as_dict()
        for timeframe in timeframes
    }
    known = [analysis for analysis in analyses.values() if analysis['direction'] in {'BULLISH', 'BEARISH'}]
    if not known:
        return MomentumMap(
            timeframes=analyses, alignment='UNKNOWN',
            interpretation='Momentum alignment is unavailable because no configured timeframe has sufficient data.',
            confidence=0.0, directional_scores={'BUY': 0.0, 'SELL': 0.0},
        )

    higher_index = next((index for index, timeframe in enumerate(timeframes[:2]) if analyses[timeframe]['direction'] in {'BULLISH', 'BEARISH'}), 0)
    higher = analyses[timeframes[higher_index]]
    higher_direction = higher['direction']
    lower = [
        analyses[timeframe]
        for timeframe in timeframes[higher_index + 1:]
        if analyses[timeframe]['direction'] in {'BULLISH', 'BEARISH'}
    ]
    same_count = sum(analysis['direction'] == higher_direction for analysis in known)
    opposite_count = len(known) - same_count
    if opposite_count == 0:
        alignment = 'ALIGNED'
        interpretation = f'{higher_direction.title()} momentum is aligned across available timeframes.'
    elif lower and opposite_count == len(lower) and structures.get(timeframes[1], higher_direction) == higher_direction:
        alignment = 'LIKELY_RETRACEMENT'
        interpretation = f'Lower-timeframe momentum opposes {higher_direction.lower()} higher-timeframe context; treat as a possible retracement pending structure confirmation.'
    else:
        alignment = 'CONFLICTING'
        interpretation = 'Momentum timeframes conflict; structure and location must resolve whether this is noise, retracement, or reversal risk.'

    divergence_risk = any(
        analysis['divergence'] == ('BEARISH' if higher_direction == 'BULLISH' else 'BULLISH')
        for analysis in analyses.values()
    )
    if divergence_risk and alignment != 'ALIGNED':
        alignment = 'POTENTIAL_REVERSAL'
        interpretation = f'{higher_direction.title()} higher-timeframe momentum conflicts with divergence evidence; monitor for structural reversal confirmation.'

    scores = {'BUY': 0.0, 'SELL': 0.0}
    for analysis in known:
        weight = 1.0 if analysis is higher else 0.5
        scores['BUY' if analysis['direction'] == 'BULLISH' else 'SELL'] += weight * analysis['confidence']
    total = scores['BUY'] + scores['SELL']
    confidence = round(min(1.0, max(scores.values()) / total if total else 0.0), 3)
    return MomentumMap(
        timeframes=analyses,
        alignment=alignment,
        interpretation=interpretation,
        confidence=confidence,
        directional_scores={key: round(min(1.0, value / max(1.5, len(known))), 3) for key, value in scores.items()},
    )


def momentum_evidence(momentum_map: MomentumMap | dict | None, direction: str) -> dict:
    """Return a bounded advisory contribution for a candidate direction."""
    payload = momentum_map.as_dict() if isinstance(momentum_map, MomentumMap) else momentum_map or {}
    normalized = 'BUY' if direction in {'BUY', 'BULLISH'} else 'SELL'
    score = float((payload.get('directionalScores') or {}).get(normalized, 0.0))
    alignment = payload.get('alignment', 'UNKNOWN')
    if alignment == 'POTENTIAL_REVERSAL':
        score *= 0.25
    elif alignment == 'CONFLICTING':
        score *= 0.5
    return {
        'score': round(min(1.0, max(0.0, score)), 3),
        'points': round(min(5.0, max(0.0, score * 5)), 2),
        'alignment': alignment,
        'reason': payload.get('interpretation', 'Momentum context is unavailable.'),
    }