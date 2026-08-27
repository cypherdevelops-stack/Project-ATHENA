from datetime import datetime, timezone

from django.test import SimpleTestCase

from .contracts import NewsEvent
from .engine import NewsEngine
from .normalizer import normalize_event
from .sentiment import analyze_sentiment
from .surprise import normalized_surprise


class StaticProvider:
    def __init__(self, items):
        self.items = items

    def fetch_latest(self, *, symbols):
        return self.items


class NewsEngineTests(SimpleTestCase):
    def test_engine_creates_asset_relative_usd_impact(self):
        engine = NewsEngine(StaticProvider([{
            'id': 'fed-1', 'title': 'Federal Reserve hawkish rate decision supports dollar',
            'source': 'central_bank', 'source_reliability': 0.96,
            'published_at': '2026-08-27T12:00:00+00:00', 'importance': 'HIGH',
        }]))
        result = engine.analyze(symbol='XAUUSD', technical_direction='BUY', now=datetime(2026, 8, 27, 12, 1, tzinfo=timezone.utc))
        instrument = result.for_symbol('XAUUSD')
        self.assertEqual(instrument.fundamental_bias, 'BEARISH')
        self.assertTrue(instrument.technical_conflict)
        self.assertFalse(instrument.execution_allowed)

    def test_normalization_and_financial_negation(self):
        event = normalize_event({'title': 'Inflation fell less than expected', 'source': 'wire'})
        self.assertEqual(analyze_sentiment(event).label, 'BEARISH')

    def test_surprise_is_normalized(self):
        self.assertEqual(normalized_surprise(actual=2.7, forecast=3.0, scale=3.0), -0.1)

    def test_news_event_contract_serializes(self):
        event = NewsEvent('id', datetime.now(timezone.utc), 'wire', 0.8, 'Headline')
        self.assertEqual(event.as_dict()['event_id'], 'id')
