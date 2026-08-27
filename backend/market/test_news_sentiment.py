from django.test import SimpleTestCase

from .news_sentiment import aggregate_headlines, fetch_news_sentiment, score_headline


class NewsSentimentTests(SimpleTestCase):
    def test_headline_score_is_directional(self):
        self.assertEqual(score_headline('Gold rally after strong growth').label, 'BULLISH')
        self.assertEqual(score_headline('Markets fear recession and selloff').label, 'BEARISH')

    def test_aggregate_locks_high_impact_extreme_sentiment(self):
        result = aggregate_headlines([
            {'title': 'FOMC rate decision sparks sharp selloff', 'source': 'wire'},
            {'title': 'Fed warns of downside risk', 'source': 'wire'},
        ], symbol='XAUUSD')
        self.assertTrue(result.news_locked)
        self.assertEqual(result.state, 'BLOCK')
        self.assertEqual(result.label, 'BEARISH')

    def test_missing_provider_fails_closed(self):
        result = fetch_news_sentiment(symbol='XAUUSD', url='http://127.0.0.1:1/news', timeout=0.01)
        self.assertFalse(result.provider_available)
        self.assertTrue(result.news_locked)
        self.assertEqual(result.state, 'DEGRADED')