from __future__ import annotations

from typing import Any

from backend.execution.contracts import OrchestrationDecision
from backend.execution.models import OrchestrationSnapshot
from backend.execution.lifecycle_events import publish_lifecycle_event
from backend.execution.intent_service import persist_execution_intent


def persist_orchestration_snapshot(*, account, analysis: dict[str, Any]) -> OrchestrationSnapshot | None:
    """Persist one successful orchestration decision for audit and replay."""
    if analysis.get('status') == 'ERROR':
        return None

    canonical_decision = OrchestrationDecision.from_analysis(analysis)
    analysis.setdefault('orchestration', {}).setdefault('decision', {})['decisionId'] = str(canonical_decision.decision_id)
    analysis['decisionId'] = str(canonical_decision.decision_id)
    orchestration = analysis.get('orchestration') or {}
    scalping = analysis.get('scalping') or {}
    day_trading = analysis.get('dayTrading') or {}
    portfolio = orchestration.get('portfolio') or {}
    price = analysis.get('price') or {}
    regime = analysis.get('regime') or {}
    decision = orchestration.get('decision') or {}
    scalp_primary = (scalping.get('candidates') or [{}])[0]
    day_primary = (day_trading.get('candidates') or [{}])[0]

    snapshot = OrchestrationSnapshot.objects.create(
        account=account,
        decision_id=canonical_decision.decision_id,
        symbol=account.broker_symbol or account.canonical_asset or 'XAUUSD',
        regime=regime.get('regime', orchestration.get('market_regime', 'UNKNOWN')),
        bid_price=price.get('bid', 0),
        ask_price=price.get('ask', 0),
        spread=price.get('spread', 0),
        scalping_status=scalping.get('status', 'OBSERVE'),
        scalping_direction=scalp_primary.get('direction'),
        scalping_score=scalp_primary.get('score', 0),
        scalping_confidence=scalp_primary.get('confidence', 0),
        scalping_evidence=scalp_primary.get('evidence', {}),
        day_trading_status=day_trading.get('status', 'OBSERVE'),
        day_trading_direction=day_primary.get('direction'),
        day_trading_score=day_primary.get('score', 0),
        day_trading_confidence=day_primary.get('confidence', 0),
        day_trading_evidence=day_primary.get('evidence', {}),
        risk_available=portfolio.get('risk_available', False),
        daily_drawdown_pct=portfolio.get('daily_drawdown_pct', 0),
        account_equity=portfolio.get('account_equity', 0),
        decision=canonical_decision.action,
        decision_reason=canonical_decision.reason,
        reason_codes=canonical_decision.reason_codes,
        recommended_strategy=decision.get('strategy'),
        ml_probability=scalp_primary.get('evidence', {}).get('ml_probability', 0),
        full_payload=analysis,
    )
    publish_lifecycle_event(
        account=account,
        decision_id=snapshot.decision_id,
        event_type='ORCHESTRATION_DECISION_CREATED',
        state=canonical_decision.action,
        symbol=snapshot.symbol,
        payload={
            'reason': canonical_decision.reason,
            'reasonCodes': canonical_decision.reason_codes,
        },
    )
    if canonical_decision.action.endswith('_APPROVED') and decision.get('strategy') and decision.get('direction') and decision.get('setup'):
        intent = persist_execution_intent(
            account=account,
            snapshot=snapshot,
            decision=decision,
            setup=decision['setup'],
        )
        publish_lifecycle_event(
            account=account,
            decision_id=snapshot.decision_id,
            event_type='EXECUTION_QUEUED',
            state='QUEUED',
            symbol=intent.symbol,
            payload={'intentId': intent.pk, 'strategy': intent.strategy, 'direction': intent.direction},
        )
    return snapshot
