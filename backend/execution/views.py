from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.http import StreamingHttpResponse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from django.conf import settings

from backend.accounts.models import Account
from backend.execution.executioner_service import generate_execution_analysis, generate_trade_signals, generate_orchestrated_execution_analysis
from backend.execution.paper_engine import open_paper_position, list_paper_positions, update_paper_positions
from backend.market.regime import evaluate_regime
from backend.market.service import MarketDataError, market_data_service
from backend.market.news_sentiment import fetch_news_sentiment
from backend.intelligence.news.risk import analysis_execution_allowed
from backend.stream.event_bus import ScalpEvent, scalp_event_bus
from backend.execution.model_training import model_status, start_training, training_status, validate_saved_model
from backend.execution.xgboost_engine import get_active_xgboost_engine
from backend.execution.snapshot_service import persist_orchestration_snapshot
from backend.execution.live_engine import LiveExecutionError, send_live_order
from backend.execution.demo_execution import DemoExecutionError, execute_confirmed_demo_decision
from backend.execution.models import BrokerPositionSnapshot, ExecutionIntent, ExecutionLifecycleEvent, LiveExecutionAttempt, OrchestrationSnapshot
from backend.execution.reconciliation import reconcile_live_positions
from backend.journal.models import JournalEvent, JournalSession

import json
from queue import Empty, Queue


def _resolve_account_for_request(request):
    account_id = request.GET.get('accountId')
    account = None
    if account_id:
        account = Account.objects.filter(user=request.user, pk=account_id).first()
    if account is None:
        account = (
            Account.objects.filter(user=request.user, is_default=True, enabled=True).first()
            or Account.objects.filter(user=request.user, enabled=True).first()
        )
    return account


def _fetch_market_data(account):
    if not account or not account.broker_symbol:
        raise MarketDataError('No broker symbol is configured for execution analysis.')
    return market_data_service.fetch(account, timeframes=('M1', 'M5'))


@login_required
@require_GET
def execution_analysis_view(request):
    account = _resolve_account_for_request(request)
    if account is None:
        return JsonResponse({'status': 'ERROR', 'reason': 'No trading account is available.'}, status=422)
    if not account.broker_symbol:
        return JsonResponse({'status': 'ERROR', 'reason': 'No broker symbol has been discovered.'}, status=422)

    try:
        data = market_data_service.fetch(account, timeframes=('M1', 'M5', 'H1'))
        payload = generate_execution_analysis(account=account, m5_candles=data.candles['M5'], m1_candles=data.candles['M1'], current_price_data=data.snapshot.as_dict(), regime_context=evaluate_regime(data.candles['H1']).as_dict(), ml_engine=get_active_xgboost_engine())
        _publish_analysis_events(payload, symbol=account.canonical_asset or 'XAUUSD', user=request.user, account=account)
        return JsonResponse(payload)
    except Exception as error:
        return JsonResponse({'status': 'ERROR', 'reason': str(error)}, status=422)


@login_required
@require_GET
def execution_orchestration_view(request):
    """
    Unified orchestrated execution analysis integrating both SCALPING and DAY_TRADING engines.
    
    Uses the Strategy Orchestrator to produce coordinated market analysis and decisions.
    Requires HTF data (H1/H4) for day trading analysis.
    """
    account = _resolve_account_for_request(request)
    if account is None:
        return JsonResponse({'status': 'ERROR', 'reason': 'No trading account is available.'}, status=422)
    if not account.broker_symbol:
        return JsonResponse({'status': 'ERROR', 'reason': 'No broker symbol has been discovered.'}, status=422)

    try:
        # Fetch multi-timeframe data: M1, M5, M15, H1, H4
        data = market_data_service.fetch(account, timeframes=('M1', 'M5', 'M15', 'H1', 'H4'))
        
        regime_ctx = evaluate_regime(data.candles.get('H1', [])).as_dict()
        news_ctx = fetch_news_sentiment(symbol=account.canonical_asset or account.broker_symbol)
        
        payload = generate_orchestrated_execution_analysis(
            account=account,
            m5_candles=data.candles.get('M5', []),
            m1_candles=data.candles.get('M1', []),
            m15_candles=data.candles.get('M15', []),
            h1_candles=data.candles.get('H1', []),
            h4_candles=data.candles.get('H4', []),
            current_price_data=data.snapshot.as_dict(),
            regime_context=regime_ctx,
            ml_engine=get_active_xgboost_engine(),
            news_sentiment=news_ctx.as_dict(),
        )
        
        persist_orchestration_snapshot(account=account, analysis=payload)
        _publish_orchestrated_analysis_events(
            payload, 
            symbol=account.canonical_asset or 'XAUUSD', 
            user=request.user, 
            account=account
        )
        return JsonResponse(payload)
    except Exception as error:
        return JsonResponse({'status': 'ERROR', 'reason': str(error)}, status=422)


