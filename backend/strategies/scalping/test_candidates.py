from types import SimpleNamespace

from django.test import SimpleTestCase

from backend.stream.event_bus import ScalpEventBus

from .candidates import build_decision_stream, generate_scalping_candidates
from .gates import detect_scalping_setup
from .waiting import WAITING_FOR_SETUP, ScalpWaitingMechanism


class ScalpingCandidateTests(SimpleTestCase):
    def setUp(self):
        self.features = {
            'timeframe': 'M1',
            'structure': 'BULLISH',
            'orderBlocks': [{'type': 'OB', 'direction': 'BULLISH', 'time': 1, 'lowerBound': 99, 'upperBound': 101, 'strength': 0.8}],
            'fairValueGaps': [],
        }

    def test_aligned_in_zone_poi_waits_without_setup_evidence(self):
        candidates = generate_scalping_candidates(
            account=SimpleNamespace(enabled=True, terminal_connected=True, trade_allowed=True),
            broker_symbol='XAUUSDc.Z', current_price=100, m1_features=self.features, m5_features={'structure': 'BULLISH'},
        )
        self.assertEqual(candidates[0]['decisionState'], 'OBSERVE')
        self.assertEqual(candidates[0]['direction'], 'BUY')
        self.assertIn('SETUP_SEQUENCE_INCOMPLETE', candidates[0]['reasonCodes'])

    def test_account_permission_blocks_candidate(self):
        candidates = generate_scalping_candidates(
            account=SimpleNamespace(enabled=True, terminal_connected=True, trade_allowed=False),
            broker_symbol='XAUUSDc.Z', current_price=100, m1_features=self.features, m5_features={'structure': 'BULLISH'},
        )
        self.assertEqual(candidates[0]['decisionState'], 'BLOCKED')
        self.assertIn('ACCOUNT_TRADE_NOT_ALLOWED', candidates[0]['reasonCodes'])

    def test_opposite_higher_timeframe_structure_is_observe(self):
        candidates = generate_scalping_candidates(
            account=SimpleNamespace(enabled=True, terminal_connected=True, trade_allowed=True),
            broker_symbol='XAUUSDc.Z', current_price=100, m1_features=self.features, m5_features={'structure': 'BEARISH'},
        )
        self.assertEqual(candidates[0]['decisionState'], 'OBSERVE')
        self.assertIn('HTF_LTF_DIRECTION_NOT_ALIGNED', candidates[0]['reasonCodes'])

    def test_context_score_below_threshold_is_observe(self):
        candidates = generate_scalping_candidates(
            account=SimpleNamespace(enabled=True, terminal_connected=True, trade_allowed=True),
            broker_symbol='XAUUSDc.Z', current_price=100, m1_features=self.features,
            m5_features={'structure': 'BULLISH'},
            context={
                'htf_bias_defined': False,
                'liquidity_sweep': False,
                'session_aligned': True,
                'structure_confirmed': False,
                'displacement': False,
                'momentum_confirmed': False,
            },
        )
        self.assertEqual(candidates[0]['decisionState'], 'OBSERVE')
        self.assertLess(candidates[0]['score'], 60)
        self.assertIn('SCALP_SCORE_BELOW_THRESHOLD', candidates[0]['reasonCodes'])

    def test_hard_gate_blocks_even_with_high_score(self):
        candidates = generate_scalping_candidates(
            account=SimpleNamespace(enabled=True, terminal_connected=True, trade_allowed=True),
            broker_symbol='XAUUSDc.Z', current_price=100, m1_features=self.features,
            m5_features={'structure': 'BULLISH'},
            context={'news_locked': True},
        )
        self.assertEqual(candidates[0]['decisionState'], 'BLOCKED')
        self.assertIn('NEWS_LOCK', candidates[0]['reasonCodes'])

    def test_decision_stream_separates_supporting_and_blocking_reasons(self):
        candidates = generate_scalping_candidates(
            account=SimpleNamespace(enabled=True, terminal_connected=True, trade_allowed=False),
            broker_symbol='XAUUSDc.Z', current_price=100, m1_features=self.features, m5_features={'structure': 'BULLISH'},
        )
        stream = build_decision_stream(candidates=candidates, m1_features=self.features, m5_features={'structure': 'BULLISH'}, current_price=100)
        self.assertTrue(stream['whyTrade'])
        self.assertTrue(any(reason['code'] == 'ACCOUNT_TRADE_NOT_ALLOWED' for reason in stream['whyNot']))
        self.assertEqual([event['type'] for event in stream['events']], ['ANALYSIS', 'ANALYSIS', 'SYSTEM', 'DECISION'])

    def test_detect_scalping_setup_accepts_a_full_bullish_sequence(self):
        setup = detect_scalping_setup(
            direction='BULLISH',
            current_price=100.03,
            poi={'type': 'OB', 'direction': 'BULLISH', 'lowerBound': 99.8, 'upperBound': 100.2},
            context={
                'htf_bias': 'BUY',
                'price_approaches_liquidity': True,
                'sell_side_liquidity_swept': True,
                'bullish_displacement': True,
                'bullish_mss': True,
                'fresh_bullish_poi': True,
                'price_returns_to_poi': True,
                'entry_confirmation': True,
            },
        )
        self.assertTrue(setup['active'])
        self.assertEqual(setup['direction'], 'LONG')
        self.assertTrue(all(step['status'] == 'PASS' for step in setup['steps']))

    def test_generate_scalping_candidates_requires_setup_sequence(self):
        context = {
            'htf_bias': 'BUY',
            'price_approaches_liquidity': True,
            'sell_side_liquidity_swept': True,
            'bullish_displacement': True,
            'bullish_mss': True,
            'fresh_bullish_poi': True,
            'price_returns_to_poi': True,
            'entry_confirmation': True,
        }
        candidates = generate_scalping_candidates(
            account=SimpleNamespace(enabled=True, terminal_connected=True, trade_allowed=True),
            broker_symbol='XAUUSDc.Z', current_price=100, m1_features=self.features, m5_features={'structure': 'BULLISH'},
            context=context,
        )
        self.assertEqual(candidates[0]['decisionState'], 'READY')
        self.assertIn('SETUP_SEQUENCE_COMPLETE', candidates[0]['reasonCodes'])

    def test_decision_stream_exposes_waiting_for_setup(self):
        candidates = generate_scalping_candidates(
            account=SimpleNamespace(enabled=True, terminal_connected=True, trade_allowed=True),
            broker_symbol='XAUUSDc.Z', current_price=100, m1_features=self.features, m5_features={'structure': 'BULLISH'},
            context={'htf_bias': 'BUY', 'price_approaches_liquidity': True},
        )
        monitor = ScalpWaitingMechanism(symbol='XAUUSDc.Z', bus=ScalpEventBus())
        stream = build_decision_stream(
            candidates=candidates,
            m1_features=self.features,
            m5_features={'structure': 'BULLISH'},
            current_price=100,
            waiting_mechanism=monitor,
        )

        self.assertEqual(stream['setupState']['state'], WAITING_FOR_SETUP)
