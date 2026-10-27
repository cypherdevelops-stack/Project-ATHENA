from __future__ import annotations

import json
from datetime import datetime, timezone as datetime_timezone
from zoneinfo import ZoneInfo

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from backend.accounts.models import Account
from backend.market.service import market_data_service
from .ingestion import import_dataset
from .models import BacktestingDrawing, HistoricalDataset, ReplaySession
from .replay import advance_replay, create_replay, execute_replay_signal, replay_analysis, replay_metrics, replay_signals, serialize_decision, serialize_session, session_candles

TIMEFRAMES = {
    'M1': 'TIMEFRAME_M1', 'M5': 'TIMEFRAME_M5', 'M15': 'TIMEFRAME_M15',
    'M30': 'TIMEFRAME_M30', 'H1': 'TIMEFRAME_H1', 'H4': 'TIMEFRAME_H4', 'D1': 'TIMEFRAME_D1',
}


def _resolve_account(request):
    account_id = request.GET.get('accountId')
    if account_id:
        return Account.objects.filter(user=request.user, pk=account_id, enabled=True).first()
    return (Account.objects.filter(user=request.user, is_default=True, enabled=True).first()
            or Account.objects.filter(user=request.user, enabled=True).first())


def _candle_count(request) -> int:
    try:
        return min(max(int(request.GET.get('candleCount', 500)), 50), 2_000)
    except (TypeError, ValueError):
        return 500


def _serialize_drawing(drawing: BacktestingDrawing) -> dict:
    return {
        'id': drawing.id,
        'type': drawing.drawing_type,
        'start': drawing.start,
        'end': drawing.end,
        'symbol': drawing.symbol,
        'timeframe': drawing.timeframe,
        'updatedAt': drawing.updated_at.isoformat(),
    }


def _drawing_scope(request):
    account = _resolve_account(request)
    if account is None:
        return None, None, None
    symbol = request.GET.get('symbol') or account.broker_symbol
    timeframe = request.GET.get('timeframe', 'M5').upper()
    return account, symbol, timeframe


def _replay_session(request):
    return ReplaySession.objects.filter(user_id=request.user.pk, pk=request.GET.get('sessionId')).first()


def _serialize_dataset(dataset):
    return {'id': dataset.id, 'accountId': dataset.account_id, 'source': dataset.source, 'symbol': dataset.symbol,
            'timezone': dataset.timezone, 'timeframe': dataset.timeframe, 'startTime': dataset.start_time,
            'endTime': dataset.end_time, 'version': dataset.version, 'rowCount': dataset.row_count,
            'filename': dataset.metadata.get('filename')}


@login_required
@require_http_methods(['GET', 'POST'])
def datasets_view(request):
    if request.method == 'GET':
        datasets = HistoricalDataset.objects.filter(user_id=request.user.pk)
        if request.GET.get('accountId'):
            datasets = datasets.filter(account_id=request.GET['accountId'])
        return JsonResponse({'datasets': [_serialize_dataset(dataset) for dataset in datasets.order_by('-created_at')]})
    account = Account.objects.filter(user=request.user, pk=request.POST.get('accountId'), enabled=True).first()
    upload = request.FILES.get('file')
    if account is None or upload is None:
        return JsonResponse({'detail': 'An enabled account and CSV/Parquet file are required.'}, status=422)
    try:
        dataset = import_dataset(user=request.user, account=account, upload=upload,
            source_timezone=request.POST.get('timezone', 'UTC'), timeframe=request.POST.get('timeframe', 'M5').upper(),
            symbol=request.POST.get('symbol') or account.broker_symbol, version=request.POST.get('version', '1'))
    except (TypeError, ValueError) as error:
        return JsonResponse({'detail': str(error)}, status=400)
    return JsonResponse(_serialize_dataset(dataset), status=201)