_last_event_signatures: dict[tuple[str, str], str] = {}


def _open_journal_session(*, user, account, symbol: str, title: str) -> JournalSession:
    """Reuse the latest open session, including databases with legacy duplicates."""
    session = JournalSession.objects.filter(
        user=user,
        account=account,
        status='OPEN',
    ).order_by('-updated_at', '-pk').first()
    if session is not None:
        return session
    return JournalSession.objects.create(
        user=user,
        account=account,
        status='OPEN',
        canonical_asset=symbol,
        title=title,
    )


def _publish_analysis_events(payload: dict, *, symbol: str, user=None, account=None) -> None:
    def publish(event_type: str, data: dict) -> None:
        signature = json.dumps(data, sort_keys=True, default=str)
        key = (symbol, event_type)
        if _last_event_signatures.get(key) == signature:
            return
        _last_event_signatures[key] = signature
        event = ScalpEvent(type=event_type, symbol=symbol, data=data)
        scalp_event_bus.publish(event)
        if user is not None:
            session = _open_journal_session(
                user=user,
                account=account,
                symbol=symbol,
                title=f'{symbol} scalping session',
            )
            JournalEvent.objects.create(session=session, event_type=event_type, body=json.dumps(data, sort_keys=True, default=str))

            from asgiref.sync import async_to_sync
            from backend.execution.orchestration_ws import OrchestrationNotificationMixin
            async_to_sync(OrchestrationNotificationMixin.send_orchestration_update)(symbol, payload)

    price = payload.get('price') or {}
    publish('MARKET_UPDATE', price)
    regime = payload.get('regimeContext') or {}
    publish('REGIME_UPDATE', regime)
    if payload.get('momentumMap'):
        publish('MOMENTUM_UPDATE', payload['momentumMap'])
    candidates = payload.get('candidates') or []
    if not candidates:
        return
    candidate = candidates[0]
    for gate in candidate.get('gates', []):
        publish('GATE_RESULT', gate)
    setup = candidate.get('setup') or {}
    event_type = 'SETUP_CONFIRMED' if setup.get('active') else 'SETUP_WAITING'
    publish(event_type, {
        'state': setup.get('missing', []),
        'status': candidate.get('decisionState', 'OBSERVE'),
        'missing': setup.get('missing', []),
        'direction': setup.get('direction'),
    })
    if payload.get('risk'):
        publish('RISK_RESULT', payload['risk'])


def _publish_orchestrated_analysis_events(payload: dict, *, symbol: str, user=None, account=None) -> None:
    """
    Publish events from orchestrated analysis to the event bus and journal.
    
    Publishes:
    - MARKET_UPDATE: Price and spread
    - REGIME_UPDATE: Market regime
    - ORCHESTRATION_RESULT: Unified orchestrator decision
    - SCALPING_STATUS: Scalping engine status
    - DAY_TRADING_STATUS: Day trading engine status
    """
    def publish(event_type: str, data: dict) -> None:
        signature = json.dumps(data, sort_keys=True, default=str)
        key = (symbol, event_type)
        if _last_event_signatures.get(key) == signature:
            return
        _last_event_signatures[key] = signature
        event = ScalpEvent(type=event_type, symbol=symbol, data=data)
        scalp_event_bus.publish(event)
        if user is not None:
            session = _open_journal_session(
                user=user,
                account=account,
                symbol=symbol,
                title=f'{symbol} multi-strategy session',
            )
            JournalEvent.objects.create(session=session, event_type=event_type, body=json.dumps(data, sort_keys=True, default=str))

    price = payload.get('price') or {}
    publish('MARKET_UPDATE', price)
    
    regime = payload.get('regime') or {}
    publish('REGIME_UPDATE', regime)
    if payload.get('momentumMap'):
        publish('MOMENTUM_UPDATE', payload['momentumMap'])
    
    orchestration = payload.get('orchestration') or {}
    publish('ORCHESTRATION_RESULT', orchestration)
    publish('NEWS_SENTIMENT', payload.get('news') or orchestration.get('news') or {})
    publish('NEWS_REACTION', payload.get('newsReaction') or {})
    publish('NEWS_RISK', payload.get('executionConditions') or {})
    
    scalping = payload.get('scalping') or {}
    publish('SCALPING_STATUS', {
        'status': scalping.get('status'),
        'candidates_count': len(scalping.get('candidates', [])),
    })
    
    day_trading = payload.get('dayTrading') or {}
    publish('DAY_TRADING_STATUS', {
        'status': day_trading.get('status'),
        'candidates_count': len(day_trading.get('candidates', [])),
    })


