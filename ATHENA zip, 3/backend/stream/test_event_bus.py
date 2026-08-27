from django.test import SimpleTestCase

from .event_bus import ScalpEvent, ScalpEventBus
from .formatters import format_event


class ScalpEventBusTests(SimpleTestCase):
    def test_publish_delivers_event_and_keeps_history(self):
        bus = ScalpEventBus()
        received = []
        bus.subscribe(received.append)
        event = bus.publish(ScalpEvent(type='REGIME_UPDATE', symbol='XAUUSD', data={'regime': 'BULLISH'}))

        self.assertEqual(received, [event])
        self.assertEqual(bus.recent(symbol='XAUUSD')[0].data['regime'], 'BULLISH')

    def test_unsubscribe_stops_delivery(self):
        bus = ScalpEventBus()
        received = []
        unsubscribe = bus.subscribe(received.append)
        unsubscribe()
        bus.publish(ScalpEvent(type='GATE_RESULT', symbol='XAUUSD', data={'gate': 'NEWS', 'status': 'PASS'}))

        self.assertEqual(received, [])

    def test_formatter_renders_structured_event(self):
        event = ScalpEvent(type='LIQUIDITY_SWEEP', symbol='XAUUSD', data={'side': 'SELL_SIDE'})
        self.assertIn('Liquidity swept (SELL_SIDE)', format_event(event))