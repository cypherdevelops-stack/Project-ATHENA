from __future__ import annotations

from datetime import datetime, time, timezone

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from backend.accounts.models import Account

from .config import news_settings
from .models import AdaptiveNewsStatistic, NewsIntelligenceSnapshot, NewsReactionObservation
from .provider_quality import provider_quality_summary
from .providers.registry import build_configured_registry


def _account(request):
    account_id = request.GET.get('accountId')
    if account_id:
        account = Account.objects.filter(user=request.user, pk=account_id).first()
        if account:
            return account
    return Account.objects.filter(user=request.user, is_default=True, enabled=True).first() or Account.objects.filter(user=request.user, enabled=True).first()


def _parse_datetime(value: str | None, *, end_of_day: bool = False):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if end_of_day and len(value) == 10:
        parsed = datetime.combine(parsed.date(), time.max, tzinfo=parsed.tzinfo)
    return parsed


def _snapshot_payload(snapshot: NewsIntelligenceSnapshot) -> dict:
    return {
        'id': snapshot.pk,
        'snapshotId': str(snapshot.snapshot_id),
        'decisionId': str(snapshot.decision_id) if snapshot.decision_id else None,
        'symbol': snapshot.symbol,
        'capturedAt': snapshot.captured_at.isoformat(),
        'providerAvailable': snapshot.provider_available,
        'newsState': snapshot.news_state,
        'fundamentalBias': snapshot.fundamental_bias,
        'eventRisk': snapshot.event_risk,
        'executionAllowed': snapshot.execution_allowed,
        'technicalAlignment': snapshot.technical_alignment,
        'technicalConflict': snapshot.technical_conflict,
        'sentimentScore': snapshot.sentiment_score,
        'sentimentConfidence': snapshot.sentiment_confidence,
        'impactScore': snapshot.impact_score,
        'reasonCodes': snapshot.reason_codes,
        'events': snapshot.events,
        'reaction': snapshot.reaction,
        'executionConditions': snapshot.execution_conditions,
        'fullPayload': snapshot.full_payload,
    }


@login_required
@require_GET
def current_news_view(request):
    account = _account(request)
    if account is None:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': 'No enabled trading account is available.'}, status=422)
    symbol = (request.GET.get('symbol') or account.canonical_asset or account.broker_symbol or 'XAUUSD').upper()
    snapshot = NewsIntelligenceSnapshot.objects.filter(account=account, symbol=symbol).first()
    if snapshot is None:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': 'No news snapshot is available.', 'symbol': symbol})
    return JsonResponse({'status': 'AVAILABLE', 'news': _snapshot_payload(snapshot)})


@login_required
@require_GET
def news_snapshots_view(request):
    account = _account(request)
    if account is None:
        return JsonResponse({'snapshots': []})
    query = NewsIntelligenceSnapshot.objects.filter(account=account)
    symbol = request.GET.get('symbol')
    event_risk = request.GET.get('eventRisk')
    event_state = request.GET.get('eventState')
    if symbol:
        query = query.filter(symbol=symbol.upper())
    if event_risk:
        query = query.filter(event_risk=event_risk.upper())
    if event_state:
        query = query.filter(events__contains=[{'event_state': event_state.upper()}])
    start = _parse_datetime(request.GET.get('start'))
    end = _parse_datetime(request.GET.get('end'), end_of_day=True)
    if start:
        query = query.filter(captured_at__gte=start)
    if end:
        query = query.filter(captured_at__lte=end)
    try:
        limit = min(max(int(request.GET.get('limit', 50)), 1), 200)
    except ValueError:
        return JsonResponse({'detail': 'limit must be an integer.'}, status=400)
    return JsonResponse({'snapshots': [_snapshot_payload(item) for item in query[:limit]]})


@login_required
@require_GET
def news_reactions_view(request):
    account = _account(request)
    if account is None:
        return JsonResponse({'reactions': []})
    query = NewsReactionObservation.objects.filter(news_snapshot__account=account)
    symbol = request.GET.get('symbol')
    state = request.GET.get('state')
    if symbol:
        query = query.filter(symbol=symbol.upper())
    if state:
        query = query.filter(reaction_state=state.upper())
    return JsonResponse({'reactions': [{
        'id': item.pk,
        'snapshotId': str(item.news_snapshot.snapshot_id),
        'symbol': item.symbol,
        'observedAt': item.observed_at.isoformat(),
        'expectedDirection': item.expected_direction,
        'actualDirection': item.actual_direction,
        'state': item.reaction_state,
        'priceChange': item.price_change,
        'volatility': item.volatility,
        'spread': item.spread,
        'outcomeContext': item.outcome_context,
    } for item in query[:200]]})


@login_required
@require_GET
def adaptive_statistics_view(request):
    account = _account(request)
    if account is None:
        return JsonResponse({'statistics': []})
    query = AdaptiveNewsStatistic.objects.all()
    symbol = request.GET.get('symbol')
    category = request.GET.get('category')
    regime = request.GET.get('regime')
    if symbol:
        allowed = set(NewsIntelligenceSnapshot.objects.filter(account=account, symbol=symbol.upper()).values_list('symbol', flat=True))
        query = query.filter(symbol__in=allowed)
    if category:
        query = query.filter(category=category.upper())
    if regime:
        query = query.filter(regime=regime.upper())
    return JsonResponse({'statistics': [{
        'id': item.pk,
        'symbol': item.symbol,
        'category': item.category,
        'regime': item.regime,
        'sourceClass': item.source_class,
        'observations': item.observations,
        'confirmedReactions': item.confirmed_reactions,
        'contraryReactions': item.contrary_reactions,
        'meanPriceChange': item.mean_price_change,
        'meanSentimentConfidence': item.mean_sentiment_confidence,
        'lastObservedAt': item.last_observed_at.isoformat(),
    } for item in query[:200]]})


@login_required
@require_GET
def provider_health_view(request):
    settings = news_settings()
    registry = build_configured_registry(settings)
    return JsonResponse({
        'providers': registry.health(),
        'quality': [provider_quality_summary(provider_name=name) for name in registry.health()],
        'configured': bool(registry.health()),
        'failClosed': settings['fail_closed'],
    })
