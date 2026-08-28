from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable


MOMENTUM_SCHEMA_VERSION = 'macd-momentum-v1'


def build_momentum_snapshot(analysis: dict[str, Any]) -> dict[str, Any]:
    """Create the point-in-time momentum context stored with an orchestration decision."""
    momentum_map = analysis.get('momentumMap') or {}
    return {
        'schemaVersion': MOMENTUM_SCHEMA_VERSION,
        'capturedAt': datetime.now(timezone.utc).isoformat(),
        'alignment': momentum_map.get('alignment', 'UNKNOWN'),
        'interpretation': momentum_map.get('interpretation', ''),
        'confidence': float(momentum_map.get('confidence', 0.0)),
        'directionalScores': momentum_map.get('directionalScores', {}),
        'timeframes': momentum_map.get('timeframes', {}),
    }


def summarize_momentum_outcomes(
    records: Iterable[dict[str, Any]],
    *,
    minimum_samples: int = 5,
    model_version: str = MOMENTUM_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Summarize closed outcomes without allowing small samples to change weighting."""
    if minimum_samples < 1:
        raise ValueError('minimum_samples must be at least 1.')
    grouped: defaultdict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get('outcome') not in {'WIN', 'LOSS'}:
            continue
        momentum = record.get('momentumSnapshot') or {}
        key = (
            str(record.get('symbol', 'UNKNOWN')),
            str(record.get('timeframe', 'UNKNOWN')),
            str(momentum.get('alignment', 'UNKNOWN')),
            str(record.get('direction', 'UNKNOWN')),
        )
        grouped[key].append(record)

    results = {}
    for key, samples in grouped.items():
        wins = sum(sample['outcome'] == 'WIN' for sample in samples)
        average_r = sum(float(sample.get('rMultiple', 0.0)) for sample in samples) / len(samples)
        eligible = len(samples) >= minimum_samples
        win_rate = wins / len(samples)
        # Advisory only: eligible groups can move a score by at most 25%.
        weight = 1.0 + max(-0.25, min(0.25, (win_rate - 0.5) * 0.5)) if eligible else 1.0
        results['|'.join(key)] = {
            'symbol': key[0], 'timeframe': key[1], 'alignment': key[2], 'direction': key[3],
            'samples': len(samples), 'wins': wins, 'losses': len(samples) - wins,
            'winRate': round(win_rate, 4), 'averageRMultiple': round(average_r, 4),
            'eligible': eligible, 'advisoryWeight': round(weight, 4),
            'modelVersion': model_version,
        }
    return {
        'schemaVersion': MOMENTUM_SCHEMA_VERSION,
        'modelVersion': model_version,
        'minimumSamples': minimum_samples,
        'groups': results,
    }