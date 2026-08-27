from __future__ import annotations

from dataclasses import asdict, dataclass


GATE_STATUSES = frozenset({'PASS', 'BLOCK', 'WAIT', 'DEGRADED', 'NOT_APPLICABLE', 'UNKNOWN'})


@dataclass(frozen=True)
class GateResult:
    name: str
    status: str
    reason: str

    def __post_init__(self):
        if self.status not in GATE_STATUSES:
            raise ValueError(f'Unsupported gate status: {self.status!r}.')

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def news_gate(context: dict) -> GateResult:
    if context.get('news_locked', False):
        return GateResult('NEWS_GATE', 'BLOCK', context.get('news_reason', 'High-impact news lock is active.'))
    if context.get('news_provider_available') is False:
        return GateResult('NEWS_GATE', 'DEGRADED', context.get('news_reason', 'News provider is unavailable; trading is fail-closed.'))
    if context.get('news_state') in GATE_STATUSES - {'PASS', 'BLOCK'}:
        return GateResult('NEWS_GATE', context['news_state'], context.get('news_reason', 'News state is not yet trusted.'))
    return GateResult('NEWS_GATE', 'PASS', context.get('news_reason', 'No high-impact event lock is active.'))


def session_gate(context: dict) -> GateResult:
    if context.get('session_aligned', True) is False:
        return GateResult('SESSION_GATE', 'BLOCK', context.get('session_reason', 'The current trading session is outside the scalping window.'))
    return GateResult('SESSION_GATE', 'PASS', context.get('session_reason', 'The current session is enabled for scalping.'))


def spread_gate(context: dict) -> GateResult:
    spread = context.get('spread')
    maximum = context.get('max_spread')
    if context.get('spread_ok', True) is False or (spread is not None and maximum is not None and spread > maximum):
        detail = f'Spread {spread:.2f} > maximum allowed {maximum:.2f}.' if spread is not None and maximum is not None else 'Spread is above the configured maximum.'
        return GateResult('SPREAD_GATE', 'BLOCK', detail)
    return GateResult('SPREAD_GATE', 'PASS', context.get('spread_reason', 'Spread is within the configured limit.'))


def volatility_gate(context: dict) -> GateResult:
    if context.get('volatility_allowed', True) is False or context.get('volatility') == 'HIGH':
        return GateResult('VOLATILITY_GATE', 'BLOCK', context.get('volatility_reason', 'Current volatility is outside the scalping range.'))
    if context.get('volatility', 'UNKNOWN') == 'UNKNOWN':
        return GateResult('VOLATILITY_GATE', 'PASS', 'Volatility gate is awaiting a classified market context.')
    return GateResult('VOLATILITY_GATE', 'PASS', context.get('volatility_reason', 'Volatility is suitable for scalping.'))


def drawdown_gate(account, context: dict) -> GateResult:
    if context.get('drawdown_allowed', True) is False:
        return GateResult('DRAWDOWN_GATE', 'BLOCK', context.get('drawdown_reason', 'Account drawdown limits prohibit new scalps.'))
    if hasattr(account, 'guardian_state') and account.guardian_state() in {'HALT', 'ACCOUNT_LOCK', 'DAILY_LOCK'}:
        return GateResult('DRAWDOWN_GATE', 'BLOCK', f'Account guardian state is {account.guardian_state()}.')
    return GateResult('DRAWDOWN_GATE', 'PASS', 'Account drawdown is within configured limits.')


def correlation_gate(context: dict) -> GateResult:
    if context.get('correlation_allowed', True) is False:
        return GateResult('CORRELATION_GATE', 'BLOCK', context.get('correlation_reason', 'Correlated exposure limit has been reached.'))
    return GateResult('CORRELATION_GATE', 'PASS', context.get('correlation_reason', 'Correlated exposure is within limits.'))


