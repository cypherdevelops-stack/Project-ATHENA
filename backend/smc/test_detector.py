from django.test import SimpleTestCase

from .detector import detect_entry_confirmation, detect_setup_evidence


class SetupEvidenceTests(SimpleTestCase):
    def test_bullish_candle_sweeps_sell_side_and_confirms_structure(self):
        candles = [
            {'open': 10, 'close': 10.5, 'high': 11, 'low': 9, 'time': index}
            for index in range(8)
        ]
        candles[4]['low'] = 8
        candles.append({'open': 8, 'close': 12, 'high': 12.5, 'low': 7, 'time': 8})

        evidence = detect_setup_evidence(candles)

        self.assertTrue(evidence['sell_side_liquidity_swept'])
        self.assertTrue(evidence['bullish_displacement'])
        self.assertTrue(evidence['bullish_mss'])
        self.assertFalse(evidence['buy_side_liquidity_swept'])

    def test_insufficient_candles_produce_no_positive_evidence(self):
        evidence = detect_setup_evidence([{'open': 1, 'close': 1, 'high': 1, 'low': 1, 'time': 1}] * 6)

        self.assertTrue(all(value is False for value in evidence.values()))

    def test_bullish_poi_confirmation_requires_all_price_action_checks(self):
        candles = [
            {'open': 100, 'close': 100.1, 'high': 100.2, 'low': 99.9, 'time': index}
            for index in range(5)
        ]
        candles[-2] = {'open': 99.8, 'close': 99.9, 'high': 100, 'low': 99.5, 'time': 3}
        candles[-1] = {'open': 99.9, 'close': 100.6, 'high': 100.8, 'low': 99.2, 'time': 4}

        result = detect_entry_confirmation(
            candles=candles,
            poi={'lowerBound': 99.5, 'upperBound': 100.2},
            direction='BUY',
        )

        self.assertTrue(result['in_poi'])
        self.assertTrue(result['rejection'])
        self.assertTrue(result['micro_mss'])
        self.assertTrue(result['momentum'])
        self.assertTrue(result['entry_confirmation'])
