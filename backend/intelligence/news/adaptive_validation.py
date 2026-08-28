from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ValidationResult:
    status: str
    reason: str
    train_count: int
    validation_count: int
    test_count: int
    baseline_accuracy: float
    candidate_accuracy: float
    model_version: str
    training_period: dict[str, str | None]

    def as_dict(self) -> dict:
        return {
            'status': self.status,
            'reason': self.reason,
            'trainCount': self.train_count,
            'validationCount': self.validation_count,
            'testCount': self.test_count,
            'baselineAccuracy': self.baseline_accuracy,
            'candidateAccuracy': self.candidate_accuracy,
            'modelVersion': self.model_version,
            'trainingPeriod': self.training_period,
        }


def validate_adaptive_candidate(*, observations: list[dict], candidate_predict, baseline_predict, model_version: str, minimum_samples: int = 30, train_ratio: float = 0.6, validation_ratio: float = 0.2) -> ValidationResult:
    ordered = sorted(observations, key=lambda item: _timestamp(item.get('timestamp')))
    if len(ordered) < minimum_samples:
        return ValidationResult('INSUFFICIENT_HISTORY', f'{minimum_samples} chronological observations are required.', len(ordered), 0, 0, 0.0, 0.0, model_version, {'from': None, 'to': None})
    if not 0 < train_ratio < 1 or not 0 < validation_ratio < 1 or train_ratio + validation_ratio >= 1:
        raise ValueError('train_ratio and validation_ratio must leave a test window.')
    train_end = int(len(ordered) * train_ratio)
    validation_end = train_end + int(len(ordered) * validation_ratio)
    train, validation, test = ordered[:train_end], ordered[train_end:validation_end], ordered[validation_end:]
    if not validation or not test:
        return ValidationResult('INSUFFICIENT_HISTORY', 'Chronological validation and test windows are required.', len(train), len(validation), len(test), 0.0, 0.0, model_version, _period(ordered))
    labels = [int(item['label']) for item in test]
    baseline = [int(baseline_predict(item)) for item in test]
    candidate = [int(candidate_predict(item)) for item in test]
    baseline_accuracy = _accuracy(baseline, labels)
    candidate_accuracy = _accuracy(candidate, labels)
    status = 'PROMOTE' if candidate_accuracy > baseline_accuracy else 'REJECT'
    return ValidationResult(status, 'Candidate improves the deterministic baseline.' if status == 'PROMOTE' else 'Candidate did not improve the deterministic baseline.', len(train), len(validation), len(test), baseline_accuracy, candidate_accuracy, model_version, _period(ordered))


def _timestamp(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace('Z', '+00:00'))


def _period(observations: list[dict]) -> dict[str, str | None]:
    return {'from': _timestamp(observations[0]['timestamp']).isoformat(), 'to': _timestamp(observations[-1]['timestamp']).isoformat()}


def _accuracy(predictions: list[int], labels: list[int]) -> float:
    return round(sum(prediction == label for prediction, label in zip(predictions, labels)) / len(labels), 4)