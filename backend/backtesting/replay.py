from __future__ import annotations

from datetime import datetime, timezone

from django.db import transaction

from backend.execution.executioner_service import generate_execution_analysis, generate_trade_signals
from backend.market.regime import evaluate_regime
from backend.market.service import market_data_service
from .models import HistoricalCandle, ReplayDecision, ReplaySession, ReplayTrade

REPLAY_TIMEFRAMES = ('M1', 'M5', 'H1')


def session_candles(session, timeframe=None):
    selected = timeframe or session.timeframe
    query = HistoricalCandle.objects.filter(user=session.user, account=session.account, symbol=session.symbol, timeframe=selected)
    if session.dataset and selected == session.dataset.timeframe:
        query = query.filter(dataset=session.dataset)
    if session.start_time is not None:
        query = query.filter(timestamp__gte=session.start_time)
    if session.end_time is not None:
        query = query.filter(timestamp__lte=session.end_time)
    return [candle.as_dict() for candle in query]


def _snapshot(session, candle):
    price = float(candle['close'])
    timestamp = datetime.fromtimestamp(candle['time'], tz=timezone.utc).isoformat()
    return {'symbol': session.symbol, 'brokerSymbol': session.symbol, 'bid': price, 'ask': price,
            'spread': session.slippage, 'timestamp': timestamp, 'mt5Time': timestamp,
            'receivedAt': timestamp, 'latencyMs': 0}


def serialize_session(session):
    candles = session_candles(session)
    cursor = min(session.cursor, len(candles))
    trades = list(session.trades.order_by('created_at'))
    return {'id': session.id, 'accountId': session.account_id, 'symbol': session.symbol,
            'datasetId': session.dataset_id, 'source': session.dataset.source if session.dataset else 'MT5',
            'datasetTimezone': session.dataset.timezone if session.dataset else 'UTC',
            'startTime': session.start_time, 'endTime': session.end_time,
            'timeframe': session.timeframe, 'cursor': cursor, 'totalCandles': len(candles),
            'status': session.status, 'speed': session.speed, 'slippage': session.slippage,
            'commission': session.commission,
            'currentTime': candles[cursor - 1]['time'] if cursor else None, 'candles': candles[:cursor],
            'trades': [serialize_trade(trade) for trade in trades],
            'decisionCount': session.decisions.count()}


def serialize_trade(trade):
    return {'id': trade.id, 'direction': trade.direction, 'entry': trade.entry,
            'stopLoss': trade.stop_loss, 'takeProfit': trade.take_profit, 'volume': trade.volume,
            'status': trade.status, 'outcome': trade.outcome, 'pnl': trade.pnl,
            'openedAt': trade.opened_at, 'exitPrice': trade.exit_price, 'closedAt': trade.closed_at,
            'closeReason': trade.close_reason, 'costs': trade.costs}


def replay_metrics(session):
    trades = list(session.trades.filter(status='CLOSED').order_by('closed_at', 'id'))
    pnls = [float(trade.pnl) for trade in trades]
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl < 0]
    equity = peak = max_drawdown = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    gross_loss = abs(sum(losses))
    return {
        'trades': len(trades), 'wins': len(wins), 'losses': len(losses),
        'winRate': round(len(wins) / len(trades), 4) if trades else 0,
        'netPnl': round(sum(pnls), 2),
        'expectancy': round(sum(pnls) / len(trades), 2) if trades else 0,
        'profitFactor': round(sum(wins) / gross_loss, 4) if gross_loss else None,
        'maxDrawdown': round(max_drawdown, 2),
        'ruleOnly': {'trades': len(trades), 'netPnl': round(sum(pnls), 2)},
        'rulePlusMl': {'trades': 0, 'netPnl': 0.0, 'note': 'ML comparison requires model-tagged replay decisions.'},
    }


def serialize_decision(decision):
    return {'id': decision.id, 'cursor': decision.cursor, 'candleTime': decision.candle_time,
            'snapshot': decision.snapshot, 'regime': decision.regime, 'analysis': decision.analysis,
            'signal': decision.signal, 'decisionState': decision.decision_state,
            'createdAt': decision.created_at.isoformat()}


