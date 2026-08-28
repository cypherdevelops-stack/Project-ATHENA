from django.test import SimpleTestCase

from .momentum_amef import build_momentum_snapshot, summarize_momentum_outcomes


class MomentumAMEFTests(SimpleTestCase):
    def test_snapshot_is_versioned_and_preserves_timeframe_context(self):
        snapshot = build_momentum_snapshot({'momentumMap': {
            'alignment': 'ALIGNED', 'confidence': 0.8,
            'directionalScores': {'BUY': 0.8}, 'timeframes': {'H1': {'direction': 'BULLISH'}},
        }})
        self.assertEqual(snapshot['schemaVersion'], 'macd-momentum-v1')
        self.assertEqual(snapshot['timeframes']['H1']['direction'], 'BULLISH')

    def test_small_samples_are_reported_but_not_weighted(self):
        records = [
            {'symbol': 'XAUUSD', 'timeframe': 'H1', 'direction': 'BUY', 'outcome': 'WIN', 'rMultiple': 2,
             'momentumSnapshot': {'alignment': 'ALIGNED'}}
        ]
        result = summarize_momentum_outcomes(records, minimum_samples=5)
        group = next(iter(result['groups'].values()))
        self.assertFalse(group['eligible'])
        self.assertEqual(group['advisoryWeight'], 1.0)

    def test_eligible_results_are_bounded_and_versioned(self):
        records = [
            {'symbol': 'XAUUSD', 'timeframe': 'H1', 'direction': 'BUY', 'outcome': outcome, 'rMultiple': 1 if outcome == 'WIN' else -1,
             'momentumSnapshot': {'alignment': 'ALIGNED'}}
            for outcome in ('WIN', 'WIN', 'WIN', 'WIN', 'LOSS')
        ]
        result = summarize_momentum_outcomes(records, minimum_samples=5, model_version='test-v2')
        group = next(iter(result['groups'].values()))
        self.assertTrue(group['eligible'])
        self.assertLessEqual(group['advisoryWeight'], 1.25)
        self.assertEqual(group['modelVersion'], 'test-v2')