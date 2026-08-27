from __future__ import annotations

from dataclasses import dataclass

from backend.stream.event_bus import ScalpEvent, ScalpEventBus


WAITING_FOR_SETUP = 'WAITING_FOR_SETUP'
WAITING_FOR_MSS = 'WAITING_FOR_MSS'
WAITING_FOR_RETRACEMENT = 'WAITING_FOR_RETRACEMENT'
LONG_CANDIDATE = 'LONG_CANDIDATE'
SHORT_CANDIDATE = 'SHORT_CANDIDATE'
RISK_APPROVED = 'RISK_APPROVED'
EXECUTED = 'EXECUTED'
INVALIDATED = 'INVALIDATED'


@dataclass
class ScalpWaitingMechanism:
    symbol: str
    bus: ScalpEventBus
    state: str = WAITING_FOR_SETUP
    _last_signature: tuple | None = None

    def update(self, *, setup: dict, market: dict | None = None) -> dict:
        missing = setup.get('missing', [])
        direction = setup.get('direction', 'LONG')
        if setup.get('invalidated'):
            next_state, waiting_for = INVALIDATED, None
        elif setup.get('executed'):
            next_state, waiting_for = EXECUTED, None
        elif setup.get('risk_approved'):
            next_state, waiting_for = RISK_APPROVED, None
        elif setup.get('active'):
            next_state = LONG_CANDIDATE if direction == 'LONG' else SHORT_CANDIDATE
            waiting_for = None
        elif 'LIQUIDITY_SWEEP' in missing:
            next_state, waiting_for = WAITING_FOR_SETUP, 'LIQUIDITY_SWEEP'
        elif 'MSS' in missing or 'DISPLACEMENT' in missing:
            next_state, waiting_for = WAITING_FOR_MSS, 'MSS'
        else:
            next_state, waiting_for = WAITING_FOR_RETRACEMENT, 'POI_RETRACEMENT'

        signature = (next_state, tuple(missing), direction)
        if signature != self._last_signature:
            event_type = 'SETUP_CONFIRMED' if next_state in {LONG_CANDIDATE, SHORT_CANDIDATE} else 'SETUP_WAITING'
            self.bus.publish(ScalpEvent(
                type=event_type,
                symbol=self.symbol,
                data={
                    'state': next_state,
                    'status': next_state,
                    'waitingFor': waiting_for,
                    'direction': direction,
                    'missing': list(missing),
                },
            ))
            self._last_signature = signature
        self.state = next_state
        result = {'state': self.state, 'waitingFor': waiting_for, 'direction': direction}
        if market:
            result['market'] = market.copy()
        return result

    def publish_market_header(self, *, bid: float, ask: float, spread: float) -> None:
        self.bus.publish(ScalpEvent(
            type='MARKET_UPDATE',
            symbol=self.symbol,
            data={'bid': bid, 'ask': ask, 'spread': spread},
        ))
