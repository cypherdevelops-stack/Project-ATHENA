from __future__ import annotations

from typing import Any

from .models import NewsAMEFRecord, NewsIntelligenceSnapshot, NewsReactionObservation


def persist_news_snapshot(*, account, analysis: dict[str, Any], orchestration_snapshot=None) -> NewsIntelligenceSnapshot | None:
    """Persist immutable news context and its current reaction observation."""
    news = analysis.get('news') or {}
    if not news and analysis.get('status') == 'ERROR':
        return None
    symbol = account.canonical_asset or account.broker_symbol or 'XAUUSD'
    instrument = (news.get('instruments') or {}).get(symbol, {})
    reaction = analysis.get('newsReaction') or {}
    snapshot = NewsIntelligenceSnapshot.objects.create(
        account_id=account.pk,
        decision_id=orchestration_snapshot.decision_id if orchestration_snapshot else None,
        symbol=symbol,
        provider_available=bool(news.get('provider_available', False)),
        news_state=str(news.get('state', 'DEGRADED')),
        fundamental_bias=str(instrument.get('fundamental_bias', news.get('label', 'UNCERTAIN'))),
        event_risk=str(instrument.get('event_risk', 'CLEAR')),
        execution_allowed=bool(instrument.get('execution_allowed', False)),
        technical_alignment=str(instrument.get('technical_alignment', 'UNCERTAIN')),
        technical_conflict=bool(instrument.get('technical_conflict', False)),
        sentiment_score=float(news.get('score', 0) or 0),
        sentiment_confidence=float(news.get('confidence', 0) or 0),
        impact_score=float(instrument.get('impact_score', 0) or 0),
        reason_codes=list(instrument.get('reason_codes', [])),
        events=list(news.get('events', [])),
        reaction=reaction,
        execution_conditions=analysis.get('executionConditions') or {},
        full_payload={'news': news, 'instrument': instrument},
    )
    if reaction:
        observation = NewsReactionObservation.objects.create(
            news_snapshot_id=snapshot.pk,
            symbol=symbol,
            expected_direction=str(reaction.get('expected_direction', 'UNKNOWN')),
            actual_direction=str(reaction.get('actual_direction', 'UNKNOWN')),
            reaction_state=str(reaction.get('state', 'UNCONFIRMED')),
            price_change=reaction.get('price_change'),
            volatility=str(reaction.get('volatility', 'UNKNOWN')),
            spread=reaction.get('spread'),
            outcome_context={'decisionId': str(orchestration_snapshot.decision_id)} if orchestration_snapshot else {},
        )
        from .adaptive import record_reaction_outcome
        record_reaction_outcome(snapshot=snapshot, regime=str((analysis.get('regime') or {}).get('regime', 'UNKNOWN')))
    NewsAMEFRecord.objects.create(
        news_snapshot_id=snapshot.pk,
        event_context={'events': snapshot.events},
        asset_context={'symbol': snapshot.symbol, 'fundamentalBias': snapshot.fundamental_bias, 'impactScore': snapshot.impact_score},
        technical_context={'alignment': snapshot.technical_alignment, 'conflict': snapshot.technical_conflict},
        reaction_context=snapshot.reaction,
        execution_context={
            'newsState': snapshot.news_state,
            'eventRisk': snapshot.event_risk,
            'executionAllowed': snapshot.execution_allowed,
            'conditions': snapshot.execution_conditions,
        },
    )
    return snapshot
