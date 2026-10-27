from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from backend.accounts.credentials import decrypt_password
from backend.accounts.metaapi import PROVISIONING_API, _get_json

from .context import normalize_candles


REQUEST_TIMEOUT_SECONDS = 10
TIMEFRAME_MAP = {
    'M1': ('1min', '1m'),
    'M5': ('5min', '5m'),
    'M15': ('15min', '15m'),
    'M30': ('30min', '30m'),
    'H1': ('1h', '1h'),
    'H4': ('4h', '4h'),
    'D1': ('1day', '1d'),
}


class MarketDataProviderError(RuntimeError):
    def __init__(self, source: str, *, rate_limited: bool = False):
        self.source = source
        self.rate_limited = rate_limited
        super().__init__(f'{source} request limit reached.' if rate_limited else f'{source} data unavailable.')


def _request_json(source: str, url: str) -> object:
    request = Request(url, headers={'Accept': 'application/json'}, method='GET')
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as error:
        raise MarketDataProviderError(source, rate_limited=error.code == 429) from error
    except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MarketDataProviderError(source) from error


def _rate_limited(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    error = str(payload.get('message') or payload.get('msg') or payload.get('note') or '').lower()
    return any(token in error for token in ('rate limit', 'request limit', 'too many requests', 'quota exceeded', '429'))


def _failed_response(source: str, payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    failed = (
        payload.get('status') is False
        or str(payload.get('status', '')).lower() in {'error', 'failed'}
        or bool(payload.get('code') and payload.get('message'))
    )
    if failed:
        raise MarketDataProviderError(source, rate_limited=_rate_limited(payload))
    return False


def _canonical_symbol(symbol: str) -> str:
    normalized = ''.join(character for character in str(symbol).upper() if character.isalnum())
    if len(normalized) == 6 and normalized.isalpha():
        return f'{normalized[:3]}/{normalized[3:]}'
    if normalized == 'XAUUSD':
        return 'XAU/USD'
    return symbol


def _record_value(record: dict, *keys: str, default=0):
    for key in keys:
        if key in record:
            return record[key]
    return default


def _normalize_provider_candles(records: object) -> list[dict]:
    if not isinstance(records, list):
        raise MarketDataProviderError('Provider')
    normalized_records = []
    for record in records:
        if not isinstance(record, dict):
            continue
        timestamp = _record_value(record, 'time', 'datetime', 'tm', 'timestamp', 't', default=None)
        if timestamp is None:
            continue
        try:
            if isinstance(timestamp, (int, float)):
                candle_time = int(timestamp)
            else:
                parsed = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                candle_time = int(parsed.timestamp())
            candle = {
                'time': candle_time,
                'open': float(_record_value(record, 'open', 'o')),
                'high': float(_record_value(record, 'high', 'h')),
                'low': float(_record_value(record, 'low', 'l')),
                'close': float(_record_value(record, 'close', 'c')),
                'volume': int(float(_record_value(record, 'volume', 'tickVolume', 'tick_volume', 'v'))),
            }
        except (OverflowError, TypeError, ValueError):
            continue
        prices = (candle['open'], candle['high'], candle['low'], candle['close'])
        if not all(math.isfinite(price) and price > 0 for price in prices):
            continue
        if candle['high'] < max(candle['open'], candle['close'], candle['low']):
            continue
        if candle['low'] > min(candle['open'], candle['close'], candle['high']):
            continue
        normalized_records.append(candle)
    if not normalized_records:
        raise MarketDataProviderError('Provider')
    by_time = {candle['time']: candle for candle in normalized_records}
    return [by_time[key] for key in sorted(by_time)]


class TwelveDataProvider:
    source = 'TwelveData'

    def __init__(self, api_key: str):
        self.api_key = api_key

    def candles(self, symbol: str, timeframe: str, count: int) -> list[dict]:
        interval = TIMEFRAME_MAP.get(timeframe, (None, None))[0]
        if not interval:
            raise MarketDataProviderError(self.source)
        query = urlencode({
            'symbol': _canonical_symbol(symbol),
            'interval': interval,
            'outputsize': min(count, 5000),
            'apikey': self.api_key,
        })
        payload = _request_json(self.source, f'https://api.twelvedata.com/time_series?{query}')
        _failed_response(self.source, payload)
        records = payload.get('values') if isinstance(payload, dict) else None
        return _normalize_provider_candles(records)[-count:]


class FCSApiProvider:
    source = 'FCSAPI'

    def __init__(self, api_key: str):
        self.api_key = api_key

    def candles(self, symbol: str, timeframe: str, count: int) -> list[dict]:
        period = TIMEFRAME_MAP.get(timeframe, (None, None))[1]
        if not period:
            raise MarketDataProviderError(self.source)
        query = urlencode({
            'symbol': _canonical_symbol(symbol),
            'period': period,
            'access_key': self.api_key,
            'count': min(count, 2000),
        })
        payload = _request_json(self.source, f'https://fcsapi.com/api-v3/forex/history?{query}')
        _failed_response(self.source, payload)
        records = payload.get('response') if isinstance(payload, dict) else None
        return _normalize_provider_candles(records)[-count:]


class MetaApiHistoricalProvider:
    source = 'MetaAPI'

    def candles(self, account, symbol: str, timeframe: str, count: int) -> list[dict]:
        interval = TIMEFRAME_MAP.get(timeframe, (None, None))[1]
        if not interval:
            raise MarketDataProviderError(self.source)
        token = decrypt_password(account.password_encrypted)
        account_id = quote(str(account.external_account_id), safe='')
        market_discovery = account.market_discovery or {}
        region = str(market_discovery.get('metaApiRegion') or '').strip()
        if not region:
            profile = _get_json(
                f'{PROVISIONING_API}/users/current/accounts/{account_id}',
                token,
            )
            region = str(profile.get('region', '') if isinstance(profile, dict) else '').strip()
        if not region or any(character not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-' for character in region):
            raise MarketDataProviderError(self.source)
        base_url = f'https://mt-market-data-client-api-v1.{region}.agiliumtrade.ai'
        endpoint = (
            f'{base_url}/users/current/accounts/{account_id}/historical-market-data/'
            f'symbols/{quote(symbol, safe="")}/timeframes/{interval}/candles?'
            f'{urlencode({"limit": min(count, 1000)})}'
        )
        request = Request(
            endpoint,
            headers={'Accept': 'application/json', 'auth-token': token},
            method='GET',
        )
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except HTTPError as error:
            raise MarketDataProviderError(self.source, rate_limited=error.code == 429) from error
        except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise MarketDataProviderError(self.source) from error
        return _normalize_provider_candles(payload)[-count:]
