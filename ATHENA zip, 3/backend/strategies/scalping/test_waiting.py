from django.test import SimpleTestCase

from backend.stream.event_bus import ScalpEventBus

from .waiting import (
    LONG_CANDIDATE,
    WAITING_FOR_MSS,
    WAITING_FOR_RETRACEMENT,
    WAITING_FOR_SETUP,
    ScalpWaitingMechanism,
    EXECUTED,
    INVALIDATED,
    RISK_APPROVED,
)


class ScalpWaitingMechanismTests(SimpleTestCase):
    def setUp(self):
        self.bus = ScalpEventBus()
        self.events = []
        self.bus.subscribe(self.events.append)
        self.monitor = ScalpWaitingMechanism(symbol='XAUUSD.Z', bus=self.bus)

    def test_waits_for_liquidity_then_mss_then_retracement(self):
        self.assertEqual(self.monitor.update(setup={'direction': 'LONG', 'missing': ['LIQUIDITY_SWEEP']})['state'], WAITING_FOR_SETUP)
        self.assertEqual(self.monitor.update(setup={'direction': 'LONG', 'missing': ['MSS']})['state'], WAITING_FOR_MSS)
        self.assertEqual(self.monitor.update(setup={'direction': 'LONG', 'missing': ['POI_RETEST']})['state'], WAITING_FOR_RETRACEMENT)

    def test_repeated_poll_does_not_emit_duplicate_state_events(self):
        setup = {'direction': 'LONG', 'missing': ['LIQUIDITY_SWEEP']}
        self.monitor.update(setup=setup)
        self.monitor.update(setup=setup)

        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].data['state'], WAITING_FOR_SETUP)

    def test_active_setup_becomes_long_candidate(self):
        state = self.monitor.update(setup={'direction': 'LONG', 'active': True, 'missing': []})

        self.assertEqual(state['state'], LONG_CANDIDATE)
        self.assertEqual(self.events[0].type, 'SETUP_CONFIRMED')

    def test_lifecycle_has_terminal_risk_execution_and_invalidation_states(self):
        self.assertEqual(self.monitor.update(setup={'direction': 'LONG', 'risk_approved': True})['state'], RISK_APPROVED)
        self.assertEqual(self.monitor.update(setup={'direction': 'LONG', 'executed': True})['state'], EXECUTED)
        self.assertEqual(self.monitor.update(setup={'direction': 'LONG', 'invalidated': True})['state'], INVALIDATED)