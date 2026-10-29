import tempfile
from pathlib import Path
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from backend.accounts.models import Account
from backend.execution.trading_audit import record_orchestration_candidates


class StrategyReportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='report-user@example.com', password='Strong-password-123')
        self.other_user = User.objects.create_user(username='other-report-user@example.com', password='Strong-password-123')
        self.account = Account.objects.create(
            user=self.user,
            enabled=True,
            canonical_asset='XAUUSD',
            broker_symbol='XAUUSD.Z',
        )
        self.other_account = Account.objects.create(
            user=self.other_user,
            enabled=True,
            canonical_asset='EURUSD',
            broker_symbol='EURUSD.Z',
        )

    def _record(self, account, decision_id: str, symbol: str):
        record_orchestration_candidates(
            account=account,
            analysis={
                'orchestration': {'decision': {'action': 'OBSERVE', 'reason': 'No setup passed.'}},
                'scalping': {'candidates': [{
                    'candidateId': f'{decision_id}-candidate',
                    'direction': 'BUY',
                    'decisionState': 'OBSERVE',
                    'score': 55,
                    'reasonCodes': ['SETUP_SEQUENCE_INCOMPLETE'],
                }]},
                'dayTrading': {'candidates': []},
            },
            decision_id=decision_id,
            timestamp=timezone.now(),
        )

    def test_report_view_is_account_scoped_and_pdf_download_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            with override_settings(TRADING_AUDIT_DIR=Path(directory)):
                self._record(self.account, 'owned-decision', self.account.broker_symbol)
                self._record(self.other_account, 'other-decision', self.other_account.broker_symbol)
                self.client.force_login(self.user)

                report = self.client.get('/api/strategies/reports/scalping')
                self.assertEqual(report.status_code, 200)
                payload = report.json()
                self.assertEqual(len(payload['rows']), 1)
                self.assertEqual(payload['rows'][0]['decision_id'], 'owned-decision')
                self.assertEqual(payload['rows'][0]['executed'], 'NO')

                pdf = self.client.get('/api/strategies/reports/scalping/pdf')
                self.assertEqual(pdf.status_code, 200)
                self.assertEqual(pdf['Content-Type'], 'application/pdf')
                self.assertTrue(pdf.content.startswith(b'%PDF-1.4'))

    def test_invalid_report_date_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/strategies/reports/day-trading?date=not-a-date')
        self.assertEqual(response.status_code, 400)