@login_required
@require_http_methods(['GET', 'POST'])
def replay_view(request):
    session = _replay_session(request)
    if request.method == 'POST' and session is None:
        try:
            payload = json.loads(request.body or '{}')
        except ValueError:
            return JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)
        account_id = payload.get('accountId')
        account = Account.objects.filter(user=request.user, pk=account_id, enabled=True).first()
        if account is None:
            return JsonResponse({'detail': 'No enabled trading account is available.'}, status=422)
        timeframe = str(payload.get('timeframe', 'M5')).upper()
        if timeframe not in TIMEFRAMES:
            return JsonResponse({'detail': 'Unsupported replay timeframe.'}, status=400)
        try:
            dataset = HistoricalDataset.objects.filter(user_id=request.user.pk, account_id=account.pk, pk=payload.get('datasetId')).first() if payload.get('datasetId') else None
            if payload.get('datasetId') and dataset is None:
                return JsonResponse({'detail': 'Historical dataset not found.'}, status=404)
            def range_bound(value, end=False):
                if not value:
                    return None
                parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=ZoneInfo(dataset.timezone if dataset else 'UTC'))
                return int(parsed.timestamp()) + (86399 if end and len(str(value)) == 10 else 0)
            session = create_replay(user=request.user, account=account, timeframe=timeframe,
                                    candle_count=min(max(int(payload.get('candleCount', 500)), 100), 2_000),
                                    slippage=float(payload.get('slippage', 0)), commission=float(payload.get('commission', 0)),
                                    dataset=dataset, start_time=range_bound(payload.get('startDate')),
                                    end_time=range_bound(payload.get('endDate'), end=True))
        except (TypeError, ValueError) as error:
            return JsonResponse({'detail': f'Invalid replay configuration: {error}'}, status=400)
        return JsonResponse(serialize_session(session), status=201)
    if session is None:
        return JsonResponse({'detail': 'Replay session not found.'}, status=404)
    if request.method == 'POST':
        try:
            payload = json.loads(request.body or '{}')
        except ValueError:
            return JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)
        action = payload.get('action', 'step')
        if action == 'step':
            session = advance_replay(session, max(1, int(payload.get('amount', 1))))
        elif action == 'reset':
            session.cursor = min(50, len(session_candles(session)))
            session.status = ReplaySession.Status.PAUSED
            session.trades.all().delete()
            session.decisions.all().delete()
            session.save(update_fields=('cursor', 'status', 'updated_at'))
        elif action in {'pause', 'play'}:
            session.status = ReplaySession.Status.PAUSED if action == 'pause' else ReplaySession.Status.PLAYING
            session.save(update_fields=('status', 'updated_at'))
        elif action == 'execute':
            return JsonResponse({'session': serialize_session(session), 'analysis': replay_analysis(session), 'signals': execute_replay_signal(session), 'metrics': replay_metrics(session)})
        else:
            return JsonResponse({'detail': 'Unsupported replay action.'}, status=400)
    response = {'session': serialize_session(session), 'analysis': replay_analysis(session), 'signals': replay_signals(session), 'metrics': replay_metrics(session)}
    if request.GET.get('includeDecisions') == '1':
        response['decisions'] = [serialize_decision(decision) for decision in session.decisions.all()]
    return JsonResponse(response)


@login_required
@require_http_methods(['GET', 'POST', 'DELETE'])
def drawings_view(request):
    account, symbol, timeframe = _drawing_scope(request)
    if account is None:
        return JsonResponse({'detail': 'No enabled trading account is available.'}, status=422)
    if not symbol:
        return JsonResponse({'detail': 'No broker symbol is available for this account.'}, status=422)

    drawings = BacktestingDrawing.objects.filter(
        user_id=request.user.pk,
        account_id=account.pk,
        symbol=symbol,
        timeframe=timeframe,
    )
    if request.method == 'GET':
        return JsonResponse({'drawings': [_serialize_drawing(drawing) for drawing in drawings.order_by('created_at')]})
    if request.method == 'DELETE':
        drawings.delete()
        return JsonResponse({}, status=204)

    try:
        payload = json.loads(request.body or '{}')
    except ValueError:
        return JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)
    drawing_type = payload.get('type')
    start = payload.get('start')
    end = payload.get('end')
    valid_types = {choice for choice, _label in BacktestingDrawing.DrawingType.choices}
    if drawing_type not in valid_types:
        return JsonResponse({'detail': 'Unsupported drawing type.'}, status=400)
    if not isinstance(start, dict) or not {'time', 'price'} <= start.keys():
        return JsonResponse({'detail': 'Drawing start must contain time and price.'}, status=400)
    if drawing_type in {'trendline', 'ray', 'rectangle', 'triangle', 'ellipse', 'long_position', 'short_position'} and (not isinstance(end, dict) or not {'time', 'price'} <= end.keys()):
        return JsonResponse({'detail': 'This drawing requires an end point with time and price.'}, status=400)
    try:
        start = {'time': int(start['time']), 'price': float(start['price'])}
        end = {'time': int(end['time']), 'price': float(end['price'])} if end else None
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'Drawing coordinates must be numeric.'}, status=400)
    drawing = BacktestingDrawing.objects.create(
        user_id=request.user.pk,
        account_id=account.pk,
        symbol=symbol,
        timeframe=timeframe,
        drawing_type=drawing_type,
        start=start,
        end=end,
    )
    return JsonResponse(_serialize_drawing(drawing), status=201)


@login_required
@require_GET
def market_data_view(request):
    account = _resolve_account(request)
    if account is None:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': 'No enabled trading account is available.'})
    if not account.broker_symbol:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': 'No broker symbol has been discovered for this account.'})

    timeframe_name = request.GET.get('timeframe', 'M5').upper()
    timeframe_attribute = TIMEFRAMES.get(timeframe_name)
    if timeframe_attribute is None:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': f'Unsupported timeframe: {timeframe_name}.'}, status=400)

    try:
        data = market_data_service.fetch(
            account,
            timeframes=(timeframe_name,),
            candle_count=_candle_count(request),
        )
        snapshot = data.snapshot
        return JsonResponse({
            'status': 'HEALTHY' if data.data_quality['verified'] else 'UNVERIFIED',
            'accountId': account.id, 'accountName': account.display_name,
            'canonicalAsset': account.canonical_asset, 'brokerSymbol': account.broker_symbol,
            'timeframe': timeframe_name, 'candles': data.candles[timeframe_name],
            'price': {
                'bid': snapshot.bid,
                'ask': snapshot.ask,
                'spread': snapshot.spread,
                'timestamp': snapshot.timestamp,
            },
            'receivedAt': snapshot.received_at,
            'marketDataQuality': data.data_quality,
        })
    except Exception as error:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': str(error)})
