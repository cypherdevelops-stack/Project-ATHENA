from __future__ import annotations

from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from xml.etree import ElementTree


class RssFeedProvider:
    name = 'rss_feed'

    def __init__(self, url: str, *, timeout: float = 3.0):
        self.url = url
        self.timeout = timeout

    def fetch_latest(self, *, symbols: list[str]) -> list[dict]:
        request = Request(self.url, headers={'Accept': 'application/rss+xml, application/xml', 'User-Agent': 'ATHENA/1.0'})
        with urlopen(request, timeout=self.timeout) as response:
            root = ElementTree.fromstring(response.read())
        items = []
        for item in root.findall('.//item'):
            published = item.findtext('pubDate')
            items.append({
                'title': item.findtext('title', ''),
                'summary': item.findtext('description', ''),
                'source': self.name,
                'published_at': parsedate_to_datetime(published).isoformat() if published else None,
                'url': item.findtext('link'),
            })
        return items