@login_required
@require_GET
def execution_events_view(request):
    symbol = request.GET.get('symbol', 'XAUUSD').upper()
    queue: Queue[ScalpEvent] = Queue()

    def receive(event: ScalpEvent) -> None:
        if event.symbol.upper() == symbol:
            queue.put(event)

    recent = scalp_event_bus.recent(symbol=symbol, limit=20)
    unsubscribe = scalp_event_bus.subscribe(receive)

    def stream():
        try:
            for event in recent:
                yield f'event: {event.type}\ndata: {json.dumps(event.as_dict())}\n\n'
            while True:
                try:
                    event = queue.get(timeout=2)
                    yield f'event: {event.type}\ndata: {json.dumps(event.as_dict())}\n\n'
                except Empty:
                    yield ': heartbeat\n\n'
        finally:
            unsubscribe()

    response = StreamingHttpResponse(stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required
@require_POST
def train_xgboost_view(request):
    account = _resolve_account_for_request(request)
    if account is None or not account.broker_symbol:
        return JsonResponse({'status': 'ERROR', 'reason': 'No enabled account with a broker symbol is available.'}, status=422)
    return JsonResponse(start_training(account.pk), status=202)


@login_required
@require_GET
def training_status_view(request):
    return JsonResponse(training_status(request.GET.get('jobId')))


@login_required
@require_GET
def model_status_view(request):
    return JsonResponse(model_status())


@login_required
@require_POST
def validate_model_view(request):
    try:
        return JsonResponse(validate_saved_model())
    except Exception as error:
        return JsonResponse({'status': 'ERROR', 'reason': str(error)}, status=422)


@login_required
@require_GET
def execution_signals_view(request):
    account = _resolve_account_for_request(request)
    if account is None:
        return JsonResponse({'signal': 'NEUTRAL', 'confidence': 0.0, 'reasoning': ['No trading account is available.']}, status=422)
    if not account.broker_symbol:
        return JsonResponse({'signal': 'NEUTRAL', 'confidence': 0.0, 'reasoning': ['No broker symbol has been discovered.']}, status=422)

    try:
        data = market_data_service.fetch(account, timeframes=('M1', 'M5', 'H1'))
        payload = generate_trade_signals(account=account, m5_candles=data.candles['M5'], m1_candles=data.candles['M1'], current_price_data=data.snapshot.as_dict(), regime_context=evaluate_regime(data.candles['H1']).as_dict(), ml_engine=get_active_xgboost_engine())
        risk = payload.get('risk')
        if risk:
            scalp_event_bus.publish(ScalpEvent(type='RISK_RESULT', symbol=account.canonical_asset or 'XAUUSD', data=risk))
        return JsonResponse(payload)
    except Exception as error:
        return JsonResponse({'signal': 'NEUTRAL', 'confidence': 0.0, 'reasoning': [str(error)]}, status=422)


@login_required
@require_GET
def execution_price_view(request):
    account = _resolve_account_for_request(request)
    if account is None:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': 'No trading account is available.'}, status=422)
    if not account.broker_symbol:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': 'No broker symbol has been discovered.'}, status=422)

    try:
        return JsonResponse({'status': 'HEALTHY', **market_data_service.fetch_snapshot(account).as_dict()})
    except Exception as error:
        return JsonResponse({'status': 'UNAVAILABLE', 'reason': str(error)}, status=422)


@login_required
@require_GET
def execution_audit_view(request):
    account = _resolve_account_for_request(request)
    if account is None:
        return JsonResponse({'events': [], 'attempts': []}, status=422)
    try:
        page = max(int(request.GET.get('page', 1)), 1)
        limit = min(max(int(request.GET.get('limit', 20)), 1), 100)
    except ValueError:
        return JsonResponse({'detail': 'page and limit must be integers.'}, status=400)
    event_query = ExecutionLifecycleEvent.objects.filter(account=account)
    attempt_query = LiveExecutionAttempt.objects.filter(account=account)
    intent_query = ExecutionIntent.objects.filter(account=account)
    decision_id = request.GET.get('decisionId')
    event_type = request.GET.get('eventType')
    state = request.GET.get('state')
    if decision_id:
        event_query = event_query.filter(decision_id=decision_id)
        attempt_query = attempt_query.filter(decision_id=decision_id)
        intent_query = intent_query.filter(decision_id=decision_id)
    if event_type:
        event_query = event_query.filter(event_type=event_type)
    if state:
        event_query = event_query.filter(state=state)
        attempt_query = attempt_query.filter(status=state)
        intent_query = intent_query.filter(status=state)
    event_count = event_query.count()
    attempt_count = attempt_query.count()
    intent_count = intent_query.count()
    offset = (page - 1) * limit
    events = event_query.order_by('-created_at')[offset:offset + limit]
    attempts = attempt_query.order_by('-created_at')[offset:offset + limit]
    positions = BrokerPositionSnapshot.objects.filter(account=account).order_by('-observed_at')[:limit]
    return JsonResponse({
        'page': page,
        'limit': limit,
        'eventCount': event_count,
        'attemptCount': attempt_count,
        'intentCount': intent_count,
        'events': [{
            'id': event.pk,
            'type': event.event_type,
            'state': event.state,
            'decisionId': str(event.decision_id),
            'symbol': event.symbol,
            'payload': event.payload,
            'createdAt': event.created_at.isoformat(),
        } for event in events],
        'attempts': [{
            'id': attempt.pk,
            'intentId': attempt.intent_id,
            'decisionId': str(attempt.decision_id),
            'strategy': attempt.strategy,
            'status': attempt.status,
            'order': attempt.order_ticket,
            'deal': attempt.deal_ticket,
            'reason': attempt.reason,
            'brokerResponse': attempt.broker_response,
            'createdAt': attempt.created_at.isoformat(),
            'completedAt': attempt.completed_at.isoformat() if attempt.completed_at else None,
        } for attempt in attempts],
        'intents': [{
            'id': intent.pk,
            'decisionId': str(intent.decision_id),
            'strategy': intent.strategy,
            'direction': intent.direction,
            'symbol': intent.symbol,
            'status': intent.status,
            'setup': intent.setup,
            'createdAt': intent.created_at.isoformat(),
            'expiresAt': intent.expires_at.isoformat() if intent.expires_at else None,
            'invalidationReason': intent.invalidation_reason,
        } for intent in intent_query.order_by('-created_at')[offset:offset + limit]],
        'positions': [{
            'ticket': position.ticket,
            'decisionId': str(position.decision_id) if position.decision_id else None,
            'symbol': position.symbol,
            'direction': position.direction,
            'volume': str(position.volume),
            'priceOpen': str(position.price_open),
            'stopLoss': str(position.stop_loss) if position.stop_loss is not None else None,
            'takeProfit': str(position.take_profit) if position.take_profit is not None else None,
            'state': position.state,
            'observedAt': position.observed_at.isoformat(),
            'closedAt': position.closed_at.isoformat() if position.closed_at else None,
        } for position in positions],
    })


@login_required
@require_POST
def reconcile_execution_view(request):
    try:
        body = json.loads(request.body or '{}')
        account_id = body.get('accountId')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'UNSAFE', 'reason': 'Request body must be valid JSON.'}, status=400)
    account = Account.objects.filter(user=request.user, pk=account_id).first()
    if account is None:
        return JsonResponse({'status': 'UNSAFE', 'reason': 'Account was not found.'}, status=404)
    return JsonResponse(reconcile_live_positions(account=account))


