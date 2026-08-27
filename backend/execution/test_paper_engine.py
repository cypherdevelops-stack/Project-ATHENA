from types import SimpleNamespace

from django.test import SimpleTestCase

from backend.stream.event_bus import scalp_event_bus

from .paper_engine import PaperTradeError, clear_paper_positions, list_paper_positions, open_paper_position, update_paper_positions


class PaperPositionTests(SimpleTestCase):
    def setUp(self):
        clear_paper_positions()
        scalp_event_bus.clear()
        self.account = SimpleNamespace(pk=7, broker_symbol='XAUUSD.Z')
        self.setup = {
            'state': 'RISK_APPROVED', 'direction': 'BUY', 'entry': 100,
            'stopLoss': 98, 'takeProfit1': 101, 'takeProfit2': 104, 'volume': 0.5,
        }

    def tearDown(self):
        clear_paper_positions()
        scalp_event_bus.clear()

    def test_open_prevents_duplicate_and_emits_active_event(self):
        position = open_paper_position(account=self.account, setup=self.setup, quote={'bid': 100, 'ask': 100.1})

        self.assertEqual(position['state'], 'ACTIVE')
        self.assertEqual(scalp_event_bus.recent()[-1].type, 'POSITION_ACTIVE')
        with self.assertRaisesRegex(PaperTradeError, 'already exists'):
            open_paper_position(account=self.account, setup=self.setup, quote={'bid': 100, 'ask': 100.1})

    def test_position_progresses_through_targets(self):
        position = open_paper_position(account=self.account, setup=self.setup, quote={'bid': 100, 'ask': 100.1})

        self.assertEqual(update_paper_positions(account_id=7, quote={'bid': 101, 'ask': 101.1})[0]['state'], 'TP1_HIT')
        self.assertEqual(update_paper_positions(account_id=7, quote={'bid': 104, 'ask': 104.1})[0]['state'], 'TP2_HIT')
        self.assertEqual([event.type for event in scalp_event_bus.recent()], ['POSITION_ACTIVE', 'TP1_HIT', 'TP2_HIT'])

    def test_stop_has_precedence_and_closes_position(self):
        open_paper_position(account=self.account, setup=self.setup, quote={'bid': 100, 'ask': 100.1})

        changed = update_paper_positions(account_id=7, quote={'bid': 97, 'ask': 97.1})

        self.assertEqual(changed[0]['state'], 'STOP_HIT')
        self.assertEqual(list_paper_positions(account_id=7)[0]['state'], 'STOP_HIT')
