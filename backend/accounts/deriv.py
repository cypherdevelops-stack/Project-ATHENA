import json
import os
from decimal import Decimal, InvalidOperation

import websocket


DERIV_WEBSOCKET_URL = 'wss://ws.derivws.com/websockets/v3'
DERIV_APP_ID = os.environ.get('DERIV_APP_ID', '1089').strip()
REQUEST_TIMEOUT_SECONDS = 10


class DerivHandshakeError(ValueError):
    pass


def verify_deriv_handshake(token):
    token = str(token or '').strip()
    if not token:
        raise DerivHandshakeError('A Deriv API token is required.')
    if not DERIV_APP_ID.isdigit():
        raise DerivHandshakeError('The Deriv API app ID is not configured correctly.')

    connection = None
    try:
        connection = websocket.create_connection(
            f'{DERIV_WEBSOCKET_URL}?app_id={DERIV_APP_ID}',
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        connection.send(json.dumps({'authorize': token}))
        response = json.loads(connection.recv())
    except (websocket.WebSocketException, OSError, TimeoutError) as error:
        raise DerivHandshakeError('Deriv could not be reached. Check the connection and try again.') from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DerivHandshakeError('Deriv returned an invalid response.') from error
    finally:
        if connection is not None:
            connection.close()

    if not isinstance(response, dict):
        raise DerivHandshakeError('Deriv returned an invalid authorization response.')
    error = response.get('error')
    if isinstance(error, dict):
        message = str(error.get('message', 'The token was rejected.')).strip()
        raise DerivHandshakeError(f'Deriv rejected the token: {message}')

    authorization = response.get('authorize')
    if not isinstance(authorization, dict):
        raise DerivHandshakeError('Deriv did not return account authorization details.')
    account_id = str(authorization.get('loginid', '')).strip()
    if not account_id:
        raise DerivHandshakeError('Deriv did not return an account ID for this token.')

    currency = str(authorization.get('currency', 'USD')).strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        currency = 'USD'
    try:
        balance = Decimal(str(authorization.get('balance', 0)))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise DerivHandshakeError('Deriv returned an invalid account balance.') from error
    if not balance.is_finite():
        raise DerivHandshakeError('Deriv returned an invalid account balance.')

    market_discovery = {
        'canonicalAsset': '',
        'brokerSymbol': None,
        'symbols': [],
        'assetMatches': [],
        'marketData': 'UNAVAILABLE',
    }
    return {
        'account_id': account_id,
        'platform': 'DERIV',
        'broker': 'Deriv',
        'server': 'Deriv',
        'balance': str(balance),
        'equity': str(balance),
        'leverage': 1,
        'currency': currency,
        'account_mode': 'VIRTUAL' if authorization.get('is_virtual') else 'REAL',
        'trade_allowed': False,
        'market_discovery': market_discovery,
    }
