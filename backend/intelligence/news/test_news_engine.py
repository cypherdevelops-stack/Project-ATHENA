from datetime import datetime, timezone

from django.test import TestCase

from .contracts import NewsEvent
from .engine import NewsEngine
from .models import AdaptiveNewsStatistic
from .models import NewsProviderQuality
from .normalizer import normalize_event
from .reaction import assess_market_reaction
from .risk import assess_execution_conditions, assess_news_risk
from .sentiment import SentimentResult, analyze_sentiment
from .surprise import normalized_surprise


class StaticProvider:
    def __init__(self, items):
        self.items = items

    def fetch_latest(self, *, symbols):
        return self.items


class StaticCalendarProvider:
    def __init__(self, items):
        self.items = items

    def fetch_events(self, *, start, end):
        return self.items


class NamedStaticProvider:
    def __init__(self, name, items):
        self.name = name
        self.items = items
        self.calls = 0

    def fetch_latest(self, *, symbols):
        self.calls += 1
        return self.items


class FailingProvider:
    name = 'failing_provider'

    def fetch_latest(self, *, symbols):
        raise RuntimeError('provider unavailable')


class FixedSentimentModel:
    name = 'test_model'
    version = 'test-1'

    def analyze(self, event):
        return SentimentResult('BULLISH', 0.8, 0.9, self.name, self.version)


class NewsEngineTests(TestCase):
    def test_provider_selection_uses_remaining_quota_and_skips_exhausted_sources(self):
        lower_capacity = NamedStaticProvider('lower_capacity', [{'title': 'Lower capacity story'}])
        higher_capacity = NamedStaticProvider('higher_capacity', [{'title': 'Higher capacity story'}])
        for _ in range(10):
            NewsProviderQuality.objects.create(
                provider_name='lower_capacity',
                available=True,
                item_count=1,
            )
        for _ in range(10):
            NewsProviderQuality.objects.create(
                provider_name='higher_capacity',
                available=True,
                item_count=1,
            )
        engine = NewsEngine(
            [lower_capacity, higher_capacity],
            settings={
                'required_provider_count': 1,
                'provider_limits': {
                    'lower_capacity': {'period_seconds': 86400, 'limit': 10},
                    'higher_capacity': {'period_seconds': 86400, 'limit': 100},
                },
            },
        )

        result = engine.analyze(symbol='XAUUSD')

        self.assertTrue(result.provider_available)
        self.assertEqual(lower_capacity.calls, 0)
        self.assertEqual(higher_capacity.calls, 1)

    def test_engine_keeps_healthy_provider_when_another_source_fails(self):
        result = NewsEngine(
            [FailingProvider(), StaticProvider([{
                'title': 'Dollar gains on strong growth',
                'source': 'wire',
                'published_at': '2026-08-27T12:00:00+00:00',
            }])],
            settings={'required_provider_count': 2},
        ).analyze(
            symbol='EURUSD',
            now=datetime(2026, 8, 27, 12, 1, tzinfo=timezone.utc),
        )

        self.assertTrue(result.provider_available)
        self.assertEqual(len(result.events), 1)
        self.assertFalse(NewsProviderQuality.objects.get(provider_name='failing_provider').available)

    def test_engine_builds_all_configured_news_sources(self):
        engine = NewsEngine(settings={
            'feed_url': 'https://feed.test/news',
            'rss_url': 'https://feed.test/rss',
            'calendar_url': 'https://feed.test/calendar',
        })

        self.assertEqual(
            {provider.name for provider in engine.providers},
            {'json_feed', 'rss_feed'},
        )
        self.assertEqual(engine.calendar_provider.name, 'economic_calendar')

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

    def test_contrary_market_reaction_is_explicit(self):
        reaction = assess_market_reaction(expected_score=0.8, before_price=100, after_price=99)
        self.assertEqual(reaction.state, 'CONTRARY')

    def test_abnormal_conditions_block_execution(self):
        allowed, codes, _ = assess_execution_conditions(spread=2.0, max_spread=1.0, volatility='EXTREME')
        self.assertFalse(allowed)
        self.assertEqual(set(codes), {'SPREAD_ABNORMAL', 'VOLATILITY_ABNORMAL'})

    def test_high_impact_event_window_blocks(self):
        event = normalize_event({
            'title': 'FOMC decision',
            'importance': 'HIGH',
            'timestamp': '2026-08-27T12:00:00+00:00',
        })
        risk, allowed, codes = assess_news_risk(
            [event], now=datetime(2026, 8, 27, 11, 50, tzinfo=timezone.utc),
        )
        self.assertEqual(risk, 'HIGH')
        self.assertFalse(allowed)
        self.assertIn('HIGH_IMPACT_EVENT_WINDOW', codes)

    def test_adaptive_advice_requires_minimum_history(self):
        advice = NewsEngine(StaticProvider([{
            'title': 'Federal Reserve supports dollar',
            'source': 'central_bank',
            'published_at': '2026-08-27T12:00:00+00:00',
        }])).analyze(symbol='XAUUSD')
        self.assertEqual(advice.adaptive_advice['status'], 'INSUFFICIENT_HISTORY')
        self.assertEqual(AdaptiveNewsStatistic.objects.count(), 0)

    def test_configured_calendar_event_enters_news_risk_window(self):
        engine = NewsEngine(
            StaticProvider([{'title': 'Market update', 'published_at': '2026-08-27T11:00:00+00:00'}]),
            calendar_provider=StaticCalendarProvider([{
                'event_id': 'fomc-1', 'title': 'FOMC rate decision', 'entities': ['USD'],
                'timestamp': '2026-08-27T12:10:00+00:00', 'importance': 'CRITICAL',
            }]),
        )
        result = engine.analyze(symbol='XAUUSD', now=datetime(2026, 8, 27, 12, tzinfo=timezone.utc))
        self.assertEqual(result.instruments['XAUUSD'].event_risk, 'CRITICAL')
        self.assertFalse(result.instruments['XAUUSD'].execution_allowed)

    def test_custom_sentiment_model_is_replaceable(self):
        event = normalize_event({'title': 'Neutral headline'})
        result = analyze_sentiment(event, FixedSentimentModel())
        self.assertEqual(result.model_name, 'test_model')
        self.assertEqual(result.score, 0.8)

    def test_relationships_are_asset_relative(self):
        provider = StaticProvider([{
            'title': 'Dollar rallies on strong growth',
            'source': 'wire',
            'published_at': '2026-08-27T12:00:00+00:00',
        }])
        eur = NewsEngine(provider).analyze(symbol='EURUSD')
        jpy = NewsEngine(provider).analyze(symbol='USDJPY')
        self.assertEqual(eur.for_symbol('EURUSD').fundamental_bias, 'BEARISH')
        self.assertEqual(jpy.for_symbol('USDJPY').fundamental_bias, 'BULLISH')
        self.assertGreater(eur.entity_pressure['USD'], 0)

    def test_provider_quality_is_recorded_for_engine_calls(self):
        NewsEngine(StaticProvider([{'title': 'Dollar gains'}])).analyze(symbol='XAUUSD')
        metric = NewsProviderQuality.objects.get(provider_name='news_provider')
        self.assertTrue(metric.available)
        self.assertEqual(metric.item_count, 1)