@transaction.atomic
def create_replay(*, user, account, timeframe, candle_count, slippage=0.0, commission=0.0,
                  dataset=None, start_time=None, end_time=None):
    if dataset is None:
        bundle = market_data_service.fetch(account, timeframes=REPLAY_TIMEFRAMES, candle_count=candle_count)
        symbol = account.broker_symbol
        for selected_timeframe, candles in bundle.candles.items():
            HistoricalCandle.objects.bulk_create([
                HistoricalCandle(user=user, account=account, symbol=symbol, timeframe=selected_timeframe,
                                 timestamp=candle['time'], open=candle['open'], high=candle['high'],
                                 low=candle['low'], close=candle['close'], volume=candle['volume'])
                for candle in candles
            ], ignore_conflicts=True)
    else:
        symbol = dataset.symbol
        timeframe = dataset.timeframe
        start_time = dataset.start_time if start_time is None else max(start_time, dataset.start_time)
        end_time = dataset.end_time if end_time is None else min(end_time, dataset.end_time)
    probe = HistoricalCandle.objects.filter(user=user, account=account, symbol=symbol, timeframe=timeframe)
    if dataset:
        probe = probe.filter(dataset=dataset)
    if start_time is not None:
        probe = probe.filter(timestamp__gte=start_time)
    if end_time is not None:
        probe = probe.filter(timestamp__lte=end_time)
    count = probe.count()
    if count == 0:
        raise ValueError('The selected dataset has no candles in the requested date range.')
    return ReplaySession.objects.create(user=user, account=account, dataset=dataset, symbol=symbol,
        timeframe=timeframe, start_time=start_time, end_time=end_time, cursor=min(50, count),
        slippage=max(0.0, slippage), commission=max(0.0, commission))


def advance_replay(session, amount=1):
    candles = session_candles(session)
    old_cursor = min(session.cursor, len(candles))
    total = len(candles)
    next_cursor = min(total, max(0, session.cursor + amount))
    for position in range(old_cursor + 1, next_cursor + 1):
        candle = candles[position - 1]
        _settle_open_trades(session, candle, force_close=position >= total)
        session.cursor = position
        record_replay_decision(session, position)
    session.cursor = next_cursor
    session.status = ReplaySession.Status.COMPLETE if session.cursor >= total else ReplaySession.Status.PAUSED
    session.save(update_fields=('cursor', 'status', 'updated_at'))
    return session


def record_replay_decision(session, cursor):
    if ReplayDecision.objects.filter(session=session, cursor=cursor).exists():
        return
    previous_cursor = session.cursor
    session.cursor = cursor
    analysis_payload = replay_analysis(session)
    signal_payload = replay_signals(session)
    analysis = analysis_payload.get('analysis', {})
    candidates = analysis.get('candidates', []) if isinstance(analysis, dict) else []
    decision_state = next((candidate.get('decisionState') for candidate in candidates if candidate.get('decisionState') == 'READY'), None)
    decision_state = decision_state or (candidates[0].get('decisionState') if candidates else 'OBSERVE')
    ReplayDecision.objects.create(
        session=session, cursor=cursor, candle_time=analysis_payload.get('replay', {}).get('currentTime') or 0,
        snapshot=analysis.get('price', {}), regime=analysis.get('regimeContext', {}),
        analysis=analysis, signal=signal_payload, decision_state=decision_state,
    )
    session.cursor = previous_cursor


def _settle_open_trades(session, candle, force_close=False):
    for trade in session.trades.filter(status='OPEN'):
        stop_hit = (trade.direction == 'BUY' and trade.stop_loss is not None and candle['low'] <= trade.stop_loss) or (trade.direction == 'SELL' and trade.stop_loss is not None and candle['high'] >= trade.stop_loss)
        target_hit = (trade.direction == 'BUY' and trade.take_profit is not None and candle['high'] >= trade.take_profit) or (trade.direction == 'SELL' and trade.take_profit is not None and candle['low'] <= trade.take_profit)
        if stop_hit:
            _close_trade(trade, trade.stop_loss, candle['time'], 'STOP_LOSS')
        elif target_hit:
            _close_trade(trade, trade.take_profit, candle['time'], 'TAKE_PROFIT')
        elif force_close:
            _close_trade(trade, candle['close'], candle['time'], 'END_OF_DATA')


