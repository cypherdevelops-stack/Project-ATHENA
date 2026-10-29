from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class NewsApiProvider:
    name = 'newsapi'

    def __init__(self, api_key: str, *, timeout: float = 3.0):
        self.api_key = api_key
        self.timeout = timeout

    def fetch_latest(self, *, symbols: list[str]) -> list[dict]:
        query = ' OR '.join(dict.fromkeys([*symbols, 'forex', 'gold', 'markets', 'central bank']))
        url = 'https://newsapi.org/v2/everything?' + urlencode({
            'q': query,
            'language': 'en',
            'sortBy': 'publishedAt',
            'pageSize': 100,
        })
        request = Request(url, headers={
            'Accept': 'application/json',
            'User-Agent': 'ATHENA/1.0',
            'X-Api-Key': self.api_key,
        })
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
        if not isinstance(payload, dict) or payload.get('status') != 'ok':
            raise ValueError('NewsAPI returned an unsuccessful response.')
        articles = payload.get('articles', [])
        if not isinstance(articles, list):
            raise ValueError('NewsAPI articles must be a list.')
        return [
            {
                'title': article.get('title', ''),
                'summary': article.get('description') or article.get('content') or '',
                'source': (article.get('source') or {}).get('name') or self.name,
                'published_at': article.get('publishedAt'),
                'url': article.get('url'),
            }
            for article in articles
            if isinstance(article, dict)
        ]
