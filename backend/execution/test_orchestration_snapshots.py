from django.contrib.auth.models import User
from django.test import TestCase

from backend.accounts.models import Account
from backend.execution.models import OrchestrationSnapshot
from backend.execution.snapshot_service import persist_orchestration_snapshot
from backend.execution.views import _open_journal_session
from backend.journal.models import JournalSession


class OrchestrationSnapshotTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='audit@example.com', password='Strong-password-123')
        self.account = Account.objects.create(
            user=user,
            broker_symbol='XAUUSD.Z',
            canonical_asset='XAUUSD',
        )

    def test_successful_analysis_is_persisted_with_traceable_decision(self):
        snapshot = persist_orchestration_snapshot(
            account=self.account,
            analysis={
                'status': 'OBSERVE',
                'price': {'bid': 2350.1, 'ask': 2350.3, 'spread': 0.2},
                'regime': {'regime': 'RANGING'},
                'momentumMap': {
                    'alignment': 'ALIGNED',
                    'interpretation': 'Momentum is aligned.',
                    'confidence': 0.8,
                    'directionalScores': {'BUY': 0.8, 'SELL': 0.0},
                    'timeframes': {'H1': {'direction': 'BULLISH'}},
                },
                'orchestration': {
                    'status': 'OBSERVE',
                    'reason': 'No ready candidates',
                    'decision': {
                        'action': 'OBSERVE',
                        'reason': 'No ready candidates',
                        'reasonCodes': ['NO_READY_CANDIDATE'],
                    },
                    'portfolio': {'risk_available': True, 'account_equity': 100000},
                },
                'scalping': {'status': 'OBSERVE', 'candidates': []},
                'dayTrading': {'status': 'OBSERVE', 'candidates': []},
            },
        )

        self.assertIsNotNone(snapshot)
        self.assertEqual(OrchestrationSnapshot.objects.count(), 1)
        self.assertEqual(snapshot.decision, 'OBSERVE')
        self.assertEqual(snapshot.reason_codes, ['NO_READY_CANDIDATE'])
        self.assertIsNotNone(snapshot.decision_id)
        self.assertEqual(snapshot.full_payload['momentumSnapshot']['alignment'], 'ALIGNED')
        self.assertEqual(snapshot.full_payload['momentumSnapshot']['schemaVersion'], 'macd-momentum-v1')

    def test_error_analysis_is_not_recorded_as_a_trading_decision(self):
        snapshot = persist_orchestration_snapshot(
            account=self.account,
            analysis={'status': 'ERROR', 'reason': 'Market data unavailable'},
        )

        self.assertIsNone(snapshot)
        self.assertEqual(OrchestrationSnapshot.objects.count(), 0)

    def test_duplicate_open_journal_sessions_are_handled_deterministically(self):
        JournalSession.objects.create(user=self.account.user, account=self.account, status='OPEN')
        latest = JournalSession.objects.create(user=self.account.user, account=self.account, status='OPEN')

        session = _open_journal_session(
            user=self.account.user,
            account=self.account,
            symbol='XAUUSD',
            title='XAUUSD multi-strategy session',
        )

        self.assertEqual(session.pk, latest.pk)
