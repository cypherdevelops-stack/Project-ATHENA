from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class FinnhubNewsProvider:
    name = 'finnhub'

    def __init__(self, api_key: str, *, timeout: float = 3.0):
        self.api_key = api_key
        self.timeout = timeout

    def fetch_latest(self, *, symbols: list[str]) -> list[dict]:
        url = 'https://finnhub.io/api/v1/news?' + urlencode({
            'category': 'general',
            'token': self.api_key,
        })
        request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'ATHENA/1.0'})
        with urlopen(request, timeout=self.timeout) as response:
            items = json.loads(response.read().decode('utf-8'))
        if not isinstance(items, list):
            raise ValueError('Finnhub news response must be a list.')
        return [
            {
                'title': item.get('headline', ''),
                'summary': item.get('summary', ''),
                'source': item.get('source') or self.name,
                'published_at': datetime.fromtimestamp(item['datetime'], timezone.utc).isoformat()
                if isinstance(item.get('datetime'), (int, float)) else None,
                'url': item.get('url'),
                'category': item.get('category'),
                'related': item.get('related'),
            }
            for item in items
            if isinstance(item, dict)
        ]
