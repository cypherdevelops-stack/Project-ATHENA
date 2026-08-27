from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone as datetime_timezone
from typing import Any
from zoneinfo import ZoneInfo

from backend.accounts.credentials import decrypt_password
from backend.accounts.handshake import DEFAULT_MT5_TERMINAL_PATH

from .context import normalize_candles

EAT = ZoneInfo('Africa/Nairobi')


class MarketDataError(RuntimeError):
    """Raised when the adapter cannot provide a valid market-data response."""


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    broker_symbol: str
    bid: float
    ask: float
    spread: float
    timestamp: str | None
    received_at: str
    latency_ms: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            'symbol': self.symbol,
            'brokerSymbol': self.broker_symbol,
            'bid': self.bid,
            'ask': self.ask,
            'spread': self.spread,
            'timestamp': self.timestamp,
            'mt5Time': self.timestamp,
            'receivedAt': self.received_at,
            'latencyMs': self.latency_ms,
        }


@dataclass(frozen=True)
class MarketDataBundle:
    snapshot: MarketSnapshot
    candles: dict[str, list[dict]]


class MT5Adapter:
    """Owns all direct MetaTrader5 SDK access."""

    def __init__(self, mt5_module=None):
        self.mt5 = mt5_module
        self.initialized = False

    def connect(self, account) -> None:
        if self.mt5 is None:
            try:
                import MetaTrader5 as mt5
            except Exception as error:
                raise MarketDataError(f'MetaTrader5 package import failed: {error}') from error
            self.mt5 = mt5

        terminal_path = account.terminal_path or DEFAULT_MT5_TERMINAL_PATH
        self.initialized = bool(self.mt5.initialize(path=terminal_path))
        if not self.initialized:
            raise MarketDataError(f'MT5 initialization failed for {terminal_path}: {self.mt5.last_error()}')

        try:
            logged_in = self.mt5.login(
                login=int(account.login),
                password=decrypt_password(account.password_encrypted),
                server=account.server,
            )
        except (TypeError, ValueError) as error:
            self.close()
            raise MarketDataError(f'MT5 account login configuration is invalid: {error}') from error
        if not logged_in:
            error = self.mt5.last_error()
            self.close()
            raise MarketDataError(f'MT5 login failed for account {account.login} on {account.server}: {error}')

    def close(self) -> None:
        if self.initialized and self.mt5 is not None:
            self.mt5.shutdown()
            self.initialized = False

    def snapshot(self, account) -> MarketSnapshot:
        broker_symbol = account.broker_symbol
        if not broker_symbol:
            raise MarketDataError('No broker symbol is configured for this account.')

        tick = self.mt5.symbol_info_tick(broker_symbol)
        bid = getattr(tick, 'bid', None) if tick else None
        ask = getattr(tick, 'ask', None) if tick else None
        if not bid or not ask:
            raise MarketDataError(f'MT5 tick fetch failed for {broker_symbol}: {self.mt5.last_error()}')

        received_utc = datetime.now(datetime_timezone.utc)
        tick_epoch = getattr(tick, 'time', None)
        tick_utc = datetime.fromtimestamp(int(tick_epoch), tz=datetime_timezone.utc) if tick_epoch else None
        return MarketSnapshot(
            symbol=account.canonical_asset or broker_symbol,
            broker_symbol=broker_symbol,
            bid=float(bid),
            ask=float(ask),
            spread=float(ask) - float(bid),
            timestamp=tick_utc.astimezone(EAT).isoformat() if tick_utc else None,
            received_at=received_utc.astimezone(EAT).isoformat(),
            latency_ms=round((received_utc - tick_utc).total_seconds() * 1000) if tick_utc else None,
        )

    def candles(self, account, timeframe: str, count: int = 200) -> list[dict]:
        timeframe_constant = getattr(self.mt5, f'TIMEFRAME_{timeframe}', None)
        if timeframe_constant is None:
            raise MarketDataError(f'Unsupported MT5 timeframe: {timeframe}')
        rates = self.mt5.copy_rates_from_pos(account.broker_symbol, timeframe_constant, 0, count)
        if rates is None:
            raise MarketDataError(f'MT5 {timeframe} candle fetch failed for {account.broker_symbol}: {self.mt5.last_error()}')
        return normalize_candles(rates)


class MarketDataService:
    """Provides normalized snapshots and candles without exposing the MT5 SDK."""

    def __init__(self, adapter_factory=MT5Adapter):
        self.adapter_factory = adapter_factory

    def fetch(self, account, timeframes: tuple[str, ...] = ('M1', 'M5'), candle_count: int = 200) -> MarketDataBundle:
        adapter = self.adapter_factory()
        try:
            adapter.connect(account)
            snapshot = adapter.snapshot(account)
            candles = {timeframe: adapter.candles(account, timeframe, candle_count) for timeframe in timeframes}
            return MarketDataBundle(snapshot=snapshot, candles=candles)
        finally:
            adapter.close()

    def fetch_snapshot(self, account) -> MarketSnapshot:
        return self.fetch(account, timeframes=(), candle_count=0).snapshot


market_data_service = MarketDataService()
