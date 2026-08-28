from datetime import datetime, timedelta, timezone

from django.contrib.auth.models import User
from django.test import TestCase

from backend.accounts.models import Account
from .contracts import NewsEvent
from .lifecycle import advance_event_state
from .models import NewsIntelligenceSnapshot
from .tasks import poll_news_for_account


class NewsLifecycleTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='news-worker@example.com', password='Strong-password-123')
        self.account = Account.objects.create(
            user=user,
            enabled=True,
            canonical_asset='XAUUSD',
            broker_symbol='XAUUSD.Z',
        )

    def test_event_lifecycle_advances_by_time(self):
        now = datetime(2026, 8, 27, 12, tzinfo=timezone.utc)
        event = NewsEvent('event', now + timedelta(minutes=5), 'calendar', 0.9, 'FOMC')
        self.assertEqual(advance_event_state(event, now=now).event_state, 'RELEVANT')
        self.assertEqual(advance_event_state(event, now=now + timedelta(minutes=6)).event_state, 'REACTING')
        self.assertEqual(advance_event_state(event, now=now + timedelta(hours=1)).event_state, 'DECAYING')
        self.assertEqual(advance_event_state(event, now=now + timedelta(days=2)).event_state, 'EXPIRED')

    def test_worker_persists_degraded_snapshot_without_execution(self):
        result = poll_news_for_account(account=self.account)
        self.assertEqual(result['status'], 'DEGRADED')
        self.assertEqual(NewsIntelligenceSnapshot.objects.count(), 1)
        self.assertFalse(NewsIntelligenceSnapshot.objects.get().execution_allowed)
