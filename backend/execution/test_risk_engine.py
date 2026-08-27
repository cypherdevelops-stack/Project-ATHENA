from types import SimpleNamespace

from django.test import SimpleTestCase

from .risk_engine import assess_risk


class RiskEngineTests(SimpleTestCase):
    def account(self, **overrides):
        values = {
            'equity': 10000,
            'balance': 10000,
            'risk_per_trade': 0.5,
            'max_daily_drawdown': 5,
            'current_daily_drawdown': 0,
            'max_concurrent_positions': 1,
            'open_positions': 0,
            'broker_symbol': 'XAUUSD.Z',
            'market_discovery': {'symbols': [{'name': 'XAUUSD.Z', 'contractSize': 100, 'volumeMin': 0.01, 'volumeMax': 10, 'volumeStep': 0.01}]},
        }
        values.update(overrides)
        account = SimpleNamespace(**values)
        account.guardian_state = lambda: 'NORMAL'
        return account

    def test_approved_trade_sizes_volume_from_equity_and_stop_distance(self):
        result = assess_risk(account=self.account(), direction='BUY', entry=100, stop_loss=99, take_profit=102)

        self.assertTrue(result['approved'])
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['riskAmount'], 50.0)
        self.assertEqual(result['volume'], 0.5)
        self.assertEqual(result['riskReward'], 2.0)

    def test_daily_drawdown_limit_rejects_trade(self):
        result = assess_risk(
            account=self.account(current_daily_drawdown=4.75),
            direction='BUY', entry=100, stop_loss=99, take_profit=102,
        )

        self.assertFalse(result['approved'])
        self.assertEqual(result['status'], 'BLOCK')
        self.assertIn('daily drawdown', result['reason'])
