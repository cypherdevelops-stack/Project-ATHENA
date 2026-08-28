from __future__ import annotations

import json
import os


DEFAULT_RELATIONSHIPS = {
    'XAUUSD': {'USD': -1.0, 'XAU': 1.0},
    'EURUSD': {'EUR': 1.0, 'USD': -1.0},
    'GBPUSD': {'GBP': 1.0, 'USD': -1.0},
    'USDJPY': {'USD': 1.0, 'JPY': -1.0},
    'USDCAD': {'USD': 1.0, 'CAD': -1.0},
    'AUDUSD': {'AUD': 1.0, 'USD': -1.0},
    'NZDUSD': {'NZD': 1.0, 'USD': -1.0},
    'USDCHF': {'USD': 1.0, 'CHF': -1.0},
    'USOIL': {'OIL': 1.0, 'CAD': 0.3, 'USD': -0.1},
    'SPX500': {'USD': 0.2, 'RISK': 1.0},
    'BTCUSD': {'BTC': 1.0, 'USD': -1.0, 'RISK': 0.5},
}


def relationship_map(overrides: dict | None = None) -> dict[str, dict[str, float]]:
    result = {symbol: values.copy() for symbol, values in DEFAULT_RELATIONSHIPS.items()}
    result.update({str(symbol).upper(): {str(entity).upper(): float(weight) for entity, weight in values.items()} for symbol, values in (overrides or {}).items()})
    configured = os.getenv('ATHENA_NEWS_RELATIONSHIPS_JSON')
    if configured:
        try:
            payload = json.loads(configured)
            if isinstance(payload, dict):
                result.update({str(symbol).upper(): {str(entity).upper(): float(weight) for entity, weight in values.items()} for symbol, values in payload.items()})
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return result