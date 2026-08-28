from django.test import SimpleTestCase

from .momentum import build_momentum_map, momentum_evidence


class MomentumMapTests(SimpleTestCase):
    @staticmethod
    def _candles(closes):
        return [
            {'time': index, 'open': close, 'high': close + 1, 'low': close - 1, 'close': close, 'volume': 100}
            for index, close in enumerate(closes)
        ]

    def test_higher_bullish_and_lower_bearish_is_retracement_context(self):
        rising = self._candles([100 + index * 0.5 for index in range(80)])
        falling = self._candles([140 - index * 0.5 for index in range(80)])
        result = build_momentum_map(
            {'H1': rising, 'M15': falling},
            structure_by_timeframe={'H1': 'BULLISH'},
            timeframes=('H1', 'M15'),
        )
        self.assertEqual(result.alignment, 'LIKELY_RETRACEMENT')
        self.assertIn('retracement', result.interpretation)

    def test_missing_timeframes_are_explicitly_unknown(self):
        result = build_momentum_map({}, timeframes=('H4', 'H1', 'M15', 'M5'))
        self.assertEqual(result.alignment, 'UNKNOWN')
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.timeframes['H4']['direction'], 'UNKNOWN')

    def test_conflicting_context_caps_candidate_contribution(self):
        result = momentum_evidence({
            'alignment': 'CONFLICTING',
            'directionalScores': {'BUY': 1.0, 'SELL': 0.0},
            'interpretation': 'Conflict requires confirmation.',
        }, 'BUY')
        self.assertEqual(result['points'], 2.5)
        self.assertIn('confirmation', result['reason'])