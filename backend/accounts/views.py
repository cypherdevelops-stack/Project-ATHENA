import json
import logging
from json import JSONDecodeError

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from .guardian import guardian_payload
from .credentials import encrypt_password
from .monitor import normalize_terminal_path
from .monitor import terminal_process_running
from backend.execution.paper_engine import PaperTradeError, build_paper_trade
from .handshake import discover_demo_account, verify_broker_handshake
from .metaapi import MetaApiHandshakeError, verify_metaapi_handshake
from .models import Account, AccountInstrumentCapability

logger = logging.getLogger(__name__)


def _account_for(request):
    account, _ = Account.objects.get_or_create(user=request.user)
    return account


def _capability_payload(capability):
    def scalar(value):
        return str(value) if hasattr(value, 'as_tuple') else value

    return {
        'canonicalAsset': capability['canonical_asset'],
        'brokerSymbol': capability['broker_symbol'],
        'symbolVisible': capability['symbol_visible'],
        'symbolSelected': capability['symbol_selected'],
        'tradeMode': capability['trade_mode'],
        'executionMode': capability['execution_mode'],
        'fillingModes': capability['filling_modes'],
        'orderModes': capability['order_modes'],
        'digits': capability['digits'],
        'point': scalar(capability['point']),
        'tickSize': scalar(capability['tick_size']),
        'volumeMin': scalar(capability['volume_min']),
        'volumeMax': scalar(capability['volume_max']),
        'volumeStep': scalar(capability['volume_step']),
        'stopsLevel': capability['stops_level'],
        'freezeLevel': capability['freeze_level'],
        'contractSize': scalar(capability['contract_size']),
        'lastDiscoveredAt': capability['last_discovered_at'].isoformat(),
    }


def _account_payload(account):
    capabilities = [_capability_payload(item) for item in account.instrument_capabilities.values()]
    return {
        'id': account.pk,
        'displayName': account.display_name,
        'platform': account.platform,
        'connectionMethod': account.connection_method,
        'login': account.login,
        'broker': account.broker,
        'server': account.server,
        'terminalPath': account.terminal_path,
        'balance': str(account.balance),
        'equity': str(account.equity),
        'accountMode': account.account_mode,
        'tradeAllowed': account.trade_allowed,
        'terminalConnected': account.terminal_connected,
        'lastHandshakeAt': account.last_handshake_at.isoformat() if account.last_handshake_at else None,
        'handshakeStatus': account.handshake_status,
        'instrumentCapabilities': capabilities,
        'accountType': account.account_type,
        'baseCurrency': account.base_currency,
        'leverage': account.leverage,
        'enabled': account.enabled,
        'isDefault': account.is_default,
        'allowedInstruments': account.allowed_instruments,
        'canonicalAsset': account.canonical_asset,
        'brokerSymbol': account.broker_symbol,
        'marketDiscovery': account.market_discovery,
        'riskPerTrade': str(account.risk_per_trade),
        'maxDailyDrawdown': str(account.max_daily_drawdown),
        'athenaSafetyDrawdown': str(account.athena_safety_drawdown),
        'maxOverallDrawdown': str(account.max_overall_drawdown),
        'maxConcurrentPositions': account.max_concurrent_positions,
        'liveExecutionEnabled': account.live_execution_enabled,
        'liveExecutionMode': account.live_execution_mode,
        'allowedStrategies': account.allowed_strategies,
        'maxLiveOrdersPerDay': account.max_live_orders_per_day,
        'maxLiveRiskPerDay': str(account.max_live_risk_per_day),
        'maxOrderValue': str(account.max_order_value),
        'requireFreshDecisionSeconds': account.require_fresh_decision_seconds,
        'reconciliationSafe': account.reconciliation_safe,
        'lastReconciliationAt': account.last_reconciliation_at.isoformat() if account.last_reconciliation_at else None,
        'guardian': guardian_payload(account),
    }


@login_required
@require_GET
def account_view(request):
    return JsonResponse(_account_payload(_account_for(request)))


@login_required
@require_GET
def accounts_view(request):
    return JsonResponse({'accounts': [_account_payload(account) for account in Account.objects.filter(user=request.user)]})


@login_required
@require_http_methods(['POST'])
def set_default_account_view(request):
    try:
        body = json.loads(request.body or '{}')
    except JSONDecodeError:
        return JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)
    account = Account.objects.filter(pk=body.get('accountId'), user=request.user).first()
    if account is None:
        return JsonResponse({'detail': 'Account was not found.'}, status=404)
    Account.objects.filter(user=request.user).update(is_default=False)
    Account.objects.filter(pk=account.pk).update(is_default=True)
    account.refresh_from_db()
    return JsonResponse(_account_payload(account))


