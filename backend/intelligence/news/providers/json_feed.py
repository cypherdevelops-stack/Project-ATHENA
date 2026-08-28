from __future__ import annotations

import json
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from urllib.request import Request, urlopen


class JsonFeedProvider:
    name = 'json_feed'

    def __init__(self, url: str, *, timeout: float = 3.0, api_key: str | None = None, api_key_header: str = 'Authorization'):
        self.url = url
        self.timeout = timeout
        self.api_key = api_key
        self.api_key_header = api_key_header

    def fetch_latest(self, *, symbols: list[str]) -> list[dict]:
        query = [('symbols', ','.join(symbols))] if symbols else []
        request = Request(self._url_with_query(query), headers=self._headers('application/json'))
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            raise ValueError('News provider response must be an object or list.')
        items = payload.get('articles', payload.get('headlines', []))
        if not isinstance(items, list):
            raise ValueError('News provider articles must be a list.')
        return items

    def _headers(self, accept: str) -> dict[str, str]:
        headers = {'Accept': accept, 'User-Agent': 'ATHENA/1.0'}
        if self.api_key:
            headers[self.api_key_header] = f'Bearer {self.api_key}' if self.api_key_header.lower() == 'authorization' else self.api_key
        return headers

    def _url_with_query(self, extra: list[tuple[str, str]]) -> str:
        parts = urlsplit(self.url)
        query = parse_qsl(parts.query, keep_blank_values=True) + extra
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
