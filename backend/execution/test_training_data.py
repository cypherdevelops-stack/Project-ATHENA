from unittest.mock import patch

from django.test import SimpleTestCase

from .training_data import build_training_dataset


class TrainingDataTests(SimpleTestCase):
    def candles(self, count=20):
        return [
            {'open': 100, 'high': 101, 'low': 99, 'close': 100.5, 'time': index}
            for index in range(count)
        ]

    @patch('backend.execution.training_data.detect_setup_evidence', return_value={
        'sell_side_liquidity_swept': False, 'buy_side_liquidity_swept': False,
        'bullish_displacement': False, 'bearish_displacement': False,
        'bullish_mss': False, 'bearish_mss': False,
    })
    @patch('backend.execution.training_data.detect_features')
    def test_builds_point_in_time_samples_and_conservative_labels(self, detect_features, _detect_evidence):
        detect_features.return_value = {
            'structure': 'BULLISH',
            'orderBlocks': [{'type': 'OB', 'direction': 'BULLISH', 'lowerBound': 99, 'upperBound': 101, 'strength': 0.8}],
            'fairValueGaps': [],
        }
        candles = self.candles()
        candles[-1] = {'open': 100, 'high': 103, 'low': 98, 'close': 100.5, 'time': 19}

        samples, labels = build_training_dataset(m1_candles=candles, horizon=1)

        self.assertTrue(samples)
        self.assertEqual(len(samples), len(labels))
        self.assertTrue(all(label == 0 for label in labels))
        self.assertTrue(all(len(call.args[0]) <= len(candles) for call in detect_features.call_args_list))
