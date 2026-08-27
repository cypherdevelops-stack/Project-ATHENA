from __future__ import annotations

from decimal import Decimal, ROUND_DOWN


class RiskEngineError(ValueError):
    pass


def _step_down(value: float, step: float) -> float:
    if step <= 0:
        return value
    return float((Decimal(str(value)) / Decimal(str(step))).to_integral_value(rounding=ROUND_DOWN) * Decimal(str(step)))


def assess_risk(*, account, direction: str, entry: float, stop_loss: float, take_profit: float) -> dict:
    """Calculate a policy-bound trade size and approve only safe paper candidates."""
    if direction not in {'BUY', 'SELL'}:
        return {'approved': False, 'status': 'UNKNOWN', 'reason': 'Trade direction is unavailable.'}
    if entry <= 0 or stop_loss <= 0 or take_profit <= 0:
        return {'approved': False, 'status': 'BLOCK', 'reason': 'Entry, stop loss, and take profit must be positive.'}

    stop_distance = abs(entry - stop_loss)
    reward_distance = abs(take_profit - entry)
    if stop_distance == 0:
        return {'approved': False, 'status': 'BLOCK', 'reason': 'Stop loss must be different from entry.'}

    guardian_state = account.guardian_state() if hasattr(account, 'guardian_state') else 'NORMAL'
    if guardian_state != 'NORMAL':
        return {'approved': False, 'status': 'BLOCK', 'reason': f'Account guardian state is {guardian_state}.'}

    equity = float(getattr(account, 'equity', 0) or getattr(account, 'balance', 0) or 0)
    risk_percent = float(getattr(account, 'risk_per_trade', 0) or 0)
    max_daily_drawdown = float(getattr(account, 'max_daily_drawdown', 0) or 0)
    current_daily_drawdown = float(getattr(account, 'current_daily_drawdown', 0) or 0)
    if equity <= 0 or risk_percent <= 0:
        return {'approved': False, 'status': 'UNKNOWN', 'reason': 'Account equity and risk policy are unavailable.'}
    if current_daily_drawdown + risk_percent > max_daily_drawdown:
        return {'approved': False, 'status': 'BLOCK', 'reason': 'Trade risk would exceed the daily drawdown limit.'}

    open_positions = int(getattr(account, 'open_positions', 0) or 0)
    max_positions = int(getattr(account, 'max_concurrent_positions', 0) or 0)
    if max_positions > 0 and open_positions >= max_positions:
        return {'approved': False, 'status': 'BLOCK', 'reason': 'Maximum concurrent position limit has been reached.'}

    risk_amount = equity * risk_percent / 100
    capability = next(
        (item for item in (getattr(account, 'market_discovery', {}) or {}).get('symbols', [])
         if item.get('name') == getattr(account, 'broker_symbol', '')),
        {},
    )
    contract_size = float(capability.get('contractSize') or 1)
    raw_volume = risk_amount / (stop_distance * contract_size)
    minimum = float(capability.get('volumeMin') or 0.01)
    maximum = float(capability.get('volumeMax') or raw_volume)
    step = float(capability.get('volumeStep') or minimum)
    volume = min(maximum, _step_down(raw_volume, step))
    if volume < minimum:
        return {'approved': False, 'status': 'BLOCK', 'reason': 'Calculated volume is below the broker minimum.'}

    return {
        'approved': True,
        'status': 'PASS',
        'reason': 'Risk is within account and broker limits.',
        'entry': entry,
        'stopLoss': stop_loss,
        'takeProfit': take_profit,
        'riskAmount': round(risk_amount, 2),
        'riskPercent': risk_percent,
        'volume': volume,
        'riskReward': round(reward_distance / stop_distance, 2),
    }
