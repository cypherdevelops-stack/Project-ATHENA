from django.test import SimpleTestCase

from .regime import evaluate_regime


class RegimeEngineTests(SimpleTestCase):
    def _candles(self, closes, spread=1.0):
        return [
            {
                'time': index,
                'open': close - 0.1,
                'high': close + spread,
                'low': close - spread,
                'close': close,
                'volume': 100,
            }
            for index, close in enumerate(closes)
        ]

    def test_insufficient_h1_data_is_unknown(self):
        result = evaluate_regime(self._candles([100 + index for index in range(50)]))
        self.assertEqual(result.regime, 'UNKNOWN')
        self.assertEqual(result.htf_bias, 'NEUTRAL')
        self.assertIn('Insufficient candle history', result.structure_reason)
        self.assertIn('Insufficient candle history', result.macd_reason)

    def test_bullish_ema_alignment_produces_bullish_regime(self):
        closes = [100 + index * 0.05 for index in range(200)]
        result = evaluate_regime(self._candles(closes))
        self.assertEqual(result.regime, 'TRENDING_BULLISH')
        self.assertEqual(result.htf_bias, 'BUY')
        self.assertEqual(result.macd, 'BULLISH')
        self.assertEqual(result.structure, 'BULLISH')
        self.assertGreater(result.confidence, 0)
        self.assertIn('Price', result.structure_reason)
        self.assertIn('MACD', result.macd_reason)
        self.assertIn('baseline', result.volatility_reason)

    def test_flat_market_is_ranging(self):
        candles = self._candles([100.0] * 180, spread=2.0) + self._candles([100.0] * 20, spread=0.2)
        result = evaluate_regime(candles)
        self.assertEqual(result.regime, 'RANGING')
        self.assertEqual(result.htf_bias, 'NEUTRAL')
        self.assertEqual(result.volatility, 'LOW')
        self.assertIn('EMA50', result.structure_reason)
        self.assertIn('signal', result.macd_reason)
        self.assertIn('baseline', result.volatility_reason)

    def test_regime_dict_exposes_explanations(self):
        result = evaluate_regime(self._candles([100 + index * 0.05 for index in range(200)]))
        payload = result.as_dict()
        self.assertIn('structureReason', payload)
        self.assertIn('macdReason', payload)
        self.assertIn('volatilityReason', payload)
