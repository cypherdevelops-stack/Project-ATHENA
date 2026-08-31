from __future__ import annotations

from .analyzer import detect_features, detect_setup_evidence
from .lifecycle import active_pois, enrich_poi
from .validation import SMC_SCHEMA_VERSION

DEFAULT_SMC_TIMEFRAMES = ('H4', 'H1', 'M15', 'M5', 'M1')


def _direction(structure: str) -> str | None:
    return {'BULLISH': 'BUY', 'BEARISH': 'SELL'}.get(structure)


def analyze_multi_timeframe(
    candles_by_timeframe: dict[str, list[dict]],
    *,
    timeframes: tuple[str, ...] = DEFAULT_SMC_TIMEFRAMES,
    current_time: float | int | str | None = None,
    poi_max_age_seconds: float | None = None,
    momentum_map: dict | None = None,
) -> dict:
    """Build independent SMC analyses and an explicit cross-timeframe summary."""
    analyses = {}
    for timeframe in timeframes:
        candles = candles_by_timeframe.get(timeframe, [])
        features = detect_features(candles, timeframe)
        enriched = {
            **features,
            'bias': _direction(features['structure']),
            'latestConfirmedEvent': features['events'][-1] if features['events'] else None,
            'dataQuality': features['status'],
            'liquidity': detect_setup_evidence(candles) if len(candles) >= 7 else {},
            'orderBlocks': [
                enrich_poi(poi, current_time=current_time, max_age_seconds=poi_max_age_seconds)
                for poi in features['orderBlocks']
            ],
            'fairValueGaps': [
                enrich_poi(poi, current_time=current_time, max_age_seconds=poi_max_age_seconds)
                for poi in features['fairValueGaps']
            ],
        }
        enriched['activePois'] = active_pois(enriched['orderBlocks'] + enriched['fairValueGaps'])
        analyses[timeframe] = enriched

    known = [
        (timeframe, analysis['bias'])
        for timeframe, analysis in analyses.items()
        if analysis['bias']
    ]
    higher = next(((timeframe, bias) for timeframe, bias in known[:2]), None)
    if not known:
        alignment = 'UNKNOWN'
        interpretation = 'SMC alignment is unavailable because no configured timeframe has directional structure.'
    elif len({bias for _, bias in known}) == 1:
        alignment = 'ALIGNED'
        interpretation = f'{higher[1]} structure is aligned across available timeframes.'
    else:
        higher_bias = higher[1]
        lower_biases = [bias for timeframe, bias in known if timeframe != higher[0]]
        if lower_biases and all(bias != higher_bias for bias in lower_biases):
            alignment = 'CONFLICTING'
            interpretation = f'Lower-timeframe SMC structure opposes {higher_bias} higher-timeframe context; this may be a retracement, but confirmation is required before treating it as reversal.'
        else:
            alignment = 'CONFLICTING'
            interpretation = 'SMC timeframes conflict; retain each timeframe and require location and confirmation to resolve the context.'

    return {
        'schemaVersion': SMC_SCHEMA_VERSION,
        'status': 'READY' if any(analysis['status'] == 'READY' for analysis in analyses.values()) else 'INSUFFICIENT_DATA',
        'timeframes': analyses,
        'higherTimeframe': higher[0] if higher else None,
        'higherTimeframeBias': higher[1] if higher else None,
        'alignment': alignment,
        'interpretation': interpretation,
        'momentumMap': momentum_map,
    }
