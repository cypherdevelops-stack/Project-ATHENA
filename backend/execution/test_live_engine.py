import os
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from .live_engine import LiveExecutionError, send_live_order


class LiveExecutionTests(SimpleTestCase):
    def account(self):
        account = SimpleNamespace(
            enabled=True, terminal_connected=True, trade_allowed=True,
            broker_symbol='XAUUSD.Z', terminal_path='', login='1', server='demo',
            password_encrypted='',
            guardian_state=lambda: 'NORMAL',
        )
        return account

    def setup(self):
        return {'state': 'RISK_APPROVED', 'direction': 'BUY', 'entry': 100, 'stopLoss': 99, 'takeProfit2': 102, 'volume': 0.1}

    def test_live_execution_is_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(LiveExecutionError, 'disabled'):
                send_live_order(account=self.account(), setup=self.setup(), idempotency_key='one')

    def test_live_execution_requires_idempotency_key_and_confirmation_is_owned_by_view(self):
        with patch.dict(os.environ, {'ATHENA_LIVE_EXECUTION_ENABLED': 'true'}):
            with self.assertRaisesRegex(LiveExecutionError, 'idempotency'):
                send_live_order(account=self.account(), setup=self.setup(), idempotency_key=None)

    def test_live_execution_rejects_non_approved_setup(self):
        with patch.dict(os.environ, {'ATHENA_LIVE_EXECUTION_ENABLED': 'true'}):
            with self.assertRaisesRegex(LiveExecutionError, 'risk-approved'):
                send_live_order(account=self.account(), setup={**self.setup(), 'state': 'OBSERVE'}, idempotency_key='one')
