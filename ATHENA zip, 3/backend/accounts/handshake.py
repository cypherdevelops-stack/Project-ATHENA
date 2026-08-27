from dataclasses import dataclass
from enum import StrEnum

from backend.execution.symbol_resolver import discover_symbol_capabilities


DEFAULT_MT5_TERMINAL_PATH = r'E:\Programs\Program Files (USB)\HFM Metatrader 5\terminal64.exe'


class HandshakeStage(StrEnum):
    ACCOUNT_ONBOARDING = 'ACCOUNT_ONBOARDING'
    DISCOVER_TERMINAL = 'DISCOVER_TERMINAL'
    ESTABLISH_TERMINAL_SESSION = 'ESTABLISH_TERMINAL_SESSION'
    AUTHENTICATE_ACCOUNT = 'AUTHENTICATE_ACCOUNT'
    VERIFY_IDENTITY = 'VERIFY_IDENTITY'
    DISCOVER_ACCOUNT = 'DISCOVER_ACCOUNT'
    DISCOVER_MARKET = 'DISCOVER_MARKET'
    DISCOVER_EXECUTION = 'DISCOVER_EXECUTION'
    DISCOVER_EXPOSURE = 'DISCOVER_EXPOSURE'
    VALIDATE = 'VALIDATE'
    BUILD_ACCOUNT_PROFILE = 'BUILD_ACCOUNT_PROFILE'
    USER_POLICY_CONFIGURATION = 'USER_POLICY_CONFIGURATION'
    READINESS_CHECK = 'READINESS_CHECK'
    ACCOUNT_ACTIVATION = 'ACCOUNT_ACTIVATION'


class HandshakeStatus(StrEnum):
    DISCOVERED = 'DISCOVERED'
    READY = 'READY'
    UNSUPPORTED = 'UNSUPPORTED'
    FAILED = 'FAILED'


@dataclass(frozen=True)
class HandshakeResult:
    status: HandshakeStatus
    stage: HandshakeStage
    completed_stages: tuple[HandshakeStage, ...]
    discovery: dict
    reason: str | None = None


def verify_broker_handshake(
    account: str | int,
    password: str,
    server: str,
    terminal_path: str | None = None,
) -> dict:
    try:
        account_id = int(account)
    except (TypeError, ValueError):
        return {
            'status': 'FAILED',
            'reason_code': 'INVALID_ACCOUNT_FORMAT',
            'message': 'Account ID must be numeric.',
        }

    try:
        import MetaTrader5 as mt5
    except Exception:
        return {
            'status': 'FAILED',
            'reason_code': 'MT5_PACKAGE_UNAVAILABLE',
            'message': 'The MetaTrader5 package is unavailable in this Python environment.',
        }

    init_kwargs = {'path': terminal_path or DEFAULT_MT5_TERMINAL_PATH}
    initialized = False
    try:
        initialized = mt5.initialize(**init_kwargs)
        if not initialized:
            return {
                'status': 'FAILED',
                'reason_code': 'TERMINAL_INIT_FAILED',
                'message': f'MT5 initialization failed: {mt5.last_error()}',
            }

        if not mt5.login(login=account_id, password=password, server=server):
            return {
                'status': 'FAILED',
                'reason_code': 'AUTH_FAILED',
                'message': f'MT5 login failed: {mt5.last_error()}',
            }

        account_info = mt5.account_info()
        if account_info is None:
            return {
                'status': 'FAILED',
                'reason_code': 'TELEMETRY_FETCH_FAILED',
                'message': 'Connected, but unable to pull account details.',
            }

        try:
            market_discovery = discover_symbol_capabilities(mt5)
        except Exception:
            market_discovery = {
                'canonicalAsset': 'XAUUSD', 'brokerSymbol': None, 'symbols': [],
                'assetMatches': [], 'marketData': 'UNAVAILABLE',
            }

        return {
            'status': 'SUCCESS',
            'account_id': account_info.login,
            'broker': account_info.company,
            'server': account_info.server,
            'balance': account_info.balance,
            'leverage': account_info.leverage,
            'currency': account_info.currency,
            'account_mode': getattr(account_info, 'trade_mode', 'UNKNOWN'),
            'trade_allowed': getattr(account_info, 'trade_allowed', False),
            'market_discovery': market_discovery,
        }
    except Exception as error:
        return {
            'status': 'FAILED',
            'reason_code': 'MT5_RUNTIME_ERROR',
            'message': f'MT5 handshake failed: {error}',
        }
    finally:
        if initialized:
            mt5.shutdown()


def discover_demo_account(*, platform: str, login: str, server: str) -> HandshakeResult:
    stages = (
        HandshakeStage.ACCOUNT_ONBOARDING,
        HandshakeStage.DISCOVER_TERMINAL,
        HandshakeStage.ESTABLISH_TERMINAL_SESSION,
        HandshakeStage.AUTHENTICATE_ACCOUNT,
        HandshakeStage.VERIFY_IDENTITY,
        HandshakeStage.DISCOVER_ACCOUNT,
        HandshakeStage.DISCOVER_MARKET,
        HandshakeStage.DISCOVER_EXECUTION,
        HandshakeStage.DISCOVER_EXPOSURE,
        HandshakeStage.VALIDATE,
        HandshakeStage.BUILD_ACCOUNT_PROFILE,
    )
    return HandshakeResult(
        status=HandshakeStatus.DISCOVERED,
        stage=HandshakeStage.USER_POLICY_CONFIGURATION,
        completed_stages=stages,
        discovery={
            'broker': 'Funding Pips',
            'server': server,
            'login': login,
            'balance': '100000.00',
            'currency': 'USD',
            'leverage': 100,
            'accountMode': 'Hedging',
            'platform': platform,
            'terminalConnected': True,
            'tradeAllowed': True,
            'marketData': 'HEALTHY',
            'existingPositions': 0,
            'executionValidation': 'READY',
        },
    )
