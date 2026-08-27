from __future__ import annotations

import re


FILLING_FLAGS = (('FOK', 'SYMBOL_FILLING_FOK', 1), ('IOC', 'SYMBOL_FILLING_IOC', 2), ('BOC', 'SYMBOL_FILLING_BOC', 4))
FILLING_ORDER_TYPES = ('IOC', 'FOK', 'RETURN', 'BOC')


def _token(value: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', value.upper())


def resolve_filling_mode(mt5, symbol_info, preferred_modes=FILLING_ORDER_TYPES) -> dict:
    flags = int(getattr(symbol_info, 'filling_mode', 0) or 0)
    execution_mode = getattr(symbol_info, 'trade_exemode', None)
    market_execution = execution_mode == getattr(mt5, 'SYMBOL_TRADE_EXECUTION_MARKET', 2)
    permitted = [name for name, constant, flag in FILLING_FLAGS if flags & getattr(mt5, constant, flag)]
    if not market_execution:
        permitted.append('RETURN')
    permitted = [mode for mode in FILLING_ORDER_TYPES if mode in permitted]
    selected = next((mode for mode in preferred_modes if mode in permitted), None)
    values = {name: getattr(mt5, f'ORDER_FILLING_{name}', index) for index, name in enumerate(FILLING_ORDER_TYPES)}
    return {
        'permitted': permitted,
        'selected': selected,
        'selectedValue': values[selected] if selected else None,
    }


def _capability(mt5, symbol, info) -> dict:
    filling = resolve_filling_mode(mt5, info)
    tick_reader = getattr(mt5, 'symbol_info_tick', None)
    tick = tick_reader(getattr(info, 'name', getattr(symbol, 'name', ''))) if tick_reader else None
    return {
        'name': str(getattr(symbol, 'name', '')).strip(),
        'description': str(getattr(info, 'description', '') or getattr(symbol, 'description', '') or ''),
        'path': str(getattr(info, 'path', '') or ''),
        'visible': bool(getattr(info, 'visible', getattr(symbol, 'visible', False))),
        'selectable': bool(getattr(info, 'select', True)),
        'tradeMode': getattr(info, 'trade_mode', getattr(symbol, 'trade_mode', None)),
        'executionMode': getattr(info, 'trade_exemode', getattr(symbol, 'trade_exemode', None)),
        'fillingModes': filling['permitted'],
        'selectedFillingMode': filling['selected'],
        'selectedFillingModeValue': filling['selectedValue'],
        'orderModes': getattr(info, 'order_mode', None),
        'digits': getattr(info, 'digits', getattr(symbol, 'digits', None)),
        'point': getattr(info, 'point', None),
        'tickSize': getattr(info, 'trade_tick_size', None),
        'tickValue': getattr(info, 'trade_tick_value', None),
        'volumeMin': getattr(info, 'volume_min', getattr(symbol, 'volume_min', None)),
        'volumeMax': getattr(info, 'volume_max', getattr(symbol, 'volume_max', None)),
        'volumeStep': getattr(info, 'volume_step', getattr(symbol, 'volume_step', None)),
        'stopsLevel': getattr(info, 'trade_stops_level', getattr(symbol, 'trade_stops_level', None)),
        'freezeLevel': getattr(info, 'trade_freeze_level', getattr(symbol, 'trade_freeze_level', None)),
        'contractSize': getattr(info, 'trade_contract_size', None),
        'currencyBase': getattr(info, 'currency_base', None),
        'currencyProfit': getattr(info, 'currency_profit', None),
        'currencyMargin': getattr(info, 'currency_margin', None),
        'bid': getattr(tick, 'bid', None) if tick else None,
        'ask': getattr(tick, 'ask', None) if tick else None,
    }


def discover_symbol_capabilities(mt5, canonical_asset: str = 'XAUUSD') -> dict:
    terminal = mt5.terminal_info() if hasattr(mt5, 'terminal_info') else None
    filtered_symbols = mt5.symbols_get(f'*{canonical_asset}*') or ()
    symbols = list(filtered_symbols)
    if not symbols:
        symbols = list(mt5.symbols_get() or ())

    canonical_token = _token(canonical_asset)
    candidates = []
    for symbol in symbols:
        name = str(getattr(symbol, 'name', '')).strip()
        if not name:
            continue
        info = mt5.symbol_info(name) or symbol
        if hasattr(mt5, 'symbol_select') and not getattr(info, 'select', True):
            mt5.symbol_select(name, True)
            info = mt5.symbol_info(name) or info
        capability = _capability(mt5, symbol, info)
        symbol_token = _token(name)
        description = f"{capability['description']} {capability['path']}".upper()
        if symbol_token == canonical_token:
            confidence = 1.0
        elif symbol_token.startswith(canonical_token):
            confidence = 0.9
        elif canonical_token in symbol_token:
            confidence = 0.8
        elif 'GOLD' in description:
            confidence = 0.45
        else:
            continue
        capability['confidence'] = confidence
        candidates.append(capability)

    executable = [candidate for candidate in candidates if candidate['selectable'] and candidate['tradeMode'] not in (None, 0)]
    selected = max(executable, key=lambda candidate: (candidate['confidence'], candidate['visible']), default=None)
    if selected and selected['confidence'] < 0.7:
        selected = None

    return {
        'canonicalAsset': canonical_asset,
        'brokerSymbol': selected['name'] if selected else None,
        'symbols': candidates,
        'assetMatches': [candidate['name'] for candidate in candidates],
        'marketData': 'HEALTHY' if symbols else 'UNAVAILABLE',
        'terminalTradeAllowed': bool(getattr(terminal, 'trade_allowed', False)) if terminal else None,
    }
