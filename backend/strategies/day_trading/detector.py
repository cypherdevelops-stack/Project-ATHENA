from __future__ import annotations

from backend.smc.detector import detect_entry_confirmation
from backend.execution.xgboost_engine import XGBoostEngine


def _detect_pullback_structure(m15_candles: list[dict], h1_candles: list[dict],
                               direction: str, current_price: float,
                               m15_features: dict | None = None) -> dict:
    """
    Detect pullback structure for day trading.
    
    Day trading operates on: H4/H1 → M15/M5 → pullback → execution
    
    This detects:
    - HTF bias (from H1)
    - M15 pullback confirmation
    - Entry zone for pullback retest
    """
    if not m15_candles or not h1_candles:
        return {
            'pullback_detected': False,
            'pullback_depth': 0,
            'entry_zone': None,
            'state': 'INSUFFICIENT_DATA',
        }

    m15_features = m15_features or {}
    points_of_interest = m15_features.get('orderBlocks', []) + m15_features.get('fairValueGaps', [])
    valid_pois = [poi for poi in points_of_interest if poi.get('state', 'DETECTED') != 'INVALIDATED']
    h1_close = h1_candles[-1]['close']
    h1_high = max(c['high'] for c in h1_candles[-20:])
    h1_low = min(c['low'] for c in h1_candles[-20:])

    m15_recent_high = max(c['high'] for c in m15_candles[-10:])
    m15_recent_low = min(c['low'] for c in m15_candles[-10:])

    pullback_detected = False
    entry_zone = None
    selected_poi = None

    if direction == 'BUY':
        # Bullish pullback: expects retracement to HTF support
        bullish_pois = [poi for poi in valid_pois if poi.get('direction') == 'BULLISH']
        selected_poi = min(bullish_pois, key=lambda poi: abs(current_price - ((poi['lowerBound'] + poi['upperBound']) / 2))) if bullish_pois else None
        if h1_close < h1_high and m15_recent_low < m15_recent_high and selected_poi:
            pullback_detected = True
            pullback_depth = ((h1_high - h1_close) / h1_high * 100) if h1_high > 0 else 0
            entry_zone = {'lower': float(selected_poi['lowerBound']), 'upper': float(selected_poi['upperBound'])}
    elif direction == 'SELL':
        # Bearish pullback: expects retracement to HTF resistance
        bearish_pois = [poi for poi in valid_pois if poi.get('direction') == 'BEARISH']
        selected_poi = min(bearish_pois, key=lambda poi: abs(current_price - ((poi['lowerBound'] + poi['upperBound']) / 2))) if bearish_pois else None
        if h1_close > h1_low and m15_recent_low < m15_recent_high and selected_poi:
            pullback_detected = True
            pullback_depth = ((h1_close - h1_low) / h1_low * 100) if h1_low > 0 else 0
            entry_zone = {'lower': float(selected_poi['lowerBound']), 'upper': float(selected_poi['upperBound'])}

    return {
        'pullback_detected': pullback_detected,
        'pullback_depth': pullback_depth if pullback_detected else 0,
        'entry_zone': entry_zone,
        'poi': selected_poi,
        'state': 'PULLBACK_DETECTED' if pullback_detected else 'AWAITING_PULLBACK',
    }


def _score_day_trade_setup(*, htf_bias: str, pullback_detected: bool, 
                            poi_confirmation: bool, m15_alignment: bool,
                            context: dict | None = None) -> tuple[int, dict[str, int]]:
    """
    Score a day trading setup (0-100 scale).
    
    Simpler than scalping: fewer components, longer horizon.
    """
    context = context or {}
    components = {
        'htfBias': 40 if htf_bias in {'BUY', 'SELL'} else 0,
        'pullbackConfirmed': 30 if pullback_detected else 0,
        'poiConfirmation': 15 if poi_confirmation else 0,
        'm15Alignment': 10 if m15_alignment else 0,
        'correlationAllowed': 5 if context.get('correlation_allowed', True) else 0,
    }
    return sum(components.values()), components