@login_required
@require_POST
def live_order_view(request):
    account = _resolve_account_for_request(request)
    try:
        body = json.loads(request.body or '{}')
        if body.get('confirm') is not True:
            raise LiveExecutionError('Explicit live-order confirmation is required.')
        if account is None:
            raise LiveExecutionError('No enabled trading account is available.')
        data = market_data_service.fetch(account, timeframes=('M1', 'M5', 'H1'))
        news_ctx = fetch_news_sentiment(symbol=account.canonical_asset or account.broker_symbol)
        news_allowed, news_reason = analysis_execution_allowed({'news': news_ctx.as_dict()}, symbol=account.canonical_asset or account.broker_symbol)
        if not news_allowed:
            raise LiveExecutionError(f'News execution block: {news_reason}')
        signals = generate_trade_signals(account=account, m5_candles=data.candles['M5'], m1_candles=data.candles['M1'], current_price_data=data.snapshot.as_dict(), regime_context=evaluate_regime(data.candles['H1']).as_dict(), ml_engine=get_active_xgboost_engine())
        return JsonResponse(send_live_order(account=account, setup=signals.get('tradeSetup') or {}, requested_price=signals.get('tradeSetup', {}).get('entry'), max_slippage=float(body.get('maxSlippage', 0)), idempotency_key=body.get('idempotencyKey')))
    except (json.JSONDecodeError, TypeError, ValueError, LiveExecutionError) as error:
        return JsonResponse({'status': 'REJECTED', 'reason': str(error)}, status=422)


