import os
from unittest.mock import patch

from django.test import SimpleTestCase

from .model_training import DEFAULT_TRAINING_CANDLES, training_candle_count


class ModelTrainingConfigTests(SimpleTestCase):
    def test_training_defaults_to_larger_history(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(training_candle_count(), DEFAULT_TRAINING_CANDLES)

    def test_training_history_is_bounded(self):
        with patch.dict(os.environ, {'ATHENA_TRAINING_CANDLES': '12000'}):
            self.assertEqual(training_candle_count(), 10000)
        with patch.dict(os.environ, {'ATHENA_TRAINING_CANDLES': 'not-a-number'}):
            self.assertEqual(training_candle_count(), DEFAULT_TRAINING_CANDLES)