def generate_day_trading_candidates(*, account, broker_symbol: str, current_price: float,
                                     m15_features: dict, h1_features: dict, h4_features: dict,
                                     context: dict | None = None, 
                                     ml_engine: XGBoostEngine | None = None,
                                     m15_candles: list[dict] | None = None,
                                     h1_candles: list[dict] | None = None) -> list[dict]:
    """
    Generate day trading candidates.
    
    Day trading strategy:
    - H4/H1 provides directional bias (trend identification)
    - M15/M5 provides structure and pullback entry
    - Longer hold time (hours instead of minutes)
    - Higher minimum R:R ratio
    
    Returns list of candidates in the same format as scalping for compatibility
    with the orchestrator.
    """
    candidates = []
    context = context or {}

    # Account-level gating
    hard_gate_codes = []
    if not account.enabled or not account.terminal_connected or not account.trade_allowed:
        hard_gate_codes.append('ACCOUNT_TRADE_NOT_ALLOWED')

    hard_gates = {
        'NEWS_LOCK': context.get('news_locked', False),
        'MARKET_CLOSED': context.get('market_open', True) is False,
        'CORRELATION_EXPOSURE_EXCEEDED': context.get('correlation_allowed', True) is False,
        'MARKET_DATA_UNVERIFIED': context.get('execution_allowed', True) is False,
    }
    hard_gate_codes.extend(code for code, active in hard_gates.items() if active)
    risk_allowed = not hard_gate_codes

    # Day trading only trades with identified HTF bias
    h1_structure = h1_features.get('structure', 'UNKNOWN')
    h4_structure = h4_features.get('structure', 'UNKNOWN') if h4_features else 'UNKNOWN'

    for direction in ['BULLISH', 'BEARISH']:
        dir_code = 'BUY' if direction == 'BULLISH' else 'SELL'

        # HTF bias alignment
        htf_aligned = (
            (direction == 'BULLISH' and h1_structure == 'BULLISH' and h4_structure in {'UNKNOWN', 'BULLISH'}) or
            (direction == 'BEARISH' and h1_structure == 'BEARISH' and h4_structure in {'UNKNOWN', 'BEARISH'})
        )

        if not htf_aligned:
            continue  # Skip if not aligned with HTF

        # Detect pullback on M15
        pullback_info = _detect_pullback_structure(m15_candles or [], h1_candles or [], dir_code, current_price, m15_features)
        pullback_detected = pullback_info.get('pullback_detected', False)
        poi = pullback_info.get('poi')
        m15_structure = m15_features.get('structure', 'UNKNOWN')
        m15_alignment = m15_structure in {'BULLISH', 'BEARISH'} and m15_structure == direction
        confirmation = detect_entry_confirmation(
            candles=m15_candles,
            poi=poi,
            direction=dir_code,
        ) if m15_candles and poi else {'entry_confirmation': False}
        poi_confirmation = poi is not None and poi.get('state', 'DETECTED') != 'INVALIDATED'

        # Score the setup
        score, score_components = _score_day_trade_setup(
            htf_bias=dir_code,
            pullback_detected=pullback_detected,
            poi_confirmation=poi_confirmation,
            m15_alignment=m15_alignment,
            context=context,
        )

        # Determine decision state
        if not risk_allowed:
            decision_state = 'BLOCKED'
        elif pullback_detected and poi_confirmation and m15_alignment and score >= 75:
            decision_state = 'DEVELOPING'  # Day trade setup is forming
        else:
            decision_state = 'OBSERVE'

        entry_zone = pullback_info.get('entry_zone')
        
        candidate = {
            'strategy': 'DAY_TRADING',
            'direction': dir_code,
            'score': score,
            'scoreComponents': score_components,
            'decisionState': decision_state,
            'status': 'DEVELOPING' if decision_state == 'DEVELOPING' else 'OBSERVE',
            'setup_state': pullback_info.get('state', 'AWAITING_PULLBACK'),
            'setup': {
                'active': pullback_detected and poi_confirmation and m15_alignment,
                'state': pullback_info.get('state'),
                'missing': [
                    code for code, present in (
                        ('HTF_ALIGNMENT', htf_aligned),
                        ('M15_PULLBACK', pullback_detected),
                        ('M15_POI', poi_confirmation),
                        ('M15_ALIGNMENT', m15_alignment),
                        ('M15_ENTRY_CONFIRMATION', bool(confirmation.get('entry_confirmation'))),
                    ) if not present
                ],
            },
            'entryZone': entry_zone,
            'gates': [
                {'code': 'NEWS_LOCK', 'passed': not context.get('news_locked', False)},
                {'code': 'MARKET_OPEN', 'passed': context.get('market_open', True)},
                {'code': 'CORRELATION', 'passed': context.get('correlation_allowed', True)},
            ],
            'evidence': {
                'htf_bias': dir_code,
                'h1_structure': h1_structure,
                'pullback_detected': pullback_detected,
                'pullback_depth': pullback_info.get('pullback_depth', 0),
                'h4_structure': h4_structure,
                'm15_structure': m15_structure,
                'poi': poi,
                'entry_confirmation': confirmation.get('entry_confirmation', False),
                'timeframe': 'H4/H1/M15',
            },
            'htf_structure': h1_structure,
            'pullback_detected': pullback_detected,
            'poi_confirmation': poi_confirmation,
            'timeframe': 'M15',
            'poi': poi,
            'reasonCodes': [
                code for code, present in (
                    ('HTF_ALIGNMENT', htf_aligned),
                    ('M15_PULLBACK_DETECTED', pullback_detected),
                    ('M15_POI_CONFIRMED', poi_confirmation),
                    ('M15_STRUCTURE_ALIGNED', m15_alignment),
                    ('M15_ENTRY_CONFIRMED', bool(confirmation.get('entry_confirmation'))),
                ) if present
            ],
        }

        # Only return candidate if it's at least DEVELOPING (not OBSERVE)
        if decision_state in {'DEVELOPING', 'RISK_APPROVED'}:
            candidates.append(candidate)

    return candidates