def htf_bias_gate(*, direction: str, higher_structure: str, context: dict) -> GateResult:
    bias = context.get('htf_bias')
    if bias in {'BUY', 'SELL'}:
        expected = 'BUY' if direction == 'BULLISH' else 'SELL'
        if bias != expected:
            return GateResult('HTF_BIAS_GATE', 'BLOCK', f'HTF bias is {bias}; {expected} permission is required for this setup.')
        return GateResult('HTF_BIAS_GATE', 'PASS', f'HTF bias {bias} permits this setup.')
    if higher_structure not in {'BULLISH', 'BEARISH'}:
        return GateResult('HTF_BIAS_GATE', 'BLOCK', 'Higher-timeframe structure is undefined.')
    return GateResult('HTF_BIAS_GATE', 'PASS', f'Higher-timeframe structure {higher_structure} permits this setup.')


def execution_gate(account, context: dict) -> GateResult:
    if not account.enabled:
        return GateResult('EXECUTION_GATE', 'BLOCK', 'Trading account is disabled.')
    if not account.terminal_connected:
        return GateResult('EXECUTION_GATE', 'BLOCK', 'Trading terminal is not connected.')
    if not account.trade_allowed:
        return GateResult('EXECUTION_GATE', 'BLOCK', 'Broker has not permitted trading.')
    if context.get('execution_allowed', True) is False:
        return GateResult('EXECUTION_GATE', 'BLOCK', context.get('execution_reason', 'Execution conditions are unavailable.'))
    return GateResult('EXECUTION_GATE', 'PASS', 'Account and broker execution conditions are available.')


