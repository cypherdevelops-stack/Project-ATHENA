import json
from json import JSONDecodeError

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from backend.accounts.models import Account

from .models import JournalEvent, JournalSession


def _market_session_for_scan(scan_time):
    hour = scan_time.hour
    if 13 <= hour < 21:
        return 'NEW_YORK'
    if 8 <= hour < 16:
        return 'LONDON'
    if hour < 9:
        return 'TOKYO'
    return 'UNKNOWN'


def _event_payload(event):
    return {
        'id': event.pk,
        'eventType': event.event_type,
        'body': event.body,
        'createdAt': event.created_at.isoformat(),
    }


def _session_payload(session):
    return {
        'id': session.pk,
        'accountId': session.account_id,
        'canonicalAsset': session.canonical_asset,
        'marketSession': session.market_session,
        'regime': session.regime,
        'title': session.title,
        'status': session.status,
        'startedAt': session.started_at.isoformat(),
        'updatedAt': session.updated_at.isoformat(),
        'events': [_event_payload(event) for event in session.events.order_by('created_at')],
    }


@login_required
@require_GET
def sessions_view(request):
    sessions = JournalSession.objects.filter(user=request.user).prefetch_related('events')[:50]
    return JsonResponse({'sessions': [_session_payload(session) for session in sessions]})


@login_required
@require_http_methods(['POST'])
def create_session_view(request):
    try:
        body = json.loads(request.body or '{}')
    except JSONDecodeError:
        return JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({'detail': 'Request body must be a JSON object.'}, status=400)
    account_id = body.get('accountId') or None
    if account_id is not None and not Account.objects.filter(pk=account_id, user=request.user).exists():
        return JsonResponse({'detail': 'Account was not found.'}, status=404)
    scan_time = timezone.now()
    market_session = str(body.get('marketSession', '')).strip().upper() or _market_session_for_scan(scan_time)
    session = JournalSession.objects.create(
        user=request.user,
        account_id=account_id,
        canonical_asset=str(body.get('canonicalAsset', 'XAUUSD')).strip() or 'XAUUSD',
        market_session=market_session,
        regime=str(body.get('regime', 'UNKNOWN')).strip() or 'UNKNOWN',
        title=str(body.get('title', 'Market observation')).strip() or 'Market observation',
    )
    return JsonResponse(_session_payload(session), status=201)


@login_required
@require_http_methods(['POST'])
def create_event_view(request, session_id):
    try:
        body = json.loads(request.body or '{}')
    except JSONDecodeError:
        return JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({'detail': 'Request body must be a JSON object.'}, status=400)
    session = JournalSession.objects.filter(pk=session_id, user=request.user).first()
    if session is None:
        return JsonResponse({'detail': 'Journal session was not found.'}, status=404)
    event_type = str(body.get('eventType', '')).strip()
    event_body = str(body.get('body', '')).strip()
    if not event_type or not event_body:
        return JsonResponse({'detail': 'Event type and body are required.'}, status=400)
    event = JournalEvent.objects.create(session=session, event_type=event_type, body=event_body)
    return JsonResponse(_event_payload(event), status=201)
