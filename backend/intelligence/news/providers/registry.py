from __future__ import annotations

from .economic_calendar import EconomicCalendarProvider
from .finnhub import FinnhubNewsProvider
from .guardian import GuardianNewsProvider
from .json_feed import JsonFeedProvider
from .newsapi import NewsApiProvider
from .rss_feed import RssFeedProvider

class ProviderRegistry:
    def __init__(self):
        self._providers = {}

    def register(self, provider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str):
        return self._providers.get(name)

    def news_sources(self) -> list:
        return [
            provider for name, provider in self._providers.items()
            if name != 'economic_calendar'
        ]

    def calendar(self):
        return self.get('economic_calendar')

    def health(self) -> dict[str, bool]:
        return {name: provider is not None for name, provider in self._providers.items()}


def build_configured_registry(settings: dict) -> ProviderRegistry:
    registry = ProviderRegistry()
    common = {
        'timeout': settings.get('timeout', 3.0),
        'api_key': settings.get('api_key'),
        'api_key_header': settings.get('api_key_header', 'Authorization'),
    }
    if settings.get('feed_url'):
        registry.register(JsonFeedProvider(settings['feed_url'], **common))
    if settings.get('calendar_url'):
        registry.register(EconomicCalendarProvider(settings['calendar_url'], **common))
    rss_url = settings.get('rss_url')
    if rss_url:
        registry.register(RssFeedProvider(rss_url, **common))
    if settings.get('finnhub_api_key'):
        registry.register(FinnhubNewsProvider(settings['finnhub_api_key'], timeout=common['timeout']))
    if settings.get('newsapi_api_key'):
        registry.register(NewsApiProvider(settings['newsapi_api_key'], timeout=common['timeout']))
    if settings.get('guardian_api_key'):
        registry.register(GuardianNewsProvider(settings['guardian_api_key'], timeout=common['timeout']))
    return registry
