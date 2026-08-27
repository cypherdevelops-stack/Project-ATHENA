from uuid import uuid4

from django.contrib.auth.models import User
from django.test import TestCase

from backend.accounts.models import Account
from backend.execution.models import PaperExecution
from backend.execution.paper_orchestration import execute_paper_decision


class PaperOrchestrationTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='paper@example.com', password='Strong-password-123')
        self.account = Account.objects.create(
            user=user,
            broker_symbol='XAUUSD.Z',
            canonical_asset='XAUUSD',
        )

    def test_non_approved_decision_is_skipped_without_creating_position_record(self):
        result = execute_paper_decision(
            account=self.account,
            analysis={'orchestration': {'decision': {'action': 'OBSERVE'}}},
            decision_id=uuid4(),
            quote={'bid': 100, 'ask': 100.1},
        )

        self.assertEqual(result['status'], 'SKIPPED')
        self.assertEqual(PaperExecution.objects.count(), 1)

    def test_same_decision_is_idempotent(self):
        decision_id = uuid4()
        analysis = {'orchestration': {'decision': {'action': 'DAY_BUY_DEVELOPING', 'strategy': 'DAY_TRADING'}}}

        first = execute_paper_decision(
            account=self.account,
            analysis=analysis,
            decision_id=decision_id,
            quote={'bid': 100, 'ask': 100.1},
        )
        second = execute_paper_decision(
            account=self.account,
            analysis=analysis,
            decision_id=decision_id,
            quote={'bid': 100, 'ask': 100.1},
        )

        self.assertEqual(first['status'], 'SKIPPED')
        self.assertEqual(second['status'], 'SKIPPED')
        self.assertEqual(PaperExecution.objects.count(), 1)
        self.assertTrue(second['duplicate'])
