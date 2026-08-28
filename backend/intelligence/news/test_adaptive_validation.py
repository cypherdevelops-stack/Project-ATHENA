from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from .adaptive_validation import validate_adaptive_candidate


class AdaptiveValidationTests(SimpleTestCase):
    def test_candidate_must_beat_chronological_baseline(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        observations = [
            {'timestamp': start + timedelta(days=index), 'label': index % 2}
            for index in range(40)
        ]
        result = validate_adaptive_candidate(
            observations=observations,
            candidate_predict=lambda item: item['label'],
            baseline_predict=lambda item: 0,
            model_version='test-1',
        )
        self.assertEqual(result.status, 'PROMOTE')
        self.assertEqual(result.train_count, 24)
        self.assertEqual(result.validation_count, 8)
        self.assertEqual(result.test_count, 8)

    def test_insufficient_history_never_promotes(self):
        result = validate_adaptive_candidate(
            observations=[{'timestamp': datetime(2026, 1, 1, tzinfo=timezone.utc), 'label': 1}],
            candidate_predict=lambda item: 1,
            baseline_predict=lambda item: 0,
            model_version='test-1',
        )
        self.assertEqual(result.status, 'INSUFFICIENT_HISTORY')
