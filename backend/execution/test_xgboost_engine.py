from types import SimpleNamespace

from django.test import SimpleTestCase

from backend.strategies.scalping.candidates import generate_scalping_candidates

from .xgboost_engine import FEATURE_NAMES, XGBoostEngine, build_feature_vector


class XGBoostEngineTests(SimpleTestCase):
    def test_untrained_engine_is_explicitly_unknown(self):
        result = XGBoostEngine().predict(candidate={}, context={})

        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertIsNone(result['probability'])

    def test_feature_vector_has_stable_schema(self):
        vector = build_feature_vector(candidate={'direction': 'BUY', 'score': 60}, context={})

        self.assertEqual(len(vector), len(FEATURE_NAMES))
        self.assertTrue(all(isinstance(value, float) for value in vector))

    def test_candidate_exposes_model_prediction_without_bypassing_rules(self):
        class FakeEngine:
            def predict(self, *, candidate, context):
                return {'status': 'PASS', 'probability': 0.99}

        features = {
            'timeframe': 'M1',
            'structure': 'BULLISH',
            'orderBlocks': [{'type': 'OB', 'direction': 'BULLISH', 'time': 1, 'lowerBound': 99, 'upperBound': 101, 'strength': 0.8}],
            'fairValueGaps': [],
        }
        candidates = generate_scalping_candidates(
            account=SimpleNamespace(enabled=True, terminal_connected=True, trade_allowed=True),
            broker_symbol='XAUUSD.Z', current_price=100, m1_features=features,
            m5_features={'structure': 'BULLISH'}, ml_engine=FakeEngine(),
        )

        self.assertEqual(candidates[0]['mlPrediction']['probability'], 0.99)
        self.assertEqual(candidates[0]['decisionState'], 'OBSERVE')
