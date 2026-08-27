from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from backend.stream.event_bus import ScalpEvent, scalp_event_bus


class PaperTradeError(ValueError):
    pass


@dataclass
class PaperPosition:
    position_id: str
    account_id: int
    symbol: str
    direction: str
    entry: float
    stop_loss: float
    take_profit1: float
    take_profit2: float
    volume: float
    state: str = 'ACTIVE'
    opened_at: str = ''
    closed_at: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


_positions: dict[str, PaperPosition] = {}
_positions_lock = RLock()


def _event(position: PaperPosition, event_type: str, **data) -> None:
    scalp_event_bus.publish(ScalpEvent(
        type=event_type,
        symbol=position.symbol,
        data={**position.as_dict(), **data},
    ))


def open_paper_position(*, account, setup: dict, quote: dict) -> dict:
    if setup.get('state') != 'RISK_APPROVED' or not setup.get('direction'):
        raise PaperTradeError('Only a risk-approved setup can open a paper position.')
    account_id = int(account.pk)
    with _positions_lock:
        active = [position for position in _positions.values() if position.account_id == account_id and position.state in {'ACTIVE', 'TP1_HIT'}]
        if active:
            raise PaperTradeError('An active paper position already exists for this account.')
        position = PaperPosition(
            position_id=uuid4().hex,
            account_id=account_id,
            symbol=account.broker_symbol,
            direction=setup['direction'],
            entry=float(setup['entry']),
            stop_loss=float(setup['stopLoss']),
            take_profit1=float(setup['takeProfit1']),
            take_profit2=float(setup['takeProfit2']),
            volume=float(setup['volume']),
            opened_at=datetime.now(timezone.utc).isoformat(),
        )
        _positions[position.position_id] = position
    _event(position, 'POSITION_ACTIVE', bid=quote.get('bid'), ask=quote.get('ask'))
    return position.as_dict()


def update_paper_positions(*, account_id: int, quote: dict) -> list[dict]:
    changed = []
    bid, ask = float(quote['bid']), float(quote['ask'])
    with _positions_lock:
        positions = [position for position in _positions.values() if position.account_id == account_id and position.state in {'ACTIVE', 'TP1_HIT'}]
        for position in positions:
            price = bid if position.direction == 'BUY' else ask
            stop_hit = price <= position.stop_loss if position.direction == 'BUY' else price >= position.stop_loss
            target1_hit = price >= position.take_profit1 if position.direction == 'BUY' else price <= position.take_profit1
            target2_hit = price >= position.take_profit2 if position.direction == 'BUY' else price <= position.take_profit2
            if stop_hit:
                position.state = 'STOP_HIT'
                position.closed_at = datetime.now(timezone.utc).isoformat()
                event_type = 'STOP_HIT'
            elif target2_hit:
                position.state = 'TP2_HIT'
                position.closed_at = datetime.now(timezone.utc).isoformat()
                event_type = 'TP2_HIT'
            elif target1_hit and position.state == 'ACTIVE':
                position.state = 'TP1_HIT'
                event_type = 'TP1_HIT'
            else:
                continue
            changed.append(position.as_dict())
            _event(position, event_type, price=price)
    return changed


def list_paper_positions(*, account_id: int | None = None) -> list[dict]:
    with _positions_lock:
        positions = list(_positions.values())
    if account_id is not None:
        positions = [position for position in positions if position.account_id == account_id]
    return [position.as_dict() for position in positions]


def clear_paper_positions() -> None:
    with _positions_lock:
        _positions.clear()


def build_paper_trade(account) -> dict:
    discovery = account.market_discovery or {}
    if not account.enabled:
        raise PaperTradeError('Account is disabled.')
    if account.canonical_asset != 'XAUUSD' or (account.allowed_instruments and 'XAUUSD' not in account.allowed_instruments):
        raise PaperTradeError('XAUUSD is outside the account policy.')
    if not account.broker_symbol:
        raise PaperTradeError('No broker symbol was discovered for XAUUSD.')

    capability = next(
        (item for item in discovery.get('symbols', []) if item.get('name') == account.broker_symbol),
        None,
    )
    if not capability or capability.get('tradeMode') in (None, 0):
        raise PaperTradeError('The discovered broker symbol is not executable.')
    if not capability.get('selectedFillingMode'):
        raise PaperTradeError('No permitted filling mode was discovered.')

    entry = float(capability.get('ask') or capability.get('bid') or 2350)
    digits = int(capability.get('digits') or 2)
    stop_distance = max(float(capability.get('stopsLevel') or 0) * float(capability.get('point') or 0), 5 * 10 ** -digits)
    direction = 'BUY' if account.pk % 2 == 0 else 'SELL'
    stop_loss = entry - stop_distance if direction == 'BUY' else entry + stop_distance
    take_profit = entry + stop_distance * 2 if direction == 'BUY' else entry - stop_distance * 2
    risk_amount = 100000 * (float(account.risk_per_trade) / 100)

    return {
        'accountId': account.pk,
        'accountName': account.display_name,
        'canonicalAsset': account.canonical_asset,
        'brokerSymbol': account.broker_symbol,
        'direction': direction,
        'entry': round(entry, digits),
        'stopLoss': round(stop_loss, digits),
        'takeProfit': round(take_profit, digits),
        'riskAmount': risk_amount,
        'volume': float(capability.get('volumeMin') or 0.01),
        'fillingMode': capability['selectedFillingMode'],
        'status': 'SIMULATED / NOT SENT TO MT5',
    }
