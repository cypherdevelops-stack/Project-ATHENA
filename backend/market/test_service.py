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
        service = MarketDataService(adapter_factory=FakeAdapter)

        result = service.fetch(account, timeframes=('M1', 'M5'))

        self.assertEqual(result.snapshot.broker_symbol, 'XAUUSD247')
        self.assertEqual(result.snapshot.ask, 2034.7)
        self.assertEqual(set(result.candles), {'M1', 'M5'})
        self.assertEqual(result.candles['M1'][0]['close'], 1.5)

    def test_adapter_error_is_preserved(self):
        account = SimpleNamespace(broker_symbol='XAUUSD247', canonical_asset='XAUUSD')
        service = MarketDataService(adapter_factory=FailingAdapter)

        with self.assertRaisesRegex(MarketDataError, 'invalid credentials'):
            service.fetch(account)
