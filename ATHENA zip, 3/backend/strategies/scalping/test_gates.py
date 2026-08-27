from types import SimpleNamespace

from django.test import SimpleTestCase

from .gates import evaluate_gates, spread_gate


class GateTests(SimpleTestCase):
    def setUp(self):
        self.account = SimpleNamespace(enabled=True, terminal_connected=True, trade_allowed=True)

    def test_spread_gate_reports_measured_and_allowed_values(self):
        result = spread_gate({'spread': 0.42, 'max_spread': 0.30})
        self.assertEqual(result.name, 'SPREAD_GATE')
        self.assertEqual(result.status, 'BLOCK')
        self.assertIn('0.42', result.reason)
        self.assertIn('0.30', result.reason)

    def test_all_eight_gates_are_evaluated(self):
        results = evaluate_gates(account=self.account, direction='BULLISH', higher_structure='BULLISH')
        self.assertEqual([result.name for result in results], [
            'NEWS_GATE', 'SESSION_GATE', 'SPREAD_GATE', 'VOLATILITY_GATE',
            'DRAWDOWN_GATE', 'CORRELATION_GATE', 'HTF_BIAS_GATE', 'EXECUTION_GATE',
        ])

    def test_hard_gate_blocks_and_preserves_specific_reason(self):
        results = evaluate_gates(
            account=self.account,
            direction='BULLISH',
            higher_structure='BULLISH',
            context={'news_locked': True, 'news_reason': 'CPI release within 30 minutes.'},
        )
        news = next(result for result in results if result.name == 'NEWS_GATE')
        self.assertEqual(news.status, 'BLOCK')
        self.assertEqual(news.reason, 'CPI release within 30 minutes.')

    def test_news_provider_states_are_explicit_and_fail_closed(self):
        waiting = next(result for result in evaluate_gates(
            account=self.account, direction='BULLISH', higher_structure='BULLISH',
            context={'news_state': 'WAIT'},
        ) if result.name == 'NEWS_GATE')
        degraded = next(result for result in evaluate_gates(
            account=self.account, direction='BULLISH', higher_structure='BULLISH',
            context={'news_provider_available': False},
        ) if result.name == 'NEWS_GATE')

        self.assertEqual(waiting.status, 'WAIT')
        self.assertEqual(degraded.status, 'DEGRADED')