@login_required
@require_POST
def confirmed_demo_order_view(request):
    try:
        body = json.loads(request.body or '{}')
        snapshot = OrchestrationSnapshot.objects.filter(
            account__user=request.user,
            decision_id=body.get('decisionId'),
        ).select_related('account').first()
        if snapshot is None:
            raise DemoExecutionError('The orchestration decision was not found.')
        result = execute_confirmed_demo_decision(
            account=snapshot.account,
            snapshot=snapshot,
            confirmation=body.get('confirm'),
            idempotency_key=body.get('idempotencyKey', ''),
            max_slippage=float(body.get('maxSlippage', 0)),
        )
        return JsonResponse(result)
    except (json.JSONDecodeError, TypeError, ValueError, DemoExecutionError, LiveExecutionError) as error:
        return JsonResponse({'status': 'REJECTED', 'reason': str(error)}, status=422)


@login_required
@require_POST
def open_paper_position_view(request):
    account = _resolve_account_for_request(request)
    if account is None or not account.broker_symbol:
        return JsonResponse({'status': 'ERROR', 'reason': 'No enabled account with a broker symbol is available.'}, status=422)
    try:
        data = market_data_service.fetch(account, timeframes=('M1', 'M5', 'H1'))
        signals = generate_trade_signals(account=account, m5_candles=data.candles['M5'], m1_candles=data.candles['M1'], current_price_data=data.snapshot.as_dict(), regime_context=evaluate_regime(data.candles['H1']).as_dict(), ml_engine=get_active_xgboost_engine())
        position = open_paper_position(account=account, setup=signals.get('tradeSetup') or {}, quote=data.snapshot.as_dict())
        return JsonResponse(position, status=201)
    except Exception as error:
        return JsonResponse({'status': 'ERROR', 'reason': str(error)}, status=422)


@login_required
@require_GET
def paper_positions_view(request):
    account = _resolve_account_for_request(request)
    if account is None:
        return JsonResponse({'positions': []})
    positions = list_paper_positions(account_id=account.pk)
    if not any(position.get('state') in {'ACTIVE', 'TP1_HIT'} for position in positions):
        return JsonResponse({'positions': positions})
    try:
        quote = market_data_service.fetch_snapshot(account).as_dict()
        update_paper_positions(account_id=account.pk, quote=quote)
    except Exception:
        pass
    return JsonResponse({'positions': list_paper_positions(account_id=account.pk)})
