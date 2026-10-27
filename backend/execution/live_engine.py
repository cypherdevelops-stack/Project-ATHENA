from __future__ import annotations

import os
from threading import RLock

from backend.accounts.credentials import decrypt_password
from backend.accounts.handshake import DEFAULT_MT5_TERMINAL_PATH
from backend.execution.execution_gateway import ExecutionGatewayError, validate_broker_setup
from backend.execution.automation_policy import AutomationPolicyError, enforce_automation_policy
from backend.execution.symbol_resolver import resolve_filling_mode


class LiveExecutionError(ValueError):
    pass


_order_lock = RLock()
_order_results: dict[str, dict] = {}


def _enabled() -> bool:
    return os.environ.get('ATHENA_LIVE_EXECUTION_ENABLED', '').lower() == 'true'


def _policy_allows(account) -> bool:
    return bool(getattr(account, 'live_execution_enabled', False))


def send_live_order(*, account, setup: dict, requested_price: float | None = None, max_slippage: float = 0.0, idempotency_key: str | None = None, mt5_module=None, required_mode: str = 'CONFIRMATION_REQUIRED') -> dict:
    if getattr(account, 'connection_method', 'BROKER') != 'BROKER':
        raise LiveExecutionError('This account connection is not supported by the MT5 live execution adapter.')
    if not _enabled():
        raise LiveExecutionError('Live execution is disabled by server policy.')
    if not idempotency_key:
        raise LiveExecutionError('An idempotency key is required for live execution.')
    with _order_lock:
        if idempotency_key in _order_results:
            return {**_order_results[idempotency_key], 'duplicate': True}
    if setup.get('state') != 'RISK_APPROVED' or setup.get('direction') not in {'BUY', 'SELL'}:
        raise LiveExecutionError('Only a risk-approved setup can be sent to MT5.')
    if not _policy_allows(account):
        raise LiveExecutionError('Live execution is disabled by server policy.')
    try:
        enforce_automation_policy(
            account=account,
            strategy=setup.get('strategy', 'SCALPING'),
            setup=setup,
            required_mode=required_mode,
        )
    except AutomationPolicyError as error:
        raise LiveExecutionError(str(error)) from error
    if account.guardian_state() != 'NORMAL' or not account.enabled or not account.terminal_connected or not account.trade_allowed or not getattr(account, 'reconciliation_safe', True):
        raise LiveExecutionError('Account safety, connection, or trading permission is not available.')
    if max_slippage < 0:
        raise LiveExecutionError('Maximum slippage cannot be negative.')

    if mt5_module is None:
        try:
            import MetaTrader5 as mt5_module
        except ImportError as error:
            raise LiveExecutionError(f'MetaTrader5 package import failed: {error}') from error
    initialized = bool(mt5_module.initialize(path=account.terminal_path or DEFAULT_MT5_TERMINAL_PATH))
    if not initialized:
        raise LiveExecutionError(f'MT5 initialization failed: {mt5_module.last_error()}')
    try:
        if not mt5_module.login(login=int(account.login), password=decrypt_password(account.password_encrypted), server=account.server):
            raise LiveExecutionError(f'MT5 login failed: {mt5_module.last_error()}')
        symbol_info = mt5_module.symbol_info(account.broker_symbol)
        if symbol_info is None:
            raise LiveExecutionError('Broker symbol information is unavailable.')
        filling = resolve_filling_mode(mt5_module, symbol_info)
        capability = next(
            (item for item in (account.market_discovery or {}).get('symbols', [])
             if item.get('name') == account.broker_symbol),
            {},
        )
        capability = {
            **capability,
            'visible': getattr(symbol_info, 'visible', capability.get('visible', True)),
            'selectable': getattr(symbol_info, 'select', capability.get('selectable', True)),
            'tradeMode': getattr(symbol_info, 'trade_mode', capability.get('tradeMode')),
            'executionMode': getattr(symbol_info, 'trade_exemode', capability.get('executionMode')),
            'orderModes': getattr(symbol_info, 'order_mode', capability.get('orderModes')),
            'marketOrderMode': getattr(mt5_module, 'SYMBOL_ORDER_MARKET', 1),
            'fillingModes': filling.get('permitted'),
            'digits': getattr(symbol_info, 'digits', capability.get('digits')),
            'point': getattr(symbol_info, 'point', capability.get('point')),
            'tickSize': getattr(symbol_info, 'trade_tick_size', capability.get('tickSize')),
            'volumeMin': getattr(symbol_info, 'volume_min', capability.get('volumeMin')),
            'volumeMax': getattr(symbol_info, 'volume_max', capability.get('volumeMax')),
            'volumeStep': getattr(symbol_info, 'volume_step', capability.get('volumeStep')),
            'stopsLevel': getattr(symbol_info, 'trade_stops_level', capability.get('stopsLevel')),
            'freezeLevel': getattr(symbol_info, 'trade_freeze_level', capability.get('freezeLevel')),
            'contractSize': getattr(symbol_info, 'trade_contract_size', capability.get('contractSize')),
            'selectedFillingMode': filling.get('selected'),
            'selectedFillingModeValue': filling.get('selectedValue'),
        }
        tick = mt5_module.symbol_info_tick(account.broker_symbol)
        market_price = float(getattr(tick, 'ask' if setup['direction'] == 'BUY' else 'bid', 0) or 0)
        if requested_price is not None and abs(market_price - requested_price) > max_slippage:
            raise LiveExecutionError('Market price moved beyond the permitted slippage.')
        try:
            setup = validate_broker_setup(setup=setup, capability=capability, market_price=market_price)
        except ExecutionGatewayError as error:
            raise LiveExecutionError(str(error)) from error
        order_type = mt5_module.ORDER_TYPE_BUY if setup['direction'] == 'BUY' else mt5_module.ORDER_TYPE_SELL
        request = {
            'action': mt5_module.TRADE_ACTION_DEAL,
            'symbol': account.broker_symbol,
            'volume': float(setup['volume']),
            'type': order_type,
            'price': market_price,
            'sl': float(setup['stopLoss']),
            'tp': float(setup['takeProfit2']),
            'deviation': int(max_slippage),
            'magic': 2707001,
            'comment': 'ATHENA_SCALP',
            'type_time': mt5_module.ORDER_TIME_GTC,
            'type_filling': capability['selectedFillingModeValue'],
        }
        result = mt5_module.order_send(request)
        if result is None:
            raise LiveExecutionError(f'MT5 order failed: {mt5_module.last_error()}')
        payload = {'status': 'ACCEPTED' if result.retcode == mt5_module.TRADE_RETCODE_DONE else 'REJECTED', 'retcode': result.retcode, 'order': getattr(result, 'order', None), 'deal': getattr(result, 'deal', None), 'symbol': account.broker_symbol, 'direction': setup['direction'], 'volume': setup['volume'], 'entry': market_price, 'stopLoss': setup['stopLoss'], 'takeProfit': setup['takeProfit2']}
        with _order_lock:
            _order_results[idempotency_key] = payload
        return payload
    finally:
        mt5_module.shutdown()
