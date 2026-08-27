from unittest.mock import patch

from django.test import SimpleTestCase

from .model_validation import validate_samples


class ModelValidationTests(SimpleTestCase):
    @patch('backend.execution.model_validation.XGBoostEngine')
    def test_validation_uses_later_holdout_and_reports_metrics(self, engine_class):
        engine = engine_class.return_value
        engine.train.return_value = {'status': 'TRAINED'}
        engine.model.predict_proba.return_value = [[0.1, 0.9], [0.9, 0.1], [0.2, 0.8], [0.8, 0.2]]
        samples = [[float(index)] for index in range(10)]
        labels = [0, 1, 0, 1, 0, 1, 0, 1, 1, 0]

        result = validate_samples(samples=samples, labels=labels, train_ratio=0.6)

        self.assertEqual(result['trainSamples'], 6)
        self.assertEqual(result['validationSamples'], 4)
        engine.train.assert_called_once_with(samples[:6], labels[:6])
        self.assertEqual(result['predictedTrades'], 2)
        self.assertEqual(result['winRate'], 0.5)

    def test_validation_rejects_single_class_holdout(self):
        with self.assertRaisesRegex(Exception, 'both positive and negative'):
            validate_samples(samples=[[float(index)] for index in range(10)], labels=[0] * 8 + [1, 1])
