from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import datetime, timezone as datetime_timezone
import hashlib
from itertools import combinations
from typing import Any
from zoneinfo import ZoneInfo

from backend.accounts.handshake import DEFAULT_MT5_TERMINAL_PATH
from django.conf import settings
from django.core.cache import cache

from .context import normalize_candles
from .providers import (
    FCSApiProvider,
    MarketDataProviderError,
    MetaApiHistoricalProvider,
    TwelveDataProvider,
)

EAT = ZoneInfo('Africa/Nairobi')
_CACHE_SECONDS = {
    'M1': 60,
    'M5': 60,
    'M15': 120,
    'M30': 180,
    'H1': 300,
    'H4': 600,
    'D1': 1800,
}
_TIMEFRAME_SECONDS = {
    'M1': 60,
    'M5': 300,
    'M15': 900,
    'M30': 1800,
    'H1': 3600,
    'H4': 14400,
    'D1': 86400,
}


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
    quote_source: str = 'MT5'
    data_quality: dict[str, Any] | None = None

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
            'quoteSource': self.quote_source,
            'dataQuality': self.data_quality or {},
        }


@dataclass(frozen=True)
class MarketDataBundle:
    snapshot: MarketSnapshot
    candles: dict[str, list[dict]]
    data_quality: dict[str, Any]


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
    """Fetches market data from configured sources and verifies overlapping candles."""

    def __init__(self, adapter_factory=MT5Adapter, provider_factories=None):
        self.adapter_factory = adapter_factory
        self.provider_factories = provider_factories

    def fetch(self, account, timeframes: tuple[str, ...] = ('M1', 'M5'), candle_count: int = 200) -> MarketDataBundle:
        verification_timeframes = timeframes or ('M1',)
        source_candles: dict[str, dict[str, list[dict]]] = {}
        source_status: dict[str, dict[str, Any]] = {}
        snapshot = None
        adapter = None

        if getattr(account, 'connection_method', 'BROKER') == 'BROKER':
            adapter = self.adapter_factory()
            quote_status = 'UNAVAILABLE'
            try:
                adapter.connect(account)
                try:
                    snapshot = adapter.snapshot(account)
                    quote_status = 'AVAILABLE'
                except Exception:
                    quote_status = 'UNAVAILABLE'
                frames = {}
                for timeframe in verification_timeframes:
                    try:
                        frames[timeframe] = adapter.candles(account, timeframe, candle_count)
                    except Exception:
                        frames[timeframe] = []
                source_candles['MT5'] = frames
                source_status['MT5'] = {
                    'status': 'AVAILABLE' if any(frames.values()) else 'QUOTE_ONLY' if snapshot else 'UNAVAILABLE',
                    'quoteStatus': quote_status,
                    'timeframes': {
                        timeframe: 'AVAILABLE' if frames.get(timeframe) else 'UNAVAILABLE'
                        for timeframe in verification_timeframes
                    },
                }
            except Exception as error:
                source_status['MT5'] = {'status': 'UNAVAILABLE', 'reason': str(error)}
            finally:
                if adapter is not None:
                    adapter.close()

        providers = self._providers(account)
        if providers:
            with ThreadPoolExecutor(max_workers=len(providers)) as executor:
                futures = {
                    executor.submit(
                        self._fetch_provider,
                        name,
                        provider,
                        account,
                        verification_timeframes,
                        candle_count,
                    ): name
                    for name, provider in providers
                }
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        frames = future.result()
                        source_candles[name] = frames
                        source_status[name] = {
                            'status': 'AVAILABLE' if any(frames.values()) else 'UNAVAILABLE',
                            'timeframes': {
                                timeframe: 'AVAILABLE' if frames.get(timeframe) else 'UNAVAILABLE'
                                for timeframe in verification_timeframes
                            },
                        }
                    except MarketDataProviderError as error:
                        source_status[name] = {
                            'status': 'RATE_LIMITED' if error.rate_limited else 'UNAVAILABLE',
                            'reason': str(error),
                        }
                    except Exception:
                        source_status[name] = {'status': 'UNAVAILABLE', 'reason': f'{name} data unavailable.'}

        threshold = float(getattr(settings, 'MARKET_DATA_MAX_PRICE_DEVIATION_PERCENT', 0.05))
        verified_candles = {}
        timeframe_quality = {}
        for timeframe in verification_timeframes:
            feeds = {
                name: frames[timeframe]
                for name, frames in source_candles.items()
                if frames.get(timeframe)
            }
            if not feeds:
                reasons = [
                    status.get('reason')
                    for status in source_status.values()
                    if status.get('reason')
                ]
                reason = reasons[0] if reasons else f'No market-data source returned {timeframe} candles.'
                raise MarketDataError(reason)
            selected, quality = self._verify_candles(feeds, threshold)
            latest_age = datetime.now(datetime_timezone.utc).timestamp() - selected[-1]['time']
            quality['latestCandleAgeSeconds'] = round(latest_age)
            if latest_age < 0 or latest_age > _TIMEFRAME_SECONDS.get(timeframe, 60) * 2:
                quality['verified'] = False
                quality['reason'] = 'The latest candle is stale or has a future timestamp.'
            verified_candles[timeframe] = selected
            timeframe_quality[timeframe] = quality

        if snapshot is None:
            m1 = verified_candles.get('M1') or next(iter(verified_candles.values()))
            latest = m1[-1]
            candle_time = datetime.fromtimestamp(latest['time'], tz=datetime_timezone.utc)
            now = datetime.now(datetime_timezone.utc)
            snapshot = MarketSnapshot(
                symbol=account.canonical_asset or account.broker_symbol,
                broker_symbol=account.broker_symbol,
                bid=latest['close'],
                ask=latest['close'],
                spread=0.0,
                timestamp=candle_time.astimezone(EAT).isoformat(),
                received_at=now.astimezone(EAT).isoformat(),
                latency_ms=round((now - candle_time).total_seconds() * 1000),
                quote_source='HISTORICAL_CANDLE',
            )

        all_verified = all(item['verified'] for item in timeframe_quality.values())
        quote_age_limit = int(getattr(settings, 'MARKET_DATA_MAX_QUOTE_AGE_SECONDS', 60))
        quote_is_fresh = (
            snapshot.quote_source == 'MT5'
            and snapshot.latency_ms is not None
            and 0 <= snapshot.latency_ms <= quote_age_limit * 1000
        )
        data_quality = {
            'verified': all_verified,
            'execution_allowed': all_verified and quote_is_fresh,
            'minimumSources': 2,
            'maxPriceDeviationPercent': threshold,
            'maxQuoteAgeSeconds': quote_age_limit,
            'timeframes': timeframe_quality,
            'sources': source_status,
            'reason': (
                'All requested timeframes were verified and the live broker quote is fresh.'
                if all_verified and quote_is_fresh
                else (
                    'Candles were verified, but a fresh live broker quote is unavailable; execution is blocked.'
                    if all_verified
                    else 'Market data is unverified or conflicting; analysis is available but execution is blocked.'
                )
            ),
        }
        snapshot = replace(snapshot, data_quality=data_quality)
        return MarketDataBundle(
            snapshot=snapshot,
            candles={timeframe: verified_candles[timeframe] for timeframe in timeframes},
            data_quality=data_quality,
        )

    def _providers(self, account):
        if self.provider_factories is not None:
            return [(name, factory()) for name, factory in self.provider_factories]
        providers = []
        if getattr(settings, 'TWELVE_DATA_API_KEY', ''):
            providers.append(('TwelveData', TwelveDataProvider(settings.TWELVE_DATA_API_KEY)))
        if getattr(settings, 'FCSAPI_API_KEY', ''):
            providers.append(('FCSAPI', FCSApiProvider(settings.FCSAPI_API_KEY)))
        if getattr(account, 'connection_method', 'BROKER') == 'METAAPI':
            providers.append(('MetaAPI', MetaApiHistoricalProvider()))
        return providers

    @staticmethod
    def _fetch_provider(name, provider, account, timeframes, candle_count):
        frames = {}
        symbol = account.broker_symbol if name == 'MetaAPI' else account.canonical_asset or account.broker_symbol
        account_identity = getattr(account, 'external_account_id', '') if name == 'MetaAPI' else ''
        cache_identity = hashlib.sha256(
            f'{name}:{account_identity}:{symbol}:{candle_count}'.encode('utf-8')
        ).hexdigest()
        cooldown_key = f'market-data-provider-cooldown:{name}'
        if cache.get(cooldown_key):
            raise MarketDataProviderError(name, rate_limited=True)
        for timeframe in timeframes:
            data_key = f'market-data-candles:{cache_identity}:{timeframe}'
            cached = cache.get(data_key)
            if cached is not None:
                frames[timeframe] = cached
                continue
            try:
                if name == 'MetaAPI':
                    candles = provider.candles(account, account.broker_symbol, timeframe, candle_count)
                else:
                    candles = provider.candles(symbol, timeframe, candle_count)
                frames[timeframe] = candles
                cache.set(data_key, candles, timeout=_CACHE_SECONDS.get(timeframe, 60))
            except MarketDataProviderError as error:
                if error.rate_limited:
                    cache.set(cooldown_key, True, timeout=60)
                    raise
                frames[timeframe] = []
        return frames

    @staticmethod
    def _verify_candles(feeds, threshold):
        timestamps = {
            name: {candle['time']: candle for candle in candles}
            for name, candles in feeds.items()
        }
        common_times = set()
        for first, second in combinations(timestamps, 2):
            common_times.update(timestamps[first].keys() & timestamps[second].keys())

        if not common_times:
            anchor = MarketDataService._preferred_source(feeds)
            return feeds[anchor], {
                'verified': False,
                'sources': list(feeds),
                'reason': 'Providers returned no overlapping candle timestamps.',
            }

        comparison_times = sorted(common_times)[-20:]
        compatible_sources = set(feeds)
        max_deviation = 0.0
        for candle_time in comparison_times:
            pairs = []
            for first, second in combinations(compatible_sources, 2):
                first_candle = timestamps[first].get(candle_time)
                second_candle = timestamps[second].get(candle_time)
                if first_candle and second_candle:
                    deviation = max(
                        abs(first_candle[field] - second_candle[field])
                        / max(abs(first_candle[field]), abs(second_candle[field]), 1e-12)
                        * 100
                        for field in ('open', 'high', 'low', 'close')
                    )
                    max_deviation = max(max_deviation, deviation)
                    if deviation <= threshold:
                        pairs.append((first, second))
            if len(compatible_sources) < 2:
                break
            if not pairs:
                compatible_sources = set()
                break
            candidates = set(max(pairs, key=lambda pair: sum(
                1 for other in compatible_sources if other in pair
            )))
            for size in range(len(compatible_sources), 1, -1):
                matches = [
                    group for group in combinations(compatible_sources, size)
                    if all(
                        (first, second) in pairs or (second, first) in pairs
                        for first, second in combinations(group, 2)
                    )
                ]
                if matches:
                    candidates = set(matches[0])
                    break
            compatible_sources &= candidates

        minimum_majority = len(feeds) // 2 + 1
        verified = len(compatible_sources) >= 2 and len(compatible_sources) >= minimum_majority
        selected_feeds = (
            {name: feeds[name] for name in compatible_sources}
            if verified
            else feeds
        )
        selected_source = MarketDataService._preferred_source(selected_feeds)
        return feeds[selected_source], {
            'verified': verified,
            'sources': sorted(compatible_sources),
            'availableSources': list(feeds),
            'maxDeviationPercent': round(max_deviation, 6),
            'reason': (
                'Overlapping candles agree within the configured tolerance.'
                if verified
                else 'Too few providers agree, or provider candles conflict.'
            ),
        }

    @staticmethod
    def _preferred_source(feeds):
        priorities = {'MT5': 0, 'MetaAPI': 1, 'TwelveData': 2, 'FCSAPI': 3}
        return min(feeds, key=lambda source: priorities.get(source, 10))

    def fetch_snapshot(self, account) -> MarketSnapshot:
        return self.fetch(account, timeframes=('M1',), candle_count=1).snapshot


market_data_service = MarketDataService()
