from __future__ import annotations

from collections.abc import Iterable
from statistics import mean
from typing import Any


SMC_SCHEMA_VERSION = 'smc-evidence-v1'
DEFAULT_MIN_SAMPLES = 30


def _ordered(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(records, key=lambda record: (record.get('timestamp', 0), record.get('id', 0)))


def _classification_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    predicted = [bool(record.get('confirmed', record.get('signal', False))) for record in records]
    labels = [bool(record.get('outcome', record.get('label', False))) for record in records]
    true_positive = sum(prediction and label for prediction, label in zip(predicted, labels))
    true_negative = sum(not prediction and not label for prediction, label in zip(predicted, labels))
    false_positive = sum(prediction and not label for prediction, label in zip(predicted, labels))
    false_negative = sum(not prediction and label for prediction, label in zip(predicted, labels))
    predicted_positive = true_positive + false_positive
    actual_positive = true_positive + false_negative
    return {
        'truePositive': true_positive,
        'trueNegative': true_negative,
        'falsePositive': false_positive,
        'falseNegative': false_negative,
        'precision': round(true_positive / predicted_positive, 4) if predicted_positive else 0.0,
        'recall': round(true_positive / actual_positive, 4) if actual_positive else 0.0,
        'falseConfirmationRate': round(false_positive / predicted_positive, 4) if predicted_positive else 0.0,
        'accuracy': round((true_positive + true_negative) / len(records), 4) if records else 0.0,
    }


def evaluate_smc_records(
    records: Iterable[dict[str, Any]],
    *,
    min_samples: int = DEFAULT_MIN_SAMPLES,
    train_ratio: float = 0.8,
) -> dict[str, Any]:
    """Evaluate point-in-time SMC confirmations without changing live decisions."""
    if min_samples < 2:
        raise ValueError('min_samples must be at least 2.')
    if not 0.5 <= train_ratio < 1:
        raise ValueError('train_ratio must be at least 0.5 and below 1.')
    ordered = _ordered(records)
    result = {
        'schemaVersion': SMC_SCHEMA_VERSION,
        'status': 'INSUFFICIENT_SAMPLES',
        'sampleCount': len(ordered),
        'minimumSamples': min_samples,
        'trainSamples': 0,
        'validationSamples': 0,
        'metrics': {},
        'stalePoiRate': 0.0,
        'averageSlippage': 0.0,
        'weightAdjustment': 0.0,
        'adaptation': 'UNCHANGED',
    }
    if len(ordered) < min_samples:
        return result

    split = max(1, int(len(ordered) * train_ratio))
    validation = ordered[split:]
    if not validation:
        return result
    result.update({
        'status': 'VALIDATED',
        'trainSamples': split,
        'validationSamples': len(validation),
        'metrics': _classification_metrics(validation),
        'stalePoiRate': round(mean(bool(record.get('stale_poi', False)) for record in validation), 4),
        'averageSlippage': round(mean(float(record.get('slippage', 0.0)) for record in validation), 6),
    })
    precision = result['metrics']['precision']
    bounded_adjustment = max(-0.1, min(0.1, (precision - 0.5) * 0.2))
    result['weightAdjustment'] = round(bounded_adjustment, 4)
    result['adaptation'] = 'ADVISORY_ONLY'
    return result
