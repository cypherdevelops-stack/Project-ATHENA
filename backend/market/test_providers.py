from datetime import datetime, timezone

from django.test import SimpleTestCase

from .providers import _normalize_provider_candles


class MarketDataProviderTests(SimpleTestCase):
    def test_provider_ohlc_fields_are_normalized_and_sorted(self):
        timestamp = '2026-10-27T10:00:00Z'
        candles = _normalize_provider_candles(
            'test-provider',
            [{
                'tm': timestamp,
                'o': '2340.1',
                'h': '2341.0',
                'l': '2339.8',
                'c': '2340.7',
                'volume': None,
            }],
        )

        self.assertEqual(candles, [{
            'time': int(datetime(2026, 10, 27, 10, tzinfo=timezone.utc).timestamp()),
            'open': 2340.1,
            'high': 2341.0,
            'low': 2339.8,
            'close': 2340.7,
            'volume': 0,
        }])
