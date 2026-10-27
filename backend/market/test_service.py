from types import SimpleNamespace

from django.test import SimpleTestCase

from .service import MarketDataError, MarketDataService, MarketSnapshot


class FakeAdapter:
    def __init__(self):
        self.closed = False

    def connect(self, account):
        self.account = account

    def snapshot(self, account):
        return MarketSnapshot(
            symbol='XAUUSD',
            broker_symbol=account.broker_symbol,
            bid=2034.5,
            ask=2034.7,
            spread=0.2,
            timestamp='2026-08-25T13:00:00+03:00',
            received_at='2026-08-25T13:00:00.100000+03:00',
            latency_ms=100,
        )

    def candles(self, account, timeframe, count):
        return [{'time': 1, 'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5, 'volume': 10}]

    def close(self):
        self.closed = True


class FailingAdapter(FakeAdapter):
    def connect(self, account):
        raise MarketDataError('MT5 login failed: invalid credentials')


class MarketDataServiceTests(SimpleTestCase):
    def test_fetch_returns_snapshot_and_requested_candles(self):
        account = SimpleNamespace(broker_symbol='XAUUSD247', canonical_asset='XAUUSD')
        service = MarketDataService(adapter_factory=FakeAdapter, provider_factories=[])

        result = service.fetch(account, timeframes=('M1', 'M5'))

        self.assertEqual(result.snapshot.broker_symbol, 'XAUUSD247')
        self.assertEqual(result.snapshot.ask, 2034.7)
        self.assertEqual(set(result.candles), {'M1', 'M5'})
        self.assertEqual(result.candles['M1'][0]['close'], 1.5)

    def test_adapter_error_is_preserved(self):
        account = SimpleNamespace(broker_symbol='XAUUSD247', canonical_asset='XAUUSD')
        service = MarketDataService(adapter_factory=FailingAdapter, provider_factories=[])

        with self.assertRaisesRegex(MarketDataError, 'invalid credentials'):
            service.fetch(account)

    def test_matching_sources_verify_and_prefer_broker_candles(self):
        candle = {'time': 100, 'open': 10.0, 'high': 11.0, 'low': 9.0, 'close': 10.5, 'volume': 1}
        selected, quality = MarketDataService._verify_candles(
            {'MT5': [candle], 'TwelveData': [dict(candle)]},
            threshold=0.05,
        )

        self.assertTrue(quality['verified'])
        self.assertEqual(quality['sources'], ['MT5', 'TwelveData'])
        self.assertEqual(selected, [candle])

    def test_conflicting_sources_do_not_verify(self):
        broker_candle = {'time': 100, 'open': 10.0, 'high': 11.0, 'low': 9.0, 'close': 10.5, 'volume': 1}
        api_candle = {**broker_candle, 'close': 10.6}
        _, quality = MarketDataService._verify_candles(
            {'MT5': [broker_candle], 'FCSAPI': [api_candle]},
            threshold=0.05,
        )

        self.assertFalse(quality['verified'])
        self.assertIn('conflict', quality['reason'])

    def test_majority_sources_exclude_an_outlier(self):
        broker_candle = {'time': 100, 'open': 10.0, 'high': 11.0, 'low': 9.0, 'close': 10.5, 'volume': 1}
        twelve_candle = dict(broker_candle)
        fcs_candle = {**broker_candle, 'close': 10.7}
        _, quality = MarketDataService._verify_candles(
            {'MT5': [broker_candle], 'TwelveData': [twelve_candle], 'FCSAPI': [fcs_candle]},
            threshold=0.05,
        )

        self.assertTrue(quality['verified'])
        self.assertEqual(quality['sources'], ['MT5', 'TwelveData'])