@login_required
@require_GET
def mt5_health_view(request):
    accounts = Account.objects.filter(user=request.user)
    if not terminal_process_running():
        accounts.filter(enabled=True, terminal_connected=True).update(
            terminal_connected=False,
            trade_allowed=False,
            handshake_status='RECONNECTING',
        )
        accounts = Account.objects.filter(user=request.user)
    return JsonResponse({
        'accounts': [
            {
                'id': account.pk,
                'name': account.display_name,
                'server': account.server,
                'terminalConnected': account.terminal_connected,
                'tradeAllowed': account.trade_allowed,
                'balance': str(account.balance),
                'equity': str(account.equity),
                'handshakeStatus': account.handshake_status or 'NOT_CHECKED',
                'lastHandshakeAt': account.last_handshake_at.isoformat() if account.last_handshake_at else None,
            }
            for account in accounts
        ],
    })


@login_required
@require_http_methods(['POST'])
def create_account_view(request):
    try:
        body = json.loads(request.body or '{}')
    except JSONDecodeError:
        return JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)

    if not isinstance(body, dict):
        return JsonResponse({'detail': 'Request body must be a JSON object.'}, status=400)

    display_name = str(body.get('accountNickname', body.get('displayName', ''))).strip()
    platform = str(body.get('platform', 'MT5')).strip()
    connection_method = str(body.get('connectionMethod', 'BROKER')).strip().upper()
    login = str(body.get('login', '')).strip()
    server = str(body.get('server', '')).strip()
    password = body.get('password', '')
    if not display_name or not isinstance(password, str) or not password:
        return JsonResponse({'detail': 'Account nickname and connection credentials are required.'}, status=400)
    if connection_method == 'METAAPI':
        external_account_id = str(body.get('apiAccountId', body.get('externalAccountId', ''))).strip()
        try:
            verified = verify_metaapi_handshake(external_account_id, password)
        except MetaApiHandshakeError as error:
            return JsonResponse({'detail': str(error)}, status=422)
        platform = verified['platform']
        login = verified['account_id']
        server = verified['server']
        broker = verified['broker']
    elif connection_method == 'BROKER':
        if not platform or not login or not server:
            return JsonResponse({'detail': 'Platform, login, and server are required for broker login.'}, status=400)
        if platform not in {'MT4', 'MT5', 'CTRADER', 'TRADINGVIEW'}:
            return JsonResponse({'detail': 'Select a supported trading platform.'}, status=400)
        external_account_id = ''
        verified = {}
        broker = platform
    else:
        return JsonResponse({'detail': 'Select a supported connection method.'}, status=400)

    discovery = body.get('marketDiscovery', {}) if isinstance(body.get('marketDiscovery', {}), dict) else {}
    if connection_method == 'METAAPI':
        discovery = verified['market_discovery']
    allowed_instruments = body.get('allowedInstruments')
    if not isinstance(allowed_instruments, list):
        canonical_asset = str(body.get('canonicalAsset', '')).strip()
        allowed_instruments = [canonical_asset] if canonical_asset else []
    if connection_method == 'METAAPI' and verified['market_discovery']['canonicalAsset']:
        canonical_asset = verified['market_discovery']['canonicalAsset']
        allowed_instruments = [verified['market_discovery']['brokerSymbol']] if verified['market_discovery']['brokerSymbol'] else []
    else:
        canonical_asset = str(body.get('canonicalAsset', '')).strip()
    account = Account.objects.create(
        user=request.user,
        display_name=display_name,
        platform=platform,
        connection_method=connection_method,
        external_account_id=external_account_id,
        login=login,
        broker=broker,
        server=server,
        terminal_path=normalize_terminal_path(body.get('terminalPath', '')),
        password_encrypted=encrypt_password(password),
        canonical_asset=canonical_asset,
        broker_symbol=verified['market_discovery']['brokerSymbol'] if connection_method == 'METAAPI' else str(body.get('brokerSymbol', '')).strip(),
        market_discovery=discovery,
        allowed_instruments=allowed_instruments,
        balance=verified.get('balance', body.get('balance', 0)) or 0,
        equity=verified.get('equity', body.get('equity', 0)) or 0,
        leverage=verified.get('leverage', body.get('leverage', 100)),
        base_currency=str(verified.get('currency', body.get('currency', 'USD'))).strip()[:3] or 'USD',
        account_mode=str(verified.get('account_mode', body.get('accountMode', ''))).strip(),
        trade_allowed=verified.get('trade_allowed', bool(body.get('tradeAllowed', False))),
        terminal_connected=connection_method == 'METAAPI' or bool(body.get('terminalConnected', False)),
        last_handshake_at=timezone.now() if discovery else None,
        handshake_status='SUCCESS' if discovery else '',
    )
    if not Account.objects.filter(user=request.user, is_default=True).exclude(pk=account.pk).exists():
        account.is_default = True
        account.save(update_fields=['is_default'])
    _persist_capabilities(account, discovery)
    return JsonResponse(_account_payload(account), status=201)


