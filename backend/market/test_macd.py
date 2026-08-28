from django.test import SimpleTestCase

from .macd import MACDAnalyzer, MACDConfig


class MACDAnalyzerTests(SimpleTestCase):
    def test_insufficient_history_is_explicit(self):
        result = MACDAnalyzer().analyze([100.0] * 20)
        self.assertEqual(result.direction, 'UNKNOWN')
        self.assertEqual(result.confidence, 0.0)

    def test_trending_prices_produce_semantic_bullish_state(self):
        closes = [100 + index * 0.5 for index in range(80)]
        result = MACDAnalyzer().analyze(closes)
        self.assertEqual(result.direction, 'BULLISH')
        self.assertEqual(result.zero_line, 'ABOVE')
        self.assertEqual(result.signal_relationship, 'BULLISH')
        self.assertTrue(result.histogram_state.startswith('POSITIVE_'))
        self.assertIn(result.momentum, {'ACCELERATING', 'DECELERATING', 'STABLE'})
        self.assertGreater(result.confidence, 0)

    def test_signal_crossover_is_detected(self):
        closes = [100.0] * 40 + [100 - index * 0.8 for index in range(15)] + [88.0, 100.0]
        result = MACDAnalyzer().analyze(closes)
        self.assertEqual(result.signal_crossover, 'BULLISH')

    def test_output_is_serializable_with_semantic_keys(self):
        result = MACDAnalyzer().analyze([100 + index * 0.2 for index in range(60)])
        payload = result.as_dict()
        self.assertIn('zero_line', payload)
        self.assertIn('signalCrossover', payload)
        self.assertIn('histogramState', payload)
        self.assertGreaterEqual(len(payload['observations']), 3)
        self.assertIn('histogram', payload['observations'][2].lower())

    def test_non_finite_closes_are_rejected(self):
        with self.assertRaises(ValueError):
            MACDAnalyzer().analyze([100.0] * 34 + [float('nan')])

    def test_bearish_divergence_uses_confirmed_separated_swings(self):
        analyzer = MACDAnalyzer()
        divergence, strength = analyzer._divergence(
            [100, 102, 100, 101, 103, 101, 99],
            [0, 2, 0, 1, 1, 0, -1],
        )
        self.assertEqual(divergence, 'BEARISH')
        self.assertGreater(strength, 0)

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            MACDAnalyzer(MACDConfig(minimum_swing_separation=0))