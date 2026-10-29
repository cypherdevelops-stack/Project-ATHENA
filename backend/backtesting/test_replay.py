from types import SimpleNamespace

from django.test import SimpleTestCase

from .replay import session_candles


class DatasetReplayTests(SimpleTestCase):
    def test_dataset_replay_does_not_read_unrelated_timeframes(self):
        session = SimpleNamespace(
            dataset=SimpleNamespace(timeframe='M5'),
            timeframe='M5',
        )

        self.assertEqual(session_candles(session, timeframe='M1'), [])