def _persist_capabilities(account, discovery):
    for capability in discovery.get('symbols', []):
        symbol = str(capability.get('name', '')).strip()
        if not symbol:
            continue
        AccountInstrumentCapability.objects.update_or_create(
            account=account,
            canonical_asset=discovery.get('canonicalAsset', ''),
            broker_symbol=symbol,
            defaults={
                'symbol_visible': bool(capability.get('visible', False)),
                'symbol_selected': bool(capability.get('selectable', False)),
                'trade_mode': capability.get('tradeMode'),
                'execution_mode': capability.get('executionMode'),
                'filling_modes': capability.get('fillingModes', []),
                'order_modes': capability.get('orderModes', []),
                'digits': capability.get('digits'),
                'point': capability.get('point'),
                'tick_size': capability.get('tickSize'),
                'volume_min': capability.get('volumeMin'),
                'volume_max': capability.get('volumeMax'),
                'volume_step': capability.get('volumeStep'),
                'stops_level': capability.get('stopsLevel'),
                'freeze_level': capability.get('freezeLevel'),
                'contract_size': capability.get('contractSize'),
            },
        )


@login_required
@require_http_methods(['POST'])
def discover_account_view(request):
    try:
        body = json.loads(request.body or '{}')
    except JSONDecodeError:
        return JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)

    connection_method = str(body.get('connectionMethod', 'BROKER')).strip().upper()
    if connection_method == 'METAAPI':
        account_id = str(body.get('apiAccountId', '')).strip()
        token = body.get('password', '')
        if not account_id or not isinstance(token, str) or not token:
            return JsonResponse({'detail': 'MetaAPI account ID and API token are required.'}, status=400)
        try:
            result = verify_metaapi_handshake(account_id, token)
        except MetaApiHandshakeError as error:
            return JsonResponse({'status': 'FAILED', 'reason': str(error)}, status=422)
        discovery = result['market_discovery']
        return JsonResponse({
            'status': 'SUCCESS',
            'stage': 'USER_POLICY_CONFIGURATION',
            'completedStages': [
                'ACCOUNT_ONBOARDING', 'AUTHENTICATE_ACCOUNT', 'VERIFY_IDENTITY',
                'DISCOVER_ACCOUNT', 'DISCOVER_MARKET', 'DISCOVER_EXECUTION',
                'DISCOVER_EXPOSURE', 'VALIDATE', 'BUILD_ACCOUNT_PROFILE',
            ],
            'discovery': {
                'broker': result['broker'],
                'server': result['server'],
                'login': result['account_id'],
                'balance': result['balance'],
                'equity': result['equity'],
                'currency': result['currency'],
                'leverage': result['leverage'],
                'accountMode': result['account_mode'],
                'platform': result['platform'],
                'terminalConnected': True,
                'tradeAllowed': result['trade_allowed'],
                'marketData': discovery['marketData'],
                'canonicalAsset': discovery['canonicalAsset'],
                'brokerSymbol': discovery['brokerSymbol'],
                'marketDiscovery': discovery,
                'existingPositions': result['existing_positions'],
                'executionValidation': 'READY',
            },
        })

    platform = str(body.get('platform', '')).strip()
    login = str(body.get('login', '')).strip()
    server = str(body.get('server', '')).strip()
    password = body.get('password', '')
    if not platform or not login or not server or not isinstance(password, str) or not password:
        return JsonResponse({'detail': 'Platform, login, password, and server are required.'}, status=400)

    return _handshake_response(body, platform=platform, login=login, password=password, server=server)


