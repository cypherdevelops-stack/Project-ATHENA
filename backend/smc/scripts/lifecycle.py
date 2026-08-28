from __future__ import annotations

from datetime import datetime, timezone


POI_STATES = {'DETECTED', 'MONITORING', 'REACTED', 'INVALIDATED', 'EXPIRED'}
_ACTIVE_STATES = {'DETECTED', 'MONITORING', 'REACTED'}


def _age_seconds(poi: dict, current_time: float | int | str | None) -> float | None:
    formation_time = poi.get('time')
    if formation_time is None:
        formation_time = poi.get('formationTimestamp')
    if formation_time is None or current_time is None:
        return None
    try:
        return max(0.0, float(current_time) - float(formation_time))
    except (TypeError, ValueError):
        return None


def enrich_poi(poi: dict, *, current_time: float | int | str | None = None, max_age_seconds: float | None = None) -> dict:
    """Attach auditable lifecycle metadata without changing zone boundaries."""
    state = poi.get('state', 'DETECTED')
    if state not in POI_STATES:
        state = 'DETECTED'
    age_seconds = _age_seconds(poi, current_time)
    expired = max_age_seconds is not None and age_seconds is not None and age_seconds > max_age_seconds
    if expired and state in _ACTIVE_STATES:
        state = 'EXPIRED'
    freshness = poi.get('freshness')
    if freshness is None:
        freshness = 0.0 if age_seconds is None or max_age_seconds in (None, 0) else round(max(0.0, 1.0 - age_seconds / max_age_seconds), 3)
    return {
        **poi,
        'state': state,
        'sourceEvent': poi.get('sourceEvent'),
        'freshness': round(float(freshness), 3),
        'mitigated': bool(poi.get('mitigated', state == 'REACTED')),
        'retestCount': int(poi.get('retestCount', 1 if state == 'REACTED' else 0)),
        'ageSeconds': age_seconds,
        'invalidationReason': poi.get('invalidationReason'),
    }


def advance_poi_state(poi: dict, current_price: float, *, current_time: float | int | str | None = None, max_age_seconds: float | None = None) -> dict:
    """Advance a POI through explicit lifecycle states using current price."""
    enriched = enrich_poi(poi, current_time=current_time, max_age_seconds=max_age_seconds)
    state = enriched['state']
    reason = enriched.get('invalidationReason')
    lower, upper = float(enriched['lowerBound']), float(enriched['upperBound'])
    direction = enriched['direction']
    if state == 'EXPIRED':
        return enriched
    if direction == 'BULLISH':
        if current_price < lower:
            state, reason = 'INVALIDATED', 'PRICE_CLOSED_BELOW_ZONE'
        elif lower <= current_price <= upper:
            state, reason = 'REACTED', None
        elif state in {'DETECTED', 'REACTED'}:
            state, reason = 'MONITORING', None
    else:
        if current_price > upper:
            state, reason = 'INVALIDATED', 'PRICE_CLOSED_ABOVE_ZONE'
        elif lower <= current_price <= upper:
            state, reason = 'REACTED', None
        elif state in {'DETECTED', 'REACTED'}:
            state, reason = 'MONITORING', None
    retest_count = enriched['retestCount'] + (1 if state == 'REACTED' and enriched['state'] != 'REACTED' else 0)
    return {
        **enriched,
        'state': state,
        'mitigated': enriched['mitigated'] or state == 'REACTED',
        'retestCount': retest_count,
        'invalidationReason': reason,
    }

def active_pois(pois: list[dict]) -> list[dict]:
    """Return only POIs eligible for downstream candidate evaluation."""
    return [poi for poi in pois if poi.get('state', 'DETECTED') in _ACTIVE_STATES]
