from __future__ import annotations

from datetime import datetime, timedelta, timezone


def build_trade_setup(*, candidate: dict, risk: dict | None, timeframe_minutes: int = 1) -> dict:
    """Build the single trade contract consumed by risk, execution, and the UI."""
    entry_zone = candidate.get('entryZone')
    direction = candidate.get('direction')
    if not entry_zone or direction not in {'BUY', 'SELL'}:
        return {
            'state': 'OBSERVE',
            'direction': direction,
            'entry': None,
            'stopLoss': None,
            'takeProfit1': None,
            'takeProfit2': None,
            'volume': None,
            'riskReward': None,
            'score': candidate.get('score', 0),
            'evidence': candidate.get('confirmation', {}),
            'expiresAt': None,
        }

    lower, upper = float(entry_zone['lower']), float(entry_zone['upper'])
    entry = (lower + upper) / 2
    width = max(upper - lower, 1e-9)
    stop_loss = lower - width * 0.5 if direction == 'BUY' else upper + width * 0.5
    take_profit1 = upper if direction == 'BUY' else lower
    take_profit2 = upper + width * 2 if direction == 'BUY' else lower - width * 2
    reward = abs(take_profit2 - entry)
    risk_distance = abs(entry - stop_loss)
    formation_time = candidate.get('poiTime')
    expires_at = None
    if formation_time:
        expires_at = (datetime.fromtimestamp(float(formation_time), timezone.utc) + timedelta(minutes=timeframe_minutes * 12)).isoformat()
    return {
        'state': 'RISK_APPROVED' if risk and risk.get('approved') else candidate.get('decisionState', 'OBSERVE'),
        'direction': direction,
        'entry': entry,
        'stopLoss': stop_loss,
        'takeProfit1': take_profit1,
        'takeProfit2': take_profit2,
        'volume': risk.get('volume') if risk else None,
        'riskPercent': risk.get('riskPercent') if risk else None,
        'riskAmount': risk.get('riskAmount') if risk else None,
        'riskReward': round(reward / risk_distance, 2) if risk_distance else None,
        'score': candidate.get('score', 0),
        'evidence': candidate.get('confirmation', {}),
        'expiresAt': expires_at,
    }
