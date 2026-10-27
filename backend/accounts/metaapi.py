import json
import re
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


PROVISIONING_API = 'https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai'
REQUEST_TIMEOUT_SECONDS = 15


class MetaApiHandshakeError(ValueError):
    pass


def _get_json(url, token):
    request = Request(
        url,
        headers={'Accept': 'application/json', 'auth-token': token},
        method='GET',
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as error:
        raise MetaApiHandshakeError(
            f'MetaAPI rejected the request (HTTP {error.code}). Check the API token, account ID, and account deployment.'
        ) from error
    except (URLError, TimeoutError) as error:
        raise MetaApiHandshakeError('MetaAPI could not be reached. Check the connection and try again.') from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MetaApiHandshakeError('MetaAPI returned an invalid response.') from error


def _required_decimal(value, name):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise MetaApiHandshakeError(f'MetaAPI did not return a valid {name}.') from error
    if not result.is_finite():
        raise MetaApiHandshakeError(f'MetaAPI did not return a valid {name}.')
    return result


def _asset_discovery(symbols):
    canonical_asset = 'XAUUSD'
    candidates = []
    for symbol in symbols:
        name = str(symbol.get('name', '') if isinstance(symbol, dict) else symbol).strip()
        if not name:
            continue
        token = re.sub(r'[^A-Z0-9]', '', name.upper())
        if token == canonical_asset:
            confidence = 1.0
        elif token.startswith(canonical_asset):
            confidence = 0.9
        elif canonical_asset in token:
            confidence = 0.8
        elif 'GOLD' in token:
            confidence = 0.45
        else:
            continue
        candidates.append({
            'name': name,
            'description': str(symbol.get('description', '') if isinstance(symbol, dict) else ''),
            'visible': True,
            'selectable': True,
            'tradeMode': None,
            'confidence': confidence,
        })
    executable = [candidate for candidate in candidates if candidate['confidence'] >= 0.7]
    selected = max(executable, key=lambda candidate: candidate['confidence'], default=None)
    return {
        'canonicalAsset': canonical_asset,
        'brokerSymbol': selected['name'] if selected else None,
        'symbols': candidates,
        'assetMatches': [candidate['name'] for candidate in candidates],
        'marketData': 'HEALTHY' if symbols else 'UNAVAILABLE',
    }


def verify_metaapi_handshake(account_id, token):
    account_id = str(account_id or '').strip()
    token = str(token or '')
    if not account_id or not token:
        raise MetaApiHandshakeError('MetaAPI account ID and API token are required.')

    encoded_id = quote(account_id, safe='')
    profile = _get_json(f'{PROVISIONING_API}/users/current/accounts/{encoded_id}', token)
    if not isinstance(profile, dict):
        raise MetaApiHandshakeError('MetaAPI did not return account details.')

    region = str(profile.get('region', '')).strip()
    if not re.fullmatch(r'[A-Za-z0-9-]+', region):
        raise MetaApiHandshakeError('MetaAPI account details do not include a valid region.')
    state = str(profile.get('state', '')).upper()
    if state and state != 'DEPLOYED':
        raise MetaApiHandshakeError('Deploy the MetaAPI account and wait until it is connected before onboarding.')

    client_api = f'https://mt-client-api-v1.{region}.agiliumtrade.ai'
    account_url = f'{client_api}/users/current/accounts/{encoded_id}'
    information = _get_json(f'{account_url}/account-information', token)
    positions = _get_json(f'{account_url}/positions', token)
    symbols = _get_json(f'{account_url}/symbols', token)
    if not isinstance(information, dict):
        raise MetaApiHandshakeError('MetaAPI did not return account information.')
    if not isinstance(positions, list):
        raise MetaApiHandshakeError('MetaAPI did not return account positions.')
    if not isinstance(symbols, list):
        raise MetaApiHandshakeError('MetaAPI did not return the account symbol list.')

    balance = _required_decimal(information.get('balance'), 'account balance')
    equity = _required_decimal(information.get('equity', balance), 'account equity')
    leverage = _required_decimal(information.get('leverage'), 'account leverage')
    if balance < 0 or equity < 0 or leverage <= 0 or leverage != leverage.to_integral_value():
        raise MetaApiHandshakeError('MetaAPI account balance, equity, or leverage is outside the supported range.')

    platform = str(profile.get('platform', information.get('platform', ''))).upper()
    if platform not in {'MT4', 'MT5'}:
        raise MetaApiHandshakeError('MetaAPI returned an unsupported trading platform.')

    market_discovery = _asset_discovery(symbols)
    return {
        'account_id': str(profile.get('login', information.get('login', account_id))),
        'external_account_id': account_id,
        'platform': platform,
        'broker': str(profile.get('broker', information.get('broker', 'MetaAPI'))),
        'server': str(profile.get('server', information.get('server', region))),
        'balance': str(balance),
        'equity': str(equity),
        'leverage': int(leverage),
        'currency': str(information.get('currency', information.get('currencyCode', 'USD')))[:3],
        'account_mode': str(information.get('marginMode', information.get('accountMode', 'UNKNOWN'))),
        'trade_allowed': bool(information.get('tradeAllowed', False)),
        'market_discovery': market_discovery,
        'existing_positions': len(positions),
    }