def _handshake_response(body, *, platform, login, password, server):
    if platform != 'MT5':
        return JsonResponse({'status': 'UNSUPPORTED', 'reason': 'Only MT5 broker handshakes are supported.'}, status=422)
    if 'ive' in server.lower():
        return JsonResponse({'status': 'UNSUPPORTED', 'reason': 'Live accounts are not yet supported.'}, status=422)
    if 'demo' not in server.lower():
        return JsonResponse({'status': 'FAILED', 'reason': 'Demo server required for the current adapter.'}, status=422)

    result = verify_broker_handshake(
        account=login,
        password=password,
        server=server,
        terminal_path=body.get('terminalPath'),
    )
    if result['status'] != 'SUCCESS':
        logger.warning(
            'Account onboarding handshake failed: reason_code=%s message=%s platform=%s server=%s',
            result.get('reason_code', 'UNKNOWN'),
            result.get('message', 'No message returned.'),
            platform,
            server,
        )
        return JsonResponse(result, status=422)

    return JsonResponse({
        'status': 'SUCCESS',
        'stage': 'USER_POLICY_CONFIGURATION',
        'discovery': {
            'broker': result['broker'],
            'server': result['server'],
            'login': str(result['account_id']),
            'balance': result['balance'],
            'currency': result['currency'],
            'leverage': result['leverage'],
            'accountMode': result['account_mode'],
            'platform': platform,
            'terminalConnected': True,
            'tradeAllowed': result['trade_allowed'],
            'marketData': 'HEALTHY',
            'canonicalAsset': result['market_discovery']['canonicalAsset'],
            'brokerSymbol': result['market_discovery']['brokerSymbol'],
            'marketDiscovery': result['market_discovery'],
            'existingPositions': 0,
            'executionValidation': 'READY',
        },
    })


@login_required
@require_http_methods(['POST'])
def test_handshake_view(request):
    try:
        body = json.loads(request.body or '{}')
    except JSONDecodeError:
        return JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)

    if not isinstance(body, dict):
        return JsonResponse({'detail': 'Request body must be a JSON object.'}, status=400)

    platform = str(body.get('platform', 'MT5')).strip()
    login = str(body.get('account_id', body.get('login', ''))).strip()
    server = str(body.get('server', '')).strip()
    password = body.get('password', '')
    if not login or not server or not isinstance(password, str) or not password:
        return JsonResponse({'detail': 'Account ID, password, and server are required.'}, status=400)

    return _handshake_response(body, platform=platform, login=login, password=password, server=server)


@login_required
@require_GET
def guardian_view(request):
    return JsonResponse(guardian_payload(_account_for(request)))


@login_required
@require_http_methods(['POST'])
def paper_trade_view(request):
    try:
        body = json.loads(request.body or '{}')
    except JSONDecodeError:
        return JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)
    account = Account.objects.filter(pk=body.get('accountId'), user=request.user).first()
    if account is None:
        return JsonResponse({'detail': 'Account was not found.'}, status=404)
    try:
        return JsonResponse(build_paper_trade(account))
    except PaperTradeError as error:
        return JsonResponse({'detail': str(error)}, status=422)


@login_required
@require_http_methods(['PATCH'])
def update_account_view(request):
    try:
        body = json.loads(request.body or '{}')
    except JSONDecodeError:
        return JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)

    if not isinstance(body, dict):
        return JsonResponse({'detail': 'Request body must be a JSON object.'}, status=400)

    account_id = body.get('accountId', body.get('id'))
    account = _account_for(request) if account_id in (None, '') else Account.objects.filter(pk=account_id, user=request.user).first()
    if account is None:
        return JsonResponse({'detail': 'Account was not found.'}, status=404)

    password = body.get('password')
    if password is not None:
        if not isinstance(password, str) or not password:
            return JsonResponse({'detail': 'A non-empty broker password is required.'}, status=400)
        account.password_encrypted = encrypt_password(password)
    if 'terminal_path' in body:
        account.terminal_path = normalize_terminal_path(body['terminal_path'])

    allowed_fields = {
        'display_name', 'broker', 'server', 'account_type', 'base_currency', 'leverage',
        'enabled', 'allowed_instruments', 'risk_per_trade', 'max_daily_drawdown',
        'athena_safety_drawdown', 'max_overall_drawdown', 'max_concurrent_positions',
        'emergency_stop', 'canonical_asset', 'broker_symbol', 'market_discovery',
        'live_execution_enabled', 'live_execution_mode', 'allowed_strategies',
        'max_live_orders_per_day', 'max_live_risk_per_day', 'max_order_value',
        'require_fresh_decision_seconds',
    }
    for field, value in body.items():
        if field in allowed_fields:
            setattr(account, field, value)
    account.save()
    account.refresh_from_db()
    return JsonResponse(_account_payload(account))


@login_required
@require_http_methods(['DELETE'])
def delete_account_view(request):
    try:
        body = json.loads(request.body or '{}')
    except JSONDecodeError:
        return JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)

    if not isinstance(body, dict) or body.get('id') in (None, ''):
        return JsonResponse({'detail': 'Account ID is required.'}, status=400)

    account = Account.objects.filter(pk=body['id'], user=request.user).first()
    if account is None:
        return JsonResponse({'detail': 'Account was not found.'}, status=404)

    account.delete()
    return JsonResponse({}, status=204)
