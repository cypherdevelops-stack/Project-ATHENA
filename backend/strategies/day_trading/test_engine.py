from datetime import timedelta
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.utils import timezone

from .detector import generate_day_trading_candidates
from .engine import evaluate_day_trading_state, generate_day_trading_analysis


class DayTradingEngineTests(SimpleTestCase):
    def setUp(self):
        self.account = SimpleNamespace(enabled=True, terminal_connected=True, trade_allowed=True, guardian_state=lambda: 'NORMAL')
        self.state = SimpleNamespace(state='NORMAL', session_locked=False, cooldown_until=None)

    def test_ready_account_is_observe_until_market_candidate_exists(self):
        result = evaluate_day_trading_state(self.account, self.state)
        self.assertEqual(result['decisionState'], 'OBSERVE')
        self.assertIn('DAY_ENGINE_AWAITING_CANDIDATE', result['reasonCodes'])

    def test_day_session_lock_is_isolated_block(self):
        self.state.session_locked = True
        result = evaluate_day_trading_state(self.account, self.state)
        self.assertEqual(result['decisionState'], 'BLOCKED')
        self.assertIn('DAY_SESSION_LOCKED', result['reasonCodes'])

    def test_day_cooldown_is_isolated_block(self):
        self.state.cooldown_until = timezone.now() + timedelta(minutes=5)
        result = evaluate_day_trading_state(self.account, self.state)
        self.assertEqual(result['decisionState'], 'BLOCKED')
        self.assertIn('DAY_STRATEGY_COOLDOWN', result['reasonCodes'])

    def test_multitimeframe_model_returns_developing_candidate_with_real_poi(self):
        h1_candles = [{'open': 107, 'close': 108, 'high': 110, 'low': 100} for _ in range(20)]
        m15_candles = [{'open': 104.5, 'close': 105, 'high': 106, 'low': 104} for _ in range(10)]
        result = generate_day_trading_analysis(
            account=self.account,
            broker_symbol='XAUUSD.Z',
            current_price=105,
            h4_features={'structure': 'BULLISH'},
            h1_features={'structure': 'BULLISH'},
            m15_features={
                'structure': 'BULLISH',
                'orderBlocks': [{'direction': 'BULLISH', 'lowerBound': 104, 'upperBound': 106, 'state': 'DETECTED', 'type': 'ORDER_BLOCK', 'time': 1}],
                'fairValueGaps': [],
            },
            m15_candles=m15_candles,
            h1_candles=h1_candles,
        )

        self.assertEqual(result['status'], 'DEVELOPING')
        candidate = result['candidates'][0]
        self.assertEqual(candidate['direction'], 'BUY')
        self.assertEqual(candidate['entryZone'], {'lower': 104.0, 'upper': 106.0})
        self.assertIn('HTF_ALIGNMENT', candidate['reasonCodes'])
        self.assertEqual(candidate['evidence']['timeframe'], 'H4/H1/M15')

    def test_conflicting_higher_timeframes_do_not_create_candidate(self):
        result = generate_day_trading_candidates(
            account=self.account,
            broker_symbol='XAUUSD.Z',
            current_price=105,
            h4_features={'structure': 'BEARISH'},
            h1_features={'structure': 'BULLISH'},
            m15_features={'structure': 'BULLISH', 'orderBlocks': [], 'fairValueGaps': []},
        )

        self.assertEqual(result, [])

    def test_unverified_market_data_blocks_a_developing_candidate(self):
        result = generate_day_trading_candidates(
            account=self.account,
            broker_symbol='XAUUSD.Z',
            current_price=105,
            h4_features={'structure': 'BULLISH'},
            h1_features={'structure': 'BULLISH'},
            m15_features={
                'structure': 'BULLISH',
                'orderBlocks': [{
                    'direction': 'BULLISH',
                    'lowerBound': 104,
                    'upperBound': 106,
                    'state': 'DETECTED',
                    'type': 'ORDER_BLOCK',
                    'time': 1,
                }],
                'fairValueGaps': [],
            },
            m15_candles=[
                {'open': 104.5, 'close': 105, 'high': 106, 'low': 104}
                for _ in range(10)
            ],
            h1_candles=[
                {'open': 107, 'close': 108, 'high': 110, 'low': 100}
                for _ in range(20)
            ],
            context={'execution_allowed': False},
        )

        self.assertEqual(result[0]['decisionState'], 'BLOCKED')
        self.assertIn('MARKET_DATA_UNVERIFIED', result[0]['reasonCodes'])
