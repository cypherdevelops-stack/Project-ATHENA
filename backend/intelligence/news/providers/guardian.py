from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class GuardianNewsProvider:
    name = 'guardian'

    def __init__(self, api_key: str, *, timeout: float = 3.0):
        self.api_key = api_key
        self.timeout = timeout

    def fetch_latest(self, *, symbols: list[str]) -> list[dict]:
        query_terms = ' OR '.join(dict.fromkeys([*symbols, 'forex', 'gold', 'markets', 'central bank']))
        url = 'https://content.guardianapis.com/search?' + urlencode({
            'q': query_terms,
            'section': 'business|world',
            'order-by': 'newest',
            'page-size': 50,
            'show-fields': 'trailText,headline',
            'api-key': self.api_key,
        })
        request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'ATHENA/1.0'})
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
        response_data = payload.get('response', {}) if isinstance(payload, dict) else {}
        if response_data.get('status') != 'ok':
            raise ValueError('The Guardian API returned an unsuccessful response.')
        results = response_data.get('results', [])
        if not isinstance(results, list):
            raise ValueError('The Guardian API results must be a list.')
        return [
            {
                'title': result.get('webTitle', ''),
                'summary': (result.get('fields') or {}).get('trailText', ''),
                'source': self.name,
                'published_at': result.get('webPublicationDate'),
                'url': result.get('webUrl'),
                'category': result.get('sectionName'),
            }
            for result in results
            if isinstance(result, dict)
        ]
