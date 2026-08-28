from django.test import SimpleTestCase

from .scripts.analyzer import detect_features
from .scripts.validation import SMC_SCHEMA_VERSION, evaluate_smc_records


class SMCValidationTests(SimpleTestCase):
    def test_insufficient_samples_do_not_change_weight(self):
        result = evaluate_smc_records(
            [{'timestamp': 1, 'confirmed': True, 'outcome': True}],
            min_samples=2,
        )

        self.assertEqual(result['status'], 'INSUFFICIENT_SAMPLES')
        self.assertEqual(result['weightAdjustment'], 0.0)
        self.assertEqual(result['adaptation'], 'UNCHANGED')

    def test_validation_uses_chronological_holdout_and_bounded_weight(self):
        records = [
            {'timestamp': timestamp, 'confirmed': timestamp % 2 == 0, 'outcome': timestamp % 3 != 0,
             'stale_poi': timestamp == 9, 'slippage': timestamp / 1000}
            for timestamp in reversed(range(10))
        ]

        result = evaluate_smc_records(records, min_samples=10, train_ratio=0.6)

        self.assertEqual(result['status'], 'VALIDATED')
        self.assertEqual(result['trainSamples'], 6)
        self.assertEqual(result['validationSamples'], 4)
        self.assertEqual(result['adaptation'], 'ADVISORY_ONLY')
        self.assertLessEqual(abs(result['weightAdjustment']), 0.1)
        self.assertEqual(result['stalePoiRate'], 0.25)
        self.assertEqual(result['averageSlippage'], 0.0075)

    def test_analysis_outputs_schema_version(self):
        candles = [
            {'open': 10, 'close': 10.5, 'high': 11, 'low': 9, 'time': index}
            for index in range(5)
        ]

        result = detect_features(candles, 'M1')

        self.assertEqual(result['schemaVersion'], SMC_SCHEMA_VERSION)
