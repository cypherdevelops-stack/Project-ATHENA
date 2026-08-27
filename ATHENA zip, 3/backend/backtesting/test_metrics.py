from types import SimpleNamespace

from django.test import SimpleTestCase

from .replay import replay_metrics


class ReplayMetricsTests(SimpleTestCase):
    def test_metrics_report_win_rate_expectancy_profit_factor_and_drawdown(self):
        trades = [
            SimpleNamespace(pnl=20),
            SimpleNamespace(pnl=-10),
            SimpleNamespace(pnl=30),
        ]
        manager = SimpleNamespace(filter=lambda **kwargs: SimpleNamespace(order_by=lambda *args: trades))

        result = replay_metrics(SimpleNamespace(trades=manager))

        self.assertEqual(result['trades'], 3)
        self.assertEqual(result['wins'], 2)
        self.assertEqual(result['winRate'], 0.6667)
        self.assertEqual(result['netPnl'], 40)
        self.assertEqual(result['expectancy'], 13.33)
        self.assertEqual(result['profitFactor'], 5)
        self.assertEqual(result['maxDrawdown'], 10)

    def test_empty_replay_has_zero_metrics(self):
        manager = SimpleNamespace(filter=lambda **kwargs: SimpleNamespace(order_by=lambda *args: []))

        result = replay_metrics(SimpleNamespace(trades=manager))

        self.assertEqual(result['trades'], 0)
        self.assertEqual(result['winRate'], 0)
        self.assertIsNone(result['profitFactor'])
