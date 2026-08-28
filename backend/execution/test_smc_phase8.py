from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.backtesting.replay import session_candles
from backend.execution import views


class SMCPhase8Tests(SimpleTestCase):
    def test_orchestrated_publisher_emits_smc_context_update(self):
        views._last_event_signatures.clear()
        payload = {
            'price': {},
            'regime': {},
            'momentumMap': {},
            'smcContext': {'alignment': 'CONFLICTING', 'higherTimeframeBias': 'BUY'},
            'orchestration': {},
            'news': {},
            'newsReaction': {},
            'executionConditions': {},
            'scalping': {'candidates': []},
            'dayTrading': {'candidates': []},
        }

        views._publish_orchestrated_analysis_events(payload, symbol='XAUUSD')

        events = views.scalp_event_bus.recent(symbol='XAUUSD', limit=20)
        smc_events = [event for event in events if event.type == 'SMC_CONTEXT_UPDATE']
        self.assertEqual(len(smc_events), 1)
        self.assertEqual(smc_events[0].data['alignment'], 'CONFLICTING')

    def test_session_candles_requests_chronological_order(self):
        candle = SimpleNamespace(as_dict=lambda: {'time': 1})

        class Query:
            def __init__(self):
                self.ordering = None

            def filter(self, **kwargs):
                return self

            def order_by(self, *fields):
                self.ordering = fields
                return [candle]

        query = Query()
        session = SimpleNamespace(
            user='user', account='account', symbol='XAUUSD', timeframe='M1',
            dataset=None, start_time=None, end_time=None,
        )
        with patch('backend.backtesting.replay.HistoricalCandle.objects.filter', return_value=query):
            result = session_candles(session)

        self.assertEqual(result, [{'time': 1}])
        self.assertEqual(query.ordering, ('timestamp', 'id'))