def _close_trade(trade, exit_price, closed_at, reason):
    direction_factor = 1 if trade.direction == 'BUY' else -1
    trade.exit_price = float(exit_price)
    trade.closed_at = closed_at
    trade.close_reason = reason
    trade.pnl = (trade.exit_price - trade.entry) * direction_factor * trade.volume - trade.costs
    trade.outcome = 'WIN' if trade.pnl > 0 else 'LOSS' if trade.pnl < 0 else 'BREAKEVEN'
    trade.status = 'CLOSED'
    trade.save(update_fields=('exit_price', 'closed_at', 'close_reason', 'pnl', 'outcome', 'status'))


def replay_analysis(session):
    datasets = {timeframe: session_candles(session, timeframe) for timeframe in REPLAY_TIMEFRAMES}
    current = session_candles(session)
    if not current or session.cursor < 1:
        return {'status': 'INSUFFICIENT_DATA', 'reason': 'Replay has no visible historical candles.'}
    cursor = min(session.cursor, len(current))
    current_candle = current[cursor - 1]
    current_time = current_candle['time']
    visible = {timeframe: [value for value in values if value['time'] <= current_time] for timeframe, values in datasets.items()}
    regime = evaluate_regime(visible['H1'])
    analysis = generate_execution_analysis(
        account=session.account, m5_candles=visible['M5'], m1_candles=visible['M1'],
        current_price_data=_snapshot(session, current_candle), regime_context=regime.as_dict(),
    )
    return {'mode': 'REPLAY', 'replay': serialize_session(session), 'analysis': analysis}


def replay_signals(session):
    payload = replay_analysis(session)
    analysis = payload.get('analysis', {})
    if analysis.get('status') != 'READY':
        return {'mode': 'REPLAY', **payload, 'signal': 'NEUTRAL', 'confidence': 0.0}
    datasets = {timeframe: session_candles(session, timeframe) for timeframe in REPLAY_TIMEFRAMES}
    cursor = min(session.cursor, len(datasets[session.timeframe]))
    current_time = session_candles(session)[min(session.cursor, len(session_candles(session))) - 1]['time']
    visible = {timeframe: [value for value in values if value['time'] <= current_time] for timeframe, values in datasets.items()}
    signals = generate_trade_signals(account=session.account, m5_candles=visible['M5'], m1_candles=visible['M1'],
        current_price_data=analysis.get('price'), regime_context=analysis.get('regimeContext'))
    return {'mode': 'REPLAY', **signals, 'replay': payload['replay']}


def execute_replay_signal(session):
    signals = replay_signals(session)
    direction = signals.get('signal')
    if direction not in {'BUY', 'SELL'}:
        return {'status': 'NOT_EXECUTED', 'reason': 'No actionable signal at the replay cursor.', 'signals': signals}
    candle = session_candles(session)[min(session.cursor, len(session_candles(session))) - 1]
    entry = float(candle['close']) + (session.slippage if direction == 'BUY' else -session.slippage)
    trade = ReplayTrade.objects.create(
        session=session, direction=direction, entry=entry, stop_loss=signals.get('stopLoss'),
        take_profit=signals.get('takeProfit'), opened_at=candle['time'], costs=session.commission,
    )
    return {'status': 'EXECUTED', 'trade': {'id': trade.id, 'direction': trade.direction, 'entry': trade.entry,
        'stopLoss': trade.stop_loss, 'takeProfit': trade.take_profit, 'status': trade.status,
        'pnl': trade.pnl, 'costs': trade.costs, 'openedAt': trade.opened_at}, 'signals': signals}
