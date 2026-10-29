import json
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from .deriv import DERIV_APP_ID, DERIV_WEBSOCKET_URL, DerivHandshakeError, verify_deriv_handshake


class DerivHandshakeTests(SimpleTestCase):
    @patch('backend.accounts.deriv.websocket.create_connection')
    def test_authorizes_token_and_returns_account_facts(self, create_connection):
        connection = Mock()
        connection.recv.return_value = json.dumps({
            'authorize': {
                'loginid': 'CR12345',
                'currency': 'EUR',
                'balance': '345.67',
                'is_virtual': 1,
            },
        })
        create_connection.return_value = connection

        result = verify_deriv_handshake('private-token')

        create_connection.assert_called_once_with(
            f'{DERIV_WEBSOCKET_URL}?app_id={DERIV_APP_ID}',
            timeout=10,
        )
        connection.send.assert_called_once_with(json.dumps({'authorize': 'private-token'}))
        connection.close.assert_called_once_with()
        self.assertEqual(result['account_id'], 'CR12345')
        self.assertEqual(result['currency'], 'EUR')
        self.assertEqual(result['balance'], '345.67')
        self.assertEqual(result['account_mode'], 'VIRTUAL')
        self.assertFalse(result['trade_allowed'])

    @patch('backend.accounts.deriv.websocket.create_connection')
    def test_rejected_token_returns_the_deriv_error(self, create_connection):
        connection = Mock()
        connection.recv.return_value = json.dumps({
            'error': {'message': 'Invalid token.', 'code': 'InvalidToken'},
        })
        create_connection.return_value = connection

        with self.assertRaisesMessage(DerivHandshakeError, 'Deriv rejected the token: Invalid token.'):
            verify_deriv_handshake('bad-token')

        connection.close.assert_called_once_with()

    @patch('backend.accounts.deriv.websocket.create_connection')
    def test_blank_token_is_rejected_without_connecting(self, create_connection):
        with self.assertRaisesMessage(DerivHandshakeError, 'A Deriv API token is required.'):
            verify_deriv_handshake(' ')

        create_connection.assert_not_called()
