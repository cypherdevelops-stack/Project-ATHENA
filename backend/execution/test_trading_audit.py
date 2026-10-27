import csv
import tempfile
from pathlib import Path
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from backend.execution.trading_audit import (
    record_execution_outcome,
    record_orchestration_candidates,
)


class TradingAuditTests(SimpleTestCase):
    def test_strategies_get_daily_csvs_and_execution_updates_match_decision(self):
        timestamp = timezone.now()
        with tempfile.TemporaryDirectory() as temporary_directory:
            with override_settings(TRADING_AUDIT_DIR=Path(temporary_directory)):
                decision_id = 'e565ad32-17f7-4e16-ad3b-d3073e968253'
                account = SimpleNamespace(
                    pk=7,
                    broker_symbol='XAUUSD.Z',
                    canonical_asset='XAUUSD',
                )
                analysis = {
                    'orchestration': {
                        'decision': {
                            'action': 'SCALP_LONG_APPROVED',
                            'strategy': 'SCALPING',
                            'reason': 'Scalping setup approved.',
                        },
                    },
                    'scalping': {
                        'candidates': [
                            {
                                'candidateId': 'scalp-1',
                                'direction': 'BUY',
                                'decisionState': 'READY',
                                'score': 82,
                                'entryZone': {'lower': 100, 'upper': 101},
                            },
                            {
                                'candidateId': 'scalp-2',
                                'direction': 'SELL',
                                'decisionState': 'OBSERVE',
                                'reasonCodes': ['HTF_BIAS_NOT_ALIGNED'],
                            },
                        ],
                    },
                    'dayTrading': {
                        'candidates': [
                            {
                                'candidateId': 'day-1',
                                'direction': 'BUY',
                                'decisionState': 'DEVELOPING',
                                'score': 76,
                            },
                        ],
                    },
                }

                record_orchestration_candidates(
                    account=account,
                    analysis=analysis,
                    decision_id=decision_id,
                    timestamp=timestamp,
                )
                record_execution_outcome(
                    strategy='SCALPING',
                    decision_id=decision_id,
                    executed=True,
                    execution_status='ACCEPTED',
                    reason='Broker accepted the order.',
                    timestamp=timestamp,
                )

                date = timezone.localtime(timestamp).date().isoformat()
                scalping_path = Path(temporary_directory) / f'scalping_{date}.csv'
                daytrading_path = Path(temporary_directory) / f'daytrading_{date}.csv'
                self.assertTrue(scalping_path.exists())
                self.assertTrue(daytrading_path.exists())
                with scalping_path.open(encoding='utf-8', newline='') as csv_file:
                    scalping_rows = list(csv.DictReader(csv_file))
                with daytrading_path.open(encoding='utf-8', newline='') as csv_file:
                    daytrading_rows = list(csv.DictReader(csv_file))

                self.assertEqual(len(scalping_rows), 2)
                self.assertEqual(len(daytrading_rows), 1)
                self.assertEqual(scalping_rows[0]['executed'], 'YES')
                self.assertEqual(scalping_rows[0]['execution_status'], 'ACCEPTED')
                self.assertEqual(scalping_rows[0]['reason'], 'Broker accepted the order.')
                self.assertEqual(scalping_rows[1]['executed'], 'NO')
                self.assertIn('HTF_BIAS_NOT_ALIGNED', scalping_rows[1]['reason'])
                self.assertEqual(daytrading_rows[0]['executed'], 'NO')
                self.assertEqual(daytrading_rows[0]['execution_status'], 'NOT_EXECUTED')
