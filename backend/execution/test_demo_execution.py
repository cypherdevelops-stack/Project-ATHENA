from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from backend.accounts.models import Account
from backend.execution.demo_execution import DemoExecutionError, execute_automatic_decision, execute_confirmed_demo_decision
from backend.execution.models import ExecutionLifecycleEvent, LiveExecutionAttempt
from backend.execution.snapshot_service import persist_orchestration_snapshot


class ConfirmedDemoExecutionTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='demo@example.com', password='Strong-password-123')
        self.account = Account.objects.create(
            user=user,
            account_type=Account.AccountType.DEMO,
            broker_symbol='XAUUSD.Z',
            canonical_asset='XAUUSD',
            enabled=True,
            terminal_connected=True,
            trade_allowed=True,
            live_execution_enabled=True,
            live_execution_mode='CONFIRMATION_REQUIRED',
            allowed_strategies=['SCALPING'],
        )
        self.analysis = {
            'status': 'SCALP_LONG_APPROVED',
            'price': {'bid': 100, 'ask': 100.1, 'spread': 0.1},
            'regime': {'regime': 'TRENDING_BULLISH'},
            'orchestration': {
                'status': 'SCALP_LONG_APPROVED',
                'decision': {'action': 'SCALP_LONG_APPROVED', 'strategy': 'SCALPING'},
                'portfolio': {'risk_available': True, 'account_equity': 100000},
            },
            'scalping': {
                'candidates': [{
                    'direction': 'BUY',
                    'entryZone': {'lower': 99.8, 'upper': 100.2},
                    'decisionState': 'READY',
                    'score': 80,
                }],
            },
            'dayTrading': {'candidates': []},
        }

    def test_confirmation_is_required(self):
        snapshot = persist_orchestration_snapshot(account=self.account, analysis=self.analysis)

        with self.assertRaisesRegex(DemoExecutionError, 'confirmation'):
            execute_confirmed_demo_decision(
                account=self.account,
                snapshot=snapshot,
                confirmation=False,
                idempotency_key='demo-1',
            )

    def test_automatic_mode_cannot_be_used_by_confirmation_endpoint(self):
        self.account.live_execution_mode = 'AUTOMATIC'
        self.account.save(update_fields=['live_execution_mode'])
        snapshot = persist_orchestration_snapshot(account=self.account, analysis=self.analysis)

        with self.assertRaisesRegex(DemoExecutionError, 'does not allow confirmed'):
            execute_confirmed_demo_decision(
                account=self.account,
                snapshot=snapshot,
                confirmation=True,
                idempotency_key='demo-automatic',
            )

    @patch('backend.execution.demo_execution.send_live_order')
    @patch('backend.execution.demo_execution.assess_risk')
    def test_automatic_worker_submits_with_decision_idempotency(self, assess_risk_mock, send_live_order_mock):
        self.account.live_execution_mode = 'AUTOMATIC'
        self.account.save(update_fields=['live_execution_mode'])
        assess_risk_mock.return_value = {
            'approved': True,
            'status': 'PASS',
            'volume': 0.1,
            'riskPercent': 0.25,
            'riskAmount': 250,
        }
        send_live_order_mock.return_value = {'status': 'ACCEPTED', 'order': 789, 'deal': 987}
        snapshot = persist_orchestration_snapshot(account=self.account, analysis=self.analysis)

        result = execute_automatic_decision(account=self.account, snapshot=snapshot)

        self.assertEqual(result['status'], 'ACCEPTED')
        send_live_order_mock.assert_called_once()
        self.assertEqual(send_live_order_mock.call_args.kwargs['required_mode'], 'AUTOMATIC')
        self.assertEqual(send_live_order_mock.call_args.kwargs['idempotency_key'], f'auto-{snapshot.decision_id}')

    def test_stale_decision_is_rejected(self):
        snapshot = persist_orchestration_snapshot(account=self.account, analysis=self.analysis)
        snapshot.timestamp = timezone.now() - timedelta(seconds=61)
        snapshot.save(update_fields=['timestamp'])

        with self.assertRaisesRegex(DemoExecutionError, 'too old'):
            execute_confirmed_demo_decision(
                account=self.account,
                snapshot=snapshot,
                confirmation=True,
                idempotency_key='demo-stale',
            )

    @patch('backend.execution.demo_execution.send_live_order')
    @patch('backend.execution.demo_execution.assess_risk')
    def test_daily_order_limit_is_enforced(self, assess_risk_mock, send_live_order_mock):
        self.account.max_live_orders_per_day = 1
        self.account.save(update_fields=['max_live_orders_per_day'])
        LiveExecutionAttempt.objects.create(
            account=self.account,
            decision_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            idempotency_key='existing-order',
            strategy='SCALPING',
            status='ACCEPTED',
            setup={'riskAmount': 1},
        )
        assess_risk_mock.return_value = {
            'approved': True,
            'status': 'PASS',
            'volume': 0.1,
            'riskPercent': 0.25,
            'riskAmount': 250,
        }
        snapshot = persist_orchestration_snapshot(account=self.account, analysis=self.analysis)

        with self.assertRaisesRegex(DemoExecutionError, 'daily live-order limit'):
            execute_confirmed_demo_decision(
                account=self.account,
                snapshot=snapshot,
                confirmation=True,
                idempotency_key='demo-limit',
            )
        send_live_order_mock.assert_not_called()

    @patch('backend.execution.demo_execution.send_live_order')
    @patch('backend.execution.demo_execution.assess_risk')
    def test_confirmed_demo_decision_is_submitted_once(self, assess_risk_mock, send_live_order_mock):
        assess_risk_mock.return_value = {
            'approved': True,
            'status': 'PASS',
            'volume': 0.1,
            'riskPercent': 0.25,
            'riskAmount': 250,
        }
        send_live_order_mock.return_value = {
            'status': 'ACCEPTED',
            'order': 123,
            'deal': 456,
        }
        snapshot = persist_orchestration_snapshot(account=self.account, analysis=self.analysis)

        first = execute_confirmed_demo_decision(
            account=self.account,
            snapshot=snapshot,
            confirmation=True,
            idempotency_key='demo-1',
        )
        second = execute_confirmed_demo_decision(
            account=self.account,
            snapshot=snapshot,
            confirmation=True,
            idempotency_key='demo-1',
        )

        self.assertEqual(first['status'], 'ACCEPTED')
        self.assertTrue(second['duplicate'])
        self.assertEqual(LiveExecutionAttempt.objects.count(), 1)
        attempt = LiveExecutionAttempt.objects.get()
        self.assertIsNotNone(attempt.completed_at)
        self.assertEqual(attempt.request_payload['symbol'], 'XAUUSD.Z')
        self.assertIsNotNone(attempt.intent_id)
        self.assertEqual(
            list(ExecutionLifecycleEvent.objects.filter(decision_id=snapshot.decision_id).values_list('event_type', flat=True)),
            ['ORDER_ACCEPTED', 'EXECUTION_SUBMITTING', 'ORCHESTRATION_DECISION_CREATED'],
        )
        send_live_order_mock.assert_called_once()
