from types import SimpleNamespace

from django.test import SimpleTestCase

from .risk_engine import assess_risk
from .trade_setup import build_trade_setup


class TradeSetupTests(SimpleTestCase):
    def test_setup_contains_consistent_targets_and_risk(self):
        candidate = {
            'direction': 'BUY',
            'entryZone': {'lower': 99, 'upper': 101},
            'score': 84,
            'confirmation': {'rejection': True, 'micro_mss': True},
            'poiTime': 1000,
            'decisionState': 'READY',
        }
        account = SimpleNamespace(
            equity=10000, balance=10000, risk_per_trade=0.5,
            max_daily_drawdown=5, current_daily_drawdown=0,
            max_concurrent_positions=1, open_positions=0,
            broker_symbol='XAUUSD.Z', market_discovery={'symbols': []},
            guardian_state=lambda: 'NORMAL',
        )
        risk = assess_risk(account=account, direction='BUY', entry=100, stop_loss=98, take_profit=105)

        setup = build_trade_setup(candidate=candidate, risk=risk)

        self.assertEqual(setup['state'], 'RISK_APPROVED')
        self.assertEqual(setup['entry'], 100)
        self.assertEqual(setup['takeProfit1'], 101)
        self.assertEqual(setup['takeProfit2'], 105)
        self.assertEqual(setup['riskReward'], 2.5)
        self.assertEqual(setup['score'], 84)

    def test_missing_candidate_stays_observe_without_trade_values(self):
        setup = build_trade_setup(candidate={}, risk=None)

        self.assertEqual(setup['state'], 'OBSERVE')
        self.assertIsNone(setup['entry'])
        self.assertIsNone(setup['takeProfit1'])
