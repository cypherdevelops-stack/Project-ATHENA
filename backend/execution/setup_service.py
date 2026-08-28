from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from backend.execution.contracts import CanonicalTradeSetup, ContractValidationError
from backend.execution.risk_engine import assess_risk


def build_approved_setup(*, account, candidate: dict[str, Any], strategy: str, current_price: float) -> dict[str, Any]:
    """Build and validate the executable setup for one selected candidate."""
    entry_zone = candidate.get('entryZone')
    direction = candidate.get('direction')
    if not entry_zone or direction not in {'BUY', 'SELL'}:
        raise ContractValidationError('Selected candidate has no executable entry zone.')

    lower = float(entry_zone['lower'])
    upper = float(entry_zone['upper'])
    if lower <= 0 or upper <= 0 or lower >= upper:
        raise ContractValidationError('Candidate entry zone is invalid.')

    entry = (lower + upper) / 2
    width = upper - lower
    stop_loss = lower - width * 0.5 if direction == 'BUY' else upper + width * 0.5
    take_profit1 = upper if direction == 'BUY' else lower
    take_profit2 = upper + width * 2 if direction == 'BUY' else lower - width * 2
    risk = assess_risk(
        account=account,
        direction=direction,
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit2,
    )
    if not risk.get('approved'):
        raise ContractValidationError(risk.get('reason', 'Risk approval failed.'))

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=12 if strategy == 'SCALPING' else 60)
    setup = CanonicalTradeSetup(
        strategy=strategy,
        direction=direction,
        symbol=account.broker_symbol,
        entry=entry,
        stop_loss=stop_loss,
        take_profit1=take_profit1,
        take_profit2=take_profit2,
        volume=float(risk['volume']),
        score=float(candidate.get('score', 0)),
        risk_reward=float(risk.get('riskReward') or 0) or None,
        expires_at=expires_at,
        evidence={
            'candidateId': candidate.get('candidateId'),
            'currentPrice': current_price,
            'risk': risk,
            'reasonCodes': candidate.get('reasonCodes', []),
            'smc': candidate.get('smcEvidence', {}),
        },
    )
    return setup.as_payload()