def detect_scalping_setup(*, direction: str, current_price: float | None = None, poi: dict | None = None, context: dict | None = None, higher_structure: str | None = None) -> dict:
    context = context or {}
    structure = higher_structure or context.get('higher_structure') or context.get('htf_structure') or context.get('m5_structure')
    direction_name = str(direction).upper()
    if direction_name not in {'BULLISH', 'BEARISH'}:
        raise ValueError(f'Unsupported setup direction: {direction!r}.')

    setup_keys = {
        'htf_bias', 'price_approaches_liquidity', 'sell_side_liquidity_swept', 'buy_side_liquidity_swept',
        'bullish_displacement', 'bearish_displacement', 'bullish_mss', 'bearish_mss',
        'fresh_bullish_poi', 'fresh_bearish_poi', 'price_returns_to_poi', 'entry_confirmation',
        'liquidity_sweep', 'displacement', 'mss_confirmed', 'fresh_poi', 'poi_retest',
    }
    if not context or not setup_keys.intersection(context):
        return {
            'direction': 'LONG' if direction_name == 'BULLISH' else 'SHORT',
            'setupName': 'BULLISH_RETRACE_BUY' if direction_name == 'BULLISH' else 'BEARISH_RETRACE_SELL',
            'active': False,
            'sequence': ['HTF_BIAS', 'LIQUIDITY_APPROACH', 'LIQUIDITY_SWEEP', 'DISPLACEMENT', 'MSS', 'POI', 'POI_RETEST', 'ENTRY'],
            'steps': [
                {'name': name, 'status': 'UNKNOWN', 'reason': 'No explicit setup evidence supplied; waiting for trusted market data.'}
                for name in ['HTF_BIAS', 'LIQUIDITY_APPROACH', 'LIQUIDITY_SWEEP', 'DISPLACEMENT', 'MSS', 'POI', 'POI_RETEST', 'ENTRY']
            ],
            'missing': ['HTF_BIAS', 'LIQUIDITY_APPROACH', 'LIQUIDITY_SWEEP', 'DISPLACEMENT', 'MSS', 'POI', 'POI_RETEST', 'ENTRY'],
        }

    expected_bias = 'BUY' if direction_name == 'BULLISH' else 'SELL'
    expected_structure = 'BULLISH' if direction_name == 'BULLISH' else 'BEARISH'
    lower, upper = None, None
    if poi:
        lower = float(poi.get('lowerBound', float('-inf')))
        upper = float(poi.get('upperBound', float('inf')))

    def _pass_if(condition: bool, name: str, message: str) -> dict:
        return {'name': name, 'status': 'PASS' if condition else 'BLOCK', 'reason': message if condition else f'{name} did not pass: {message}'}

    def _price_in_zone() -> bool:
        if current_price is None or lower is None or upper is None:
            return False
        return lower <= current_price <= upper

    def _approaching_zone() -> bool:
        if current_price is None or lower is None or upper is None:
            return bool(context.get('price_approaches_liquidity', False))
        band = max((upper - lower) * 0.25, 0.0001)
        return lower - band <= current_price <= upper + band

    sequence = [
        ('HTF_BIAS', 'htf_bias', lambda: context.get('htf_bias') == expected_bias or (structure == expected_structure and context.get('htf_bias') in {'BUY', 'SELL'})),
        ('LIQUIDITY_APPROACH', 'price_approaches_liquidity', lambda: bool(context.get('price_approaches_liquidity', _approaching_zone()))),
        ('LIQUIDITY_SWEEP', 'sell_side_liquidity_swept', lambda: bool(context.get('sell_side_liquidity_swept', context.get('liquidity_sweep', False)) if direction_name == 'BULLISH' else context.get('buy_side_liquidity_swept', context.get('liquidity_sweep', False)))),
        ('DISPLACEMENT', 'bullish_displacement', lambda: bool(context.get('bullish_displacement', context.get('displacement', False)) if direction_name == 'BULLISH' else context.get('bearish_displacement', context.get('displacement', False)))),
        ('MSS', 'bullish_mss', lambda: bool(context.get('bullish_mss', context.get('mss_confirmed', False)) if direction_name == 'BULLISH' else context.get('bearish_mss', context.get('mss_confirmed', False)))),
        ('POI', 'fresh_bullish_poi', lambda: bool(context.get('fresh_bullish_poi', context.get('fresh_poi', False)) if direction_name == 'BULLISH' else context.get('fresh_bearish_poi', context.get('fresh_poi', False)))),
        ('POI_RETEST', 'price_returns_to_poi', lambda: bool(context.get('price_returns_to_poi', _price_in_zone() or context.get('poi_retest', False)))),
        ('ENTRY', 'entry_confirmation', lambda: bool(context.get('entry_confirmation', False))),
    ]

    steps = []
    for name, key, condition in sequence:
        result = condition()
        if name == 'HTF_BIAS':
            reason = f'HTF bias {expected_bias} is required for a {direction_name.lower()} setup.'
        elif name == 'LIQUIDITY_APPROACH':
            reason = 'Price is approaching the liquidity pocket that the setup wants to react off.'
        elif name == 'LIQUIDITY_SWEEP':
            reason = 'The liquidity sweep has occurred on the correct side of the market.'
        elif name == 'DISPLACEMENT':
            reason = 'Displacement confirms the move away from the liquidity event.'
        elif name == 'MSS':
            reason = 'MSS confirms the trend continuation after the initial move.'
        elif name == 'POI':
            reason = 'A fresh POI is active for the setup.'
        elif name == 'POI_RETEST':
            reason = 'Price has returned to the POI and is reloading the structure.'
        else:
            reason = 'Entry confirmation is present and aligned with the setup.'
        steps.append(_pass_if(result, name, reason))

    active = all(step['status'] == 'PASS' for step in steps)
    return {
        'direction': 'LONG' if direction_name == 'BULLISH' else 'SHORT',
        'setupName': 'BULLISH_RETRACE_BUY' if direction_name == 'BULLISH' else 'BEARISH_RETRACE_SELL',
        'active': active,
        'sequence': [step['name'] for step in steps],
        'steps': steps,
        'missing': [step['name'] for step in steps if step['status'] != 'PASS'],
    }


def evaluate_gates(*, account, direction: str, higher_structure: str, context: dict | None = None) -> list[GateResult]:
    context = context or {}
    return [
        news_gate(context),
        session_gate(context),
        spread_gate(context),
        volatility_gate(context),
        drawdown_gate(account, context),
        correlation_gate(context),
        htf_bias_gate(direction=direction, higher_structure=higher_structure, context=context),
        execution_gate(account, context),
    ]
