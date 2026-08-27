from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import User
from django.test import TestCase

from backend.accounts.models import Account
from backend.execution.models import BrokerPositionSnapshot, ExecutionLifecycleEvent, LiveExecutionAttempt
from backend.execution.reconciliation import reconcile_live_positions


class ReconciliationTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(
            user=User.objects.create_user(username='reconcile@example.com'),
            account_type=Account.AccountType.DEMO,
            broker_symbol='XAUUSD.Z',
            login='1',
            server='demo',
            reconciliation_safe=False,
        )

    def mt5(self, positions):
        return SimpleNamespace(
            initialize=lambda path: True,
            login=lambda login, password, server: True,
            positions_get=lambda symbol: positions,
            shutdown=lambda: None,
        )

    @patch('backend.execution.reconciliation.decrypt_password', return_value='password')
    def test_successful_empty_position_query_restores_safety(self, decrypt_mock):
        result = reconcile_live_positions(account=self.account, mt5_module=self.mt5(()))

        self.assertEqual(result['status'], 'SAFE')
        self.account.refresh_from_db()
        self.assertTrue(self.account.reconciliation_safe)
        self.assertIsNotNone(self.account.last_reconciliation_at)

    @patch('backend.execution.reconciliation.decrypt_password', return_value='password')
    def test_failed_position_query_halts_execution(self, decrypt_mock):
        result = reconcile_live_positions(account=self.account, mt5_module=self.mt5(None))

        self.assertEqual(result['status'], 'UNSAFE')
        self.account.refresh_from_db()
        self.assertFalse(self.account.reconciliation_safe)
        self.assertEqual(
            list(ExecutionLifecycleEvent.objects.values_list('event_type', flat=True)),
            ['LIVE_EXECUTION_HALTED', 'RECONCILIATION_FAILED'],
        )

    @patch('backend.execution.reconciliation.decrypt_password', return_value='password')
    def test_position_snapshot_is_updated_and_closed_when_broker_position_disappears(self, decrypt_mock):
        position = SimpleNamespace(ticket=321, symbol='XAUUSD.Z', type=0, volume=0.1, price_open=100, sl=99, tp=102)
        first = reconcile_live_positions(account=self.account, mt5_module=self.mt5((position,)))
        self.assertEqual(first['status'], 'SAFE')
        self.assertEqual(BrokerPositionSnapshot.objects.get().state, 'ACTIVE')

        second = reconcile_live_positions(account=self.account, mt5_module=self.mt5(()))

        self.assertEqual(second['status'], 'SAFE')
        snapshot = BrokerPositionSnapshot.objects.get(ticket=321)
        self.assertEqual(snapshot.state, 'CLOSED')
        self.assertIsNotNone(snapshot.closed_at)
        self.assertTrue(ExecutionLifecycleEvent.objects.filter(event_type='POSITION_CLOSED').exists())