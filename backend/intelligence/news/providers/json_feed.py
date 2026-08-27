from __future__ import annotations

import json
from urllib.request import Request, urlopen


class JsonFeedProvider:
    name = 'json_feed'

    def __init__(self, url: str, *, timeout: float = 3.0):
        self.url = url
        self.timeout = timeout

    def fetch_latest(self, *, symbols: list[str]) -> list[dict]:
        request = Request(self.url, headers={'Accept': 'application/json', 'User-Agent': 'ATHENA/1.0'})
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
