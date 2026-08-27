from datetime import datetime, timezone
from uuid import uuid4

from django.test import SimpleTestCase

from .contracts import (
    BrokerPositionSnapshot,
    CanonicalTradeSetup,
    ContractValidationError,
    OrchestrationDecision,
)


class ExecutionContractTests(SimpleTestCase):
    def test_current_observe_analysis_maps_to_canonical_decision(self):
        decision = OrchestrationDecision.from_analysis({
            'orchestration': {
                'status': 'OBSERVE',
                'reason': 'No ready candidates',
                'decision': {
                    'action': 'OBSERVE',
                    'reason': 'No ready candidates',
                    'reasonCodes': ['NO_READY_CANDIDATE'],
                },
            },
        })

        self.assertEqual(decision.action, 'OBSERVE')
        self.assertEqual(decision.reason_codes, ['NO_READY_CANDIDATE'])
        self.assertIsInstance(decision.decision_id, type(uuid4()))

    def test_invalid_decision_action_is_rejected(self):
        with self.assertRaises(ContractValidationError):
            OrchestrationDecision(action='OPEN_POSITION', reason='invalid')

    def test_trade_setup_rejects_non_positive_volume(self):
        with self.assertRaises(ContractValidationError):
            CanonicalTradeSetup(
                strategy='SCALPING',
                direction='BUY',
                symbol='XAUUSD.Z',
                entry=100,
                stop_loss=99,
                take_profit1=101,
                take_profit2=102,
                volume=0,
            )

    def test_broker_position_requires_timezone_aware_timestamp(self):
        with self.assertRaises(ContractValidationError):
            BrokerPositionSnapshot(
                account_id=1,
                symbol='XAUUSD.Z',
                ticket=10,
                direction='BUY',
                volume=0.1,
                price_open=100,
                observed_at=datetime.now(),
            )
