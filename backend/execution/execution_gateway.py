from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Any


class ExecutionGatewayError(ValueError):
    pass


def normalize_price(price: float, capability: dict[str, Any]) -> float:
    """Normalize a price to broker digits and, when supplied, tick size."""
    digits = int(capability.get('digits') or 2)
    requested = Decimal(str(price))
    tick_size = Decimal(str(capability.get('tickSize') or 0))
    if requested <= 0:
        raise ExecutionGatewayError('Price must be greater than zero.')
    if tick_size > 0:
        requested = (requested / tick_size).to_integral_value(rounding=ROUND_HALF_UP) * tick_size
    return float(round(requested, digits))


def normalize_volume(volume: float, capability: dict[str, Any]) -> float:
    minimum = Decimal(str(capability.get('volumeMin') or 0))
    maximum = Decimal(str(capability.get('volumeMax') or volume))
    step = Decimal(str(capability.get('volumeStep') or minimum or 0))
    requested = Decimal(str(volume))
    if requested <= 0 or minimum <= 0 or step <= 0:
        raise ExecutionGatewayError('Broker volume limits are unavailable.')
    normalized = (requested / step).to_integral_value(rounding=ROUND_DOWN) * step
    if normalized < minimum:
        raise ExecutionGatewayError('Volume is below the broker minimum.')
    if normalized > maximum:
        normalized = (maximum / step).to_integral_value(rounding=ROUND_DOWN) * step
    if normalized < minimum:
        raise ExecutionGatewayError('Broker maximum volume is below its minimum.')
    return float(normalized)


def validate_broker_setup(*, setup: dict[str, Any], capability: dict[str, Any], market_price: float) -> dict[str, Any]:
    """Validate and normalize one setup against discovered broker capabilities."""
    if not capability.get('visible', True) or not capability.get('selectable', True):
        raise ExecutionGatewayError('Broker symbol is not visible or selectable.')
    if capability.get('tradeMode') in (None, 0):
        raise ExecutionGatewayError('Broker symbol is not tradeable.')
    order_modes = capability.get('orderModes')
    market_order_mode = capability.get('marketOrderMode', 1)
    if order_modes is not None and not int(order_modes) & int(market_order_mode):
        raise ExecutionGatewayError('Broker symbol does not allow market orders.')
    if not capability.get('selectedFillingMode'):
        raise ExecutionGatewayError('No permitted broker filling mode was discovered.')
    if market_price <= 0:
        raise ExecutionGatewayError('Current broker price is unavailable.')

    direction = setup.get('direction')
    if direction not in {'BUY', 'SELL'}:
        raise ExecutionGatewayError('Trade direction is invalid.')
    entry = float(setup.get('entry') or 0)
    stop_loss = float(setup.get('stopLoss') or 0)
    take_profit2 = float(setup.get('takeProfit2') or 0)
    if min(entry, stop_loss, take_profit2) <= 0:
        raise ExecutionGatewayError('Entry, stop loss, and take profit must be positive.')

    digits = int(capability.get('digits') or 2)
    point = float(capability.get('point') or 0)
    minimum_stop_distance = max(
        float(capability.get('stopsLevel') or 0),
        float(capability.get('freezeLevel') or 0),
    ) * point
    if direction == 'BUY':
        stop_distance = market_price - stop_loss
        target_distance = take_profit2 - market_price
    else:
        stop_distance = stop_loss - market_price
        target_distance = market_price - take_profit2
    if stop_distance < minimum_stop_distance or target_distance < minimum_stop_distance:
        raise ExecutionGatewayError('Stop loss or take profit violates the broker minimum distance.')

    return {
        **setup,
        'entry': normalize_price(entry, capability),
        'stopLoss': normalize_price(stop_loss, capability),
        'takeProfit2': normalize_price(take_profit2, capability),
        'volume': normalize_volume(float(setup.get('volume') or 0), capability),
        'fillingMode': capability['selectedFillingMode'],
        'fillingModeValue': capability.get('selectedFillingModeValue'),
    }
