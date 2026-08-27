from __future__ import annotations

from .xgboost_engine import XGBoostEngine, XGBoostEngineError


def _metrics(*, probabilities: list[float], labels: list[int], train_samples: int) -> dict:
    predictions = [int(probability >= 0.5) for probability in probabilities]
    true_positive = sum(prediction == label == 1 for prediction, label in zip(predictions, labels))
    true_negative = sum(prediction == label == 0 for prediction, label in zip(predictions, labels))
    false_positive = sum(prediction == 1 and label == 0 for prediction, label in zip(predictions, labels))
    false_negative = sum(prediction == 0 and label == 1 for prediction, label in zip(predictions, labels))
    total = len(labels)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
    predicted_trades = true_positive + false_positive
    return {
        'status': 'VALIDATED', 'trainSamples': train_samples, 'validationSamples': total,
        'trainPositiveLabels': None, 'validationPositiveLabels': sum(labels),
        'accuracy': round((true_positive + true_negative) / total, 4),
        'precision': round(precision, 4), 'recall': round(recall, 4),
        'winRate': round(true_positive / predicted_trades if predicted_trades else 0, 4),
        'predictedTrades': predicted_trades,
        'confusionMatrix': {'truePositive': true_positive, 'trueNegative': true_negative, 'falsePositive': false_positive, 'falseNegative': false_negative},
    }


def validate_engine(*, engine: XGBoostEngine, train_samples: list[list[float]], train_labels: list[int], test_samples: list[list[float]], test_labels: list[int]) -> dict:
    if not test_samples or len(set(test_labels)) < 2:
        raise XGBoostEngineError('Validation window requires both positive and negative labels.')
    result = _metrics(probabilities=[row[1] for row in engine.model.predict_proba(test_samples)], labels=test_labels, train_samples=len(train_samples))
    result['trainPositiveLabels'] = sum(train_labels)
    return result


def validate_samples(*, samples: list[list[float]], labels: list[int], train_ratio: float = 0.8, engine: XGBoostEngine | None = None) -> dict:
    """Evaluate a chronological holdout; samples must already be ordered by time."""
    if len(samples) != len(labels) or not samples:
        raise XGBoostEngineError('Validation samples and labels must be non-empty and have equal length.')
    if not 0.5 <= train_ratio < 1:
        raise ValueError('train_ratio must be at least 0.5 and below 1.')
    split = int(len(samples) * train_ratio)
    train_samples, test_samples = samples[:split], samples[split:]
    train_labels, test_labels = labels[:split], labels[split:]
    if len(set(train_labels)) < 2:
        raise XGBoostEngineError('Training window requires both positive and negative labels.')
    if not test_samples or len(set(test_labels)) < 2:
        raise XGBoostEngineError('Validation window requires both positive and negative labels.')

    if engine is None:
        engine = XGBoostEngine()
        engine.train(train_samples, train_labels)
    return validate_engine(engine=engine, train_samples=train_samples, train_labels=train_labels, test_samples=test_samples, test_labels=test_labels)
