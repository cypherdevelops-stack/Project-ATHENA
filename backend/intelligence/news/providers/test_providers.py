from datetime import datetime, timezone
from unittest.mock import patch

from django.test import SimpleTestCase

from .economic_calendar import EconomicCalendarProvider
from .finnhub import FinnhubNewsProvider
from .guardian import GuardianNewsProvider
from .json_feed import JsonFeedProvider
from .newsapi import NewsApiProvider
from .registry import build_configured_registry


class ResponseStub:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        import json
        return json.dumps(self.payload).encode()


class ProviderTests(SimpleTestCase):
    @patch('backend.intelligence.news.providers.json_feed.urlopen')
    def test_json_provider_sends_authentication_and_symbols(self, open_url):
        open_url.return_value = ResponseStub({'articles': [{'title': 'Dollar gains'}]})
        provider = JsonFeedProvider('https://feed.test/news?limit=10', api_key='secret', api_key_header='X-API-Key')
        items = provider.fetch_latest(symbols=['XAUUSD', 'EURUSD'])
        request = open_url.call_args.args[0]
        self.assertEqual(items[0]['title'], 'Dollar gains')
        self.assertEqual(request.headers['X-api-key'], 'secret')
        self.assertIn('symbols=XAUUSD%2CEURUSD', request.full_url)

    @patch('backend.intelligence.news.providers.economic_calendar.urlopen')
    def test_calendar_provider_normalizes_event_fields(self, open_url):
        open_url.return_value = ResponseStub({'events': [{
            'id': 'cpi-1', 'name': 'CPI', 'currency': 'USD', 'date': '2026-08-27T13:30:00+00:00',
            'impact': 'high', 'estimate': '3.0', 'actual': '2.7',
        }]})
        provider = EconomicCalendarProvider('https://feed.test/calendar')
        events = provider.fetch_events(
            start=datetime(2026, 8, 27, tzinfo=timezone.utc),
            end=datetime(2026, 8, 28, tzinfo=timezone.utc),
        )
        self.assertEqual(events[0]['event_id'], 'cpi-1')
        self.assertEqual(events[0]['title'], 'CPI')
        self.assertEqual(events[0]['importance'], 'HIGH')
        self.assertEqual(events[0]['forecast'], '3.0')
        self.assertIn('start=', open_url.call_args.args[0].full_url)

    def test_registry_builds_only_configured_adapters(self):
        registry = build_configured_registry({
            'feed_url': 'https://feed.test/news',
            'calendar_url': 'https://feed.test/calendar',
            'finnhub_api_key': 'finnhub-secret',
            'newsapi_api_key': 'newsapi-secret',
            'guardian_api_key': 'guardian-secret',
            'timeout': 2.0,
        })
        self.assertEqual(
            registry.health(),
            {
                'json_feed': True,
                'economic_calendar': True,
                'finnhub': True,
                'newsapi': True,
                'guardian': True,
            },
        )

    @patch('backend.intelligence.news.providers.finnhub.urlopen')
    def test_finnhub_provider_normalizes_headline_fields(self, open_url):
        open_url.return_value = ResponseStub([{
            'headline': 'Markets gain',
            'summary': 'A market summary',
            'source': 'Wire',
            'datetime': 1787832000,
            'url': 'https://example.test/article',
        }])
        item = FinnhubNewsProvider('finnhub-secret').fetch_latest(symbols=['XAUUSD'])[0]
        self.assertEqual(item['title'], 'Markets gain')
        self.assertEqual(item['source'], 'Wire')
        self.assertIn('token=finnhub-secret', open_url.call_args.args[0].full_url)

    @patch('backend.intelligence.news.providers.newsapi.urlopen')
    def test_newsapi_provider_sends_key_header_and_normalizes_articles(self, open_url):
        open_url.return_value = ResponseStub({'status': 'ok', 'articles': [{
            'title': 'Dollar gains',
            'description': 'A currency update',
            'source': {'name': 'Wire'},
            'publishedAt': '2026-10-29T12:00:00Z',
        }]})
        item = NewsApiProvider('newsapi-secret').fetch_latest(symbols=['XAUUSD'])[0]
        request = open_url.call_args.args[0]
        self.assertEqual(request.headers['X-api-key'], 'newsapi-secret')
        self.assertEqual(item['source'], 'Wire')

    @patch('backend.intelligence.news.providers.guardian.urlopen')
    def test_guardian_provider_normalizes_results(self, open_url):
        open_url.return_value = ResponseStub({'response': {
            'status': 'ok',
            'results': [{
                'webTitle': 'Gold market update',
                'webPublicationDate': '2026-10-29T12:00:00Z',
                'webUrl': 'https://example.test/guardian',
                'fields': {'trailText': 'Market report'},
            }],
        }})
        item = GuardianNewsProvider('guardian-secret').fetch_latest(symbols=['XAUUSD'])[0]
        self.assertEqual(item['title'], 'Gold market update')
        self.assertEqual(item['summary'], 'Market report')
        self.assertIn('api-key=guardian-secret', open_url.call_args.args[0].full_url)

    def test_generic_json_provider_sends_the_authorization_credential(self):
        provider = JsonFeedProvider(
            'https://feed.test/news',
            api_key='feed-secret',
            api_key_header='Authorization',
        )
        self.assertEqual(provider._headers('application/json')['Authorization'], 'Bearer feed-secret')