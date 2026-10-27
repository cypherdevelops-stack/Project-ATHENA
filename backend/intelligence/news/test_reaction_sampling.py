from datetime import datetime, timezone

from django.contrib.auth.models import User
from django.test import TestCase

from backend.accounts.models import Account
from .models import NewsMarketSample, NewsReactionObservation
from .persistence import persist_news_snapshot
from .reaction_sampling import capture_market_sample
from .risk import analysis_execution_allowed


class ReactionSamplingTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='reaction-sampling@example.com', password='Strong-password-123')
        self.account = Account.objects.create(user=user, canonical_asset='XAUUSD', broker_symbol='XAUUSD.Z')
        self.news_snapshot = persist_news_snapshot(
            account=self.account,
            analysis={'news': {'score': 0.8, 'label': 'BULLISH', 'provider_available': True, 'instruments': {'XAUUSD': {'fundamental_bias': 'BULLISH'}}}},
        )

    def test_pre_and_post_samples_update_reaction_observation(self):
        timestamp = datetime(2026, 8, 27, 12, tzinfo=timezone.utc)
        capture_market_sample(news_snapshot=self.news_snapshot, phase='PRE', quote={'bid': 100, 'ask': 100.2}, captured_at=timestamp)
        capture_market_sample(news_snapshot=self.news_snapshot, phase='POST', quote={'bid': 101, 'ask': 101.2}, captured_at=timestamp.replace(minute=5), volatility='HIGH')

        self.assertEqual(NewsMarketSample.objects.count(), 2)
        observation = NewsReactionObservation.objects.get(news_snapshot_id=self.news_snapshot.pk)
        self.assertEqual(observation.reaction_state, 'CONFIRMED')
        self.assertGreater(observation.price_change, 0)

    def test_shared_execution_guard_blocks_locked_news(self):
        allowed, reason = analysis_execution_allowed(
            {'news': {'news_locked': True, 'reason': 'FOMC blackout active.'}},
            symbol='XAUUSD',
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, 'FOMC blackout active.')
