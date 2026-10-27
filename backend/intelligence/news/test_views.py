import json
from datetime import datetime, timezone

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from backend.accounts.models import Account
from .models import NewsAMEFRecord
from .persistence import persist_news_snapshot


class NewsApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='news-api@example.com', password='Strong-password-123')
        self.other_user = User.objects.create_user(username='other-news-api@example.com', password='Strong-password-123')
        self.account = Account.objects.create(user=self.user, enabled=True, canonical_asset='XAUUSD', broker_symbol='XAUUSD.Z')
        self.other_account = Account.objects.create(user=self.other_user, enabled=True, canonical_asset='EURUSD', broker_symbol='EURUSD.Z')
        self.snapshot = persist_news_snapshot(account=self.account, analysis={
            'news': {
                'provider_available': True, 'state': 'PASS', 'score': 0.6, 'confidence': 0.8, 'label': 'BULLISH',
                'events': [{'event_id': 'fed-1', 'category': 'CENTRAL_BANK', 'event_state': 'ACTIVE'}],
                'instruments': {'XAUUSD': {'fundamental_bias': 'BULLISH', 'event_risk': 'LOW', 'execution_allowed': True, 'impact_score': 0.7}},
            },
            'newsReaction': {'state': 'CONFIRMED', 'expected_direction': 'UP', 'actual_direction': 'UP'},
        })
        persist_news_snapshot(account=self.other_account, analysis={'news': {'state': 'PASS', 'events': []}})

    def test_current_endpoint_returns_owned_snapshot_and_amef_exists(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/news/current?accountId=%s&symbol=XAUUSD' % self.account.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['news']['snapshotId'], str(self.snapshot.snapshot_id))
        self.assertTrue(NewsAMEFRecord.objects.filter(news_snapshot_id=self.snapshot.pk).exists())

    def test_snapshot_list_filters_by_symbol_and_does_not_leak_accounts(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/news/snapshots?symbol=XAUUSD')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['snapshots']), 1)
        self.assertEqual(response.json()['snapshots'][0]['symbol'], 'XAUUSD')

    def test_reactions_endpoint_returns_owned_reaction(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/news/reactions?symbol=XAUUSD&state=CONFIRMED')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reactions'][0]['state'], 'CONFIRMED')

    def test_provider_health_endpoint_is_authenticated(self):
        response = self.client.get('/api/news/providers/health')
        self.assertEqual(response.status_code, 302)