from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from django.db.models import Q
from django.utils import timezone

from backend.accounts.credentials import decrypt_password
from backend.accounts.handshake import DEFAULT_MT5_TERMINAL_PATH
from backend.execution.lifecycle_events import publish_lifecycle_event
from backend.execution.models import BrokerPositionSnapshot, LiveExecutionAttempt


class ReconciliationError(ValueError):
    pass


def reconcile_live_positions(*, account, mt5_module=None) -> dict:
    """Compare broker positions with ATHENA attempts and fail closed on uncertainty."""
    if mt5_module is None:
        try:
            import MetaTrader5 as mt5_module
        except ImportError as error:
            return _failed(account, f'MetaTrader5 package import failed: {error}')

    initialized = bool(mt5_module.initialize(path=account.terminal_path or DEFAULT_MT5_TERMINAL_PATH))
    if not initialized:
        return _failed(account, f'MT5 initialization failed: {mt5_module.last_error()}')
    try:
        if not mt5_module.login(login=int(account.login), password=decrypt_password(account.password_encrypted), server=account.server):
            return _failed(account, f'MT5 login failed: {mt5_module.last_error()}')
        positions = mt5_module.positions_get(symbol=account.broker_symbol)
        if positions is None:
            return _failed(account, 'MT5 position query failed.')

        broker_positions = [_position_payload(position, account.broker_symbol) for position in positions]
        broker_tickets = {item['ticket'] for item in broker_positions}
        attempts = LiveExecutionAttempt.objects.filter(
            account=account,
            status='ACCEPTED',
        ).filter(Q(order_ticket__isnull=False) | Q(deal_ticket__isnull=False))
        missing = [
            attempt for attempt in attempts
            if attempt.order_ticket not in broker_tickets and attempt.deal_ticket not in broker_tickets
            and not BrokerPositionSnapshot.objects.filter(
                account=account,
                decision_id=attempt.decision_id,
                state='CLOSED',
            ).exists()
        ]
        snapshots = {item.ticket: item for item in BrokerPositionSnapshot.objects.filter(account=account)}
        now = timezone.now()
        account.reconciliation_safe = not missing
        account.last_reconciliation_at = now
        account.save(update_fields=['reconciliation_safe', 'last_reconciliation_at', 'updated_at'])
        for position in broker_positions:
            previous = snapshots.get(position['ticket'])
            state = 'ACTIVE'
            event_type = 'POSITION_ACTIVE'
            changed = previous and any(Decimal(str(getattr(previous, field))) != Decimal(str(position[key])) for field, key in (
                ('volume', 'volume'), ('price_open', 'priceOpen'), ('stop_loss', 'stopLoss'), ('take_profit', 'takeProfit')
            ))
            if changed:
                state = 'MODIFIED'
                event_type = 'POSITION_MODIFIED'
            snapshot, _ = BrokerPositionSnapshot.objects.update_or_create(
                account=account,
                ticket=position['ticket'],
                defaults={
                    'decision_id': _decision_for_ticket(attempts, position['ticket']),
                    'symbol': position['symbol'],
                    'direction': position['direction'],
                    'volume': position['volume'],
                    'price_open': position['priceOpen'],
                    'stop_loss': position['stopLoss'],
                    'take_profit': position['takeProfit'],
                    'state': state,
                    'observed_at': now,
                    'closed_at': None,
                },
            )
            publish_lifecycle_event(
                account=account,
                decision_id=snapshot.decision_id or uuid4(),
                event_type=event_type,
                state=state,
                symbol=position['symbol'],
                payload=position,
            )
        for previous in snapshots.values():
            if previous.state in {'ACTIVE', 'MODIFIED', 'PARTIALLY_FILLED'} and previous.ticket not in broker_tickets:
                previous.state = 'CLOSED'
                previous.closed_at = now
                previous.observed_at = now
                previous.save(update_fields=['state', 'closed_at', 'observed_at'])
                publish_lifecycle_event(
                    account=account,
                    decision_id=previous.decision_id or uuid4(),
                    event_type='POSITION_CLOSED',
                    state='CLOSED',
                    symbol=previous.symbol,
                    payload={'ticket': previous.ticket},
                )
        for attempt in missing:
            publish_lifecycle_event(
                account=account,
                decision_id=attempt.decision_id,
                event_type='RECONCILIATION_REQUIRED',
                state='RECONCILIATION_REQUIRED',
                symbol=account.broker_symbol,
                payload={'order': attempt.order_ticket, 'deal': attempt.deal_ticket},
            )
        return {'status': 'SAFE' if not missing else 'UNSAFE', 'positions': broker_positions, 'missingAttempts': len(missing)}
    finally:
        mt5_module.shutdown()


def _position_payload(position, symbol: str) -> dict:
    return {
        'ticket': int(getattr(position, 'ticket', 0)),
        'symbol': str(getattr(position, 'symbol', symbol)),
        'direction': 'BUY' if getattr(position, 'type', 0) == 0 else 'SELL',
        'volume': float(getattr(position, 'volume', 0) or 0),
        'priceOpen': float(getattr(position, 'price_open', 0) or 0),
        'stopLoss': float(getattr(position, 'sl', 0) or 0),
        'takeProfit': float(getattr(position, 'tp', 0) or 0),
    }


def _decision_for_ticket(attempts, ticket: int):
    for attempt in attempts:
        if attempt.order_ticket == ticket or attempt.deal_ticket == ticket:
            return attempt.decision_id
    return attempts.first().decision_id if attempts.exists() else uuid4()


def _failed(account, reason: str) -> dict:
    account.reconciliation_safe = False
    account.save(update_fields=['reconciliation_safe', 'updated_at'])
    decision_id = uuid4()
    publish_lifecycle_event(
        account=account,
        decision_id=decision_id,
        event_type='RECONCILIATION_FAILED',
        state='RECONCILIATION_REQUIRED',
        symbol=account.broker_symbol,
        payload={'reason': reason},
    )
    publish_lifecycle_event(
        account=account,
        decision_id=decision_id,
        event_type='LIVE_EXECUTION_HALTED',
        state='RECONCILIATION_REQUIRED',
        symbol=account.broker_symbol,
        payload={'reason': reason},
    )
    return {'status': 'UNSAFE', 'reason': reason}