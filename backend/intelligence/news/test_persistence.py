from django.contrib.auth.models import User
from django.test import TestCase

from backend.accounts.models import Account
from .models import NewsIntelligenceSnapshot, NewsReactionObservation
from .persistence import persist_news_snapshot


class NewsPersistenceTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='news-persistence@example.com', password='Strong-password-123')
        self.account = Account.objects.create(
            user=user,
            broker_symbol='XAUUSD.Z',
            canonical_asset='XAUUSD',
        )

    def test_persists_point_in_time_news_and_reaction_context(self):
        snapshot = persist_news_snapshot(
            account=self.account,
            analysis={
                'news': {
                    'provider_available': True,
                    'state': 'PASS',
                    'score': -0.7,
                    'confidence': 0.9,
                    'label': 'BEARISH',
                    'events': [{'event_id': 'fed-1'}],
                    'instruments': {
                        'XAUUSD': {
                            'fundamental_bias': 'BEARISH',
                            'event_risk': 'HIGH',
                            'execution_allowed': False,
                            'technical_alignment': 'CONFLICT',
                            'technical_conflict': True,
                            'impact_score': 0.8,
                            'reason_codes': ['TECHNICAL_FUNDAMENTAL_CONFLICT'],
                        },
                    },
                },
                'newsReaction': {
                    'expected_direction': 'DOWN',
                    'actual_direction': 'UP',
                    'state': 'CONTRARY',
                    'price_change': 0.001,
                    'volatility': 'HIGH',
                    'spread': 1.5,
                },
                'executionConditions': {'allowed': False, 'reasonCodes': ['SPREAD_ABNORMAL']},
            },
        )

        self.assertIsNotNone(snapshot)
        self.assertEqual(NewsIntelligenceSnapshot.objects.count(), 1)
        self.assertEqual(NewsReactionObservation.objects.get().reaction_state, 'CONTRARY')
        self.assertFalse(snapshot.execution_allowed)
        self.assertEqual(snapshot.reason_codes, ['TECHNICAL_FUNDAMENTAL_CONFLICT'])
