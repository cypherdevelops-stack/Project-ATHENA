from __future__ import annotations

from uuid import UUID

from django.db import IntegrityError

from backend.execution.models import PaperExecution
from backend.execution.paper_engine import PaperTradeError, open_paper_position
from backend.execution.risk_engine import assess_risk
from backend.execution.trade_setup import build_trade_setup


class PaperOrchestrationError(ValueError):
    pass


def execute_paper_decision(*, account, analysis: dict, decision_id: UUID, quote: dict) -> dict:
    """Execute one approved orchestrator decision in the paper engine."""
    orchestration = analysis.get('orchestration') or {}
    decision = orchestration.get('decision') or {}
    action = decision.get('action', orchestration.get('status', 'OBSERVE'))
    strategy = decision.get('strategy')

    existing = PaperExecution.objects.filter(decision_id=decision_id).first()
    if existing:
        return _execution_payload(existing, duplicate=True)

    if not action.endswith('_APPROVED') or strategy not in {'SCALPING', 'DAY_TRADING'}:
        return _record(
            account=account,
            decision_id=decision_id,
            status='SKIPPED',
            reason=f'Decision {action} is not paper-executable.',
            setup={},
            quote=quote,
        )

    from backend.intelligence.news.risk import analysis_execution_allowed
    news_allowed, news_reason = analysis_execution_allowed(
        analysis,
        symbol=account.canonical_asset or account.broker_symbol or 'XAUUSD',
    )
    if not news_allowed:
        return _record(
            account=account,
            decision_id=decision_id,
            status='REJECTED',
            reason=f'News execution block: {news_reason}',
            setup={},
            quote=quote,
        )

    candidates_key = 'scalping' if strategy == 'SCALPING' else 'dayTrading'
    candidates = (analysis.get(candidates_key) or {}).get('candidates') or []
    candidate = next((item for item in candidates if item.get('direction')), None)
    if not candidate:
        raise PaperOrchestrationError('Approved decision has no executable candidate.')

    entry_zone = candidate.get('entryZone') or {}
    entry = (float(entry_zone['lower']) + float(entry_zone['upper'])) / 2
    width = max(float(entry_zone['upper']) - float(entry_zone['lower']), 1e-9)
    stop_loss = entry - width * 0.5 if candidate['direction'] == 'BUY' else entry + width * 0.5
    take_profit = entry + width * 2 if candidate['direction'] == 'BUY' else entry - width * 2
    risk = assess_risk(
        account=account,
        direction=candidate['direction'],
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )
    setup = build_trade_setup(candidate=candidate, risk=risk)
    if not risk.get('approved') or setup.get('state') != 'RISK_APPROVED':
        return _record(
            account=account,
            decision_id=decision_id,
            status='REJECTED',
            reason=risk.get('reason', 'Paper risk approval failed.'),
            setup=setup,
            quote=quote,
        )

    try:
        position = open_paper_position(account=account, setup=setup, quote=quote)
    except PaperTradeError as error:
        return _record(
            account=account,
            decision_id=decision_id,
            status='REJECTED',
            reason=str(error),
            setup=setup,
            quote=quote,
        )

    return _record(
        account=account,
        decision_id=decision_id,
        status='OPENED',
        position_id=position['position_id'],
        setup=setup,
        quote=quote,
    )


def _record(*, account, decision_id, status, setup, quote, reason='', position_id=None) -> dict:
    try:
        execution = PaperExecution.objects.create(
            account=account,
            decision_id=decision_id,
            position_id=position_id,
            status=status,
            reason=reason,
            setup=setup,
            quote=quote,
        )
    except IntegrityError:
        execution = PaperExecution.objects.get(decision_id=decision_id)
        return _execution_payload(execution, duplicate=True)
    return _execution_payload(execution)


def _execution_payload(execution: PaperExecution, duplicate=False) -> dict:
    return {
        'status': execution.status,
        'reason': execution.reason,
        'decisionId': str(execution.decision_id),
        'positionId': execution.position_id,
        'duplicate': duplicate,
    }
