from __future__ import annotations

from .gates import detect_scalping_setup, evaluate_gates
from backend.execution.xgboost_engine import XGBoostEngine
from backend.smc.detector import detect_entry_confirmation
from backend.smc.context_service import build_smc_context, extract_smc_evidence
from backend.market.momentum import momentum_evidence


def _in_zone(price: float, item: dict) -> bool:
    return item['lowerBound'] <= price <= item['upperBound']


def _score_setup(*, direction: str, aligned: bool, in_zone: bool, has_structure_event: bool, has_confluence: bool, context: dict | None) -> tuple[int, dict[str, int]]:
    context = context or {}
    liquidity_sweep = context.get('liquidity_sweep', context.get('sell_side_liquidity_swept', has_structure_event))
    structure_confirmed = context.get('structure_confirmed', context.get('bullish_mss', context.get('bearish_mss', has_structure_event)))
    displacement = context.get('displacement', context.get('bullish_displacement', context.get('bearish_displacement', has_structure_event)))
    momentum_confirmed = context.get('momentum_confirmed', context.get('bullish_mss', context.get('bearish_mss', has_structure_event)))
    fresh_poi = context.get('fresh_poi', context.get('fresh_bullish_poi', context.get('fresh_bearish_poi', in_zone)))
    momentum = momentum_evidence(context.get('momentumMap'), direction) if context.get('momentumMap') else {
        'points': 5 if momentum_confirmed else 0,
        'alignment': 'LEGACY',
        'reason': 'Momentum confirmation is supplied by the existing setup evidence.',
    }
    components = {
        'htfBias': 15 if context.get('htf_bias', 'UNKNOWN') in {'BUY', 'SELL'} else (15 if not context else 0),
        'liquiditySetup': 15 if liquidity_sweep else 0,
        'sessionAlignment': 10 if context.get('session_aligned', True) else 0,
        'structureConfirmation': 15 if structure_confirmed else 0,
        'displacement': 15 if displacement else 0,
        'freshPoi': 10 if in_zone or fresh_poi else 0,
        'poiConfluence': 10 if has_confluence else 0,
        'correlationAlignment': 5 if context.get('correlation_allowed', True) else 0,
        'momentum': round(momentum['points']),
    }
    return sum(components.values()), components


def generate_scalping_candidates(*, account, broker_symbol: str, current_price: float, m1_features: dict, m5_features: dict, context: dict | None = None, ml_engine: XGBoostEngine | None = None, m1_candles: list[dict] | None = None, m5_candles: list[dict] | None = None) -> list[dict]:
    candidates = []
    higher_structure = m5_features.get('structure', 'UNKNOWN')
    lower_structure = m1_features.get('structure', 'UNKNOWN')
    context = context or {}
    if m1_candles and 'smcEvidence' not in context:
        smc_context = build_smc_context(
            candles_by_timeframe={'M5': m5_candles or [], 'M1': m1_candles},
            current_price=current_price,
            timeframes=('M5', 'M1'),
        )
        context = {
            **extract_smc_evidence(
                smc_context,
                primary_timeframe='M1',
                secondary_timeframe='M5',
                higher_timeframe='M5',
            ),
            **context,
            'smcEvidence': smc_context,
        }
    smc_evidence = context.get('smcEvidence', {})
    active_smc_pois = {
        (poi.get('type'), poi.get('time'))
        for poi in smc_evidence.get('timeframes', {}).get('M1', {}).get('activePois', [])
    }
    hard_gate_codes = []
    if not account.enabled or not account.terminal_connected or not account.trade_allowed:
        hard_gate_codes.append('ACCOUNT_TRADE_NOT_ALLOWED')
    hard_gates = {
        'NEWS_LOCK': context.get('news_locked', False),
        'SPREAD_TOO_HIGH': context.get('spread_ok', True) is False,
        'MARKET_CLOSED': context.get('market_open', True) is False,
        'CORRELATION_EXPOSURE_EXCEEDED': context.get('correlation_allowed', True) is False,
        'EXECUTION_UNAVAILABLE': context.get('execution_allowed', True) is False,
    }
    hard_gate_codes.extend(code for code, active in hard_gates.items() if active)
    risk_allowed = not hard_gate_codes
    points_of_interest = [
        poi for poi in (m1_features.get('orderBlocks', []) + m1_features.get('fairValueGaps', []))
        if not active_smc_pois or (poi.get('type'), poi.get('time')) in active_smc_pois
    ]
    has_structure_event = bool(m1_features.get('events'))

    for index, poi in enumerate(points_of_interest):
        direction = poi['direction']
        aligned = (direction == 'BULLISH' and higher_structure == 'BULLISH') or (direction == 'BEARISH' and higher_structure == 'BEARISH')
        regime_bias = context.get('htf_bias')
        bias_aligned = (direction == 'BULLISH' and regime_bias == 'BUY') or (direction == 'BEARISH' and regime_bias == 'SELL')
        in_zone = _in_zone(current_price, poi)
        score, score_components = _score_setup(
            direction=direction,
            aligned=aligned,
            in_zone=in_zone,
            has_structure_event=has_structure_event,
            has_confluence=len(points_of_interest) > 1,
            context=context,
        )
        setup_context_present = any(key in context for key in {
            'htf_bias', 'price_approaches_liquidity', 'sell_side_liquidity_swept', 'buy_side_liquidity_swept',
            'bullish_displacement', 'bearish_displacement', 'bullish_mss', 'bearish_mss',
            'fresh_bullish_poi', 'fresh_bearish_poi', 'price_returns_to_poi', 'entry_confirmation',
            'liquidity_sweep', 'displacement', 'mss_confirmed', 'fresh_poi', 'poi_retest',
        })
        confirmation = detect_entry_confirmation(candles=m1_candles, poi=poi, direction='BUY' if direction == 'BULLISH' else 'SELL') if m1_candles else {'entry_confirmation': bool(context.get('entry_confirmation', False))}
        setup_context = {
            **context,
            **confirmation,
            'fresh_bullish_poi': poi.get('state', 'DETECTED') != 'INVALIDATED' if direction == 'BULLISH' else context.get('fresh_bullish_poi', False),
            'fresh_bearish_poi': poi.get('state', 'DETECTED') != 'INVALIDATED' if direction == 'BEARISH' else context.get('fresh_bearish_poi', False),
        }
        setup = detect_scalping_setup(
            direction=direction,
            current_price=current_price,
            poi=poi,
            context={**setup_context, 'higher_structure': higher_structure, 'm5_structure': higher_structure},
            higher_structure=higher_structure,
        )
        gate_results = evaluate_gates(account=account, direction=direction, higher_structure=higher_structure, context=context)
        blocked_gates = [gate for gate in gate_results if gate.status == 'BLOCK']
        reason_codes = list(hard_gate_codes)
        reason_codes.extend(gate.name for gate in blocked_gates if gate.name not in reason_codes)
        state = 'READY'
        if blocked_gates:
            state = 'BLOCKED'
        elif any(gate.status != 'PASS' for gate in gate_results):
            state = 'OBSERVE'
            reason_codes.extend(f'GATE_{gate.status}' for gate in gate_results if gate.status != 'PASS')
        elif context and score < 60:
            state = 'OBSERVE'
            reason_codes.append('SCALP_SCORE_BELOW_THRESHOLD')
        elif not setup['active']:
            state = 'OBSERVE'
            reason_codes.append('SETUP_SEQUENCE_INCOMPLETE')
            reason_codes.extend(f"SETUP_{step}" for step in setup['missing'])
        elif context.get('htf_bias') in {'BUY', 'SELL'} and not bias_aligned:
            state = 'OBSERVE'
            reason_codes.append('HTF_BIAS_NOT_ALIGNED')
        elif higher_structure == 'UNKNOWN' or lower_structure == 'UNKNOWN':
            state = 'OBSERVE'
            reason_codes.append('INSUFFICIENT_STRUCTURE')
        elif not aligned:
            state = 'OBSERVE'
            reason_codes.append('HTF_LTF_DIRECTION_NOT_ALIGNED')
        elif not in_zone:
            state = 'OBSERVE'
            reason_codes.append('PRICE_NOT_IN_POI_ZONE')
        elif setup_context_present:
            reason_codes.append('SETUP_SEQUENCE_COMPLETE')
        if not aligned and 'HTF_LTF_DIRECTION_NOT_ALIGNED' not in reason_codes:
            reason_codes.append('HTF_LTF_DIRECTION_NOT_ALIGNED')
        candidates.append({
            'candidateId': f'{broker_symbol}:{m1_features.get("timeframe", "M1")}:{poi["type"]}:{poi["time"]}:{index}',
            'asset': 'XAUUSD',
            'brokerSymbol': broker_symbol,
            'module': 'SCALPING',
            'direction': 'BUY' if direction == 'BULLISH' else 'SELL',
            'poiType': poi['type'],
            'entryZone': {'lower': poi['lowerBound'], 'upper': poi['upperBound']},
            'regimeContext': higher_structure,
            'decisionState': state,
            'riskEligibility': risk_allowed,
            'reasonCodes': reason_codes,
            'currentPrice': current_price,
            'timeframe': m1_features.get('timeframe', 'M1'),
            'poiTime': poi.get('time'),
            'strength': poi.get('strength', 0),
            'score': score,
            'scoreComponents': score_components,
            'gates': [gate.as_dict() for gate in gate_results],
            'setup': setup,
            'confirmation': confirmation,
            'smcEvidence': smc_evidence,
            'momentumEvidence': momentum_evidence(context.get('momentumMap'), direction) if context.get('momentumMap') else None,
        })
        if ml_engine is not None:
            candidates[-1]['mlPrediction'] = ml_engine.predict(candidate=candidates[-1], context={**context, 'm1_structure': lower_structure})

    if candidates:
        return candidates
    return [{
        'candidateId': f'{broker_symbol}:SCALPING:NO_CANDIDATE',
        'asset': 'XAUUSD',
        'brokerSymbol': broker_symbol,
        'module': 'SCALPING',
        'direction': None,
        'poiType': None,
        'entryZone': None,
        'regimeContext': higher_structure,
        'decisionState': 'OBSERVE',
        'riskEligibility': risk_allowed,
        'reasonCodes': ['NO_ACTIVE_POI'],
        'currentPrice': current_price,
        'timeframe': m1_features.get('timeframe', 'M1'),
        'strength': 0,
        'score': 0,
        'scoreComponents': {},
        'gates': [],
    }]


def build_decision_stream(*, candidates: list[dict], m1_features: dict, m5_features: dict, current_price: float, waiting_mechanism=None, market: dict | None = None) -> dict:
    why_trade = []
    why_not = []
    gates = candidates[0].get('gates', []) if candidates else []
    why_trade.extend({'code': gate['name'], 'message': gate['reason']} for gate in gates if gate['status'] == 'PASS')
    why_not.extend({'code': gate['name'], 'message': gate['reason']} for gate in gates if gate['status'] == 'BLOCK')
    if m5_features.get('structure') in {'BULLISH', 'BEARISH'}:
        why_trade.append({'code': 'HTF_STRUCTURE_DEFINED', 'message': f"M5 structure is {m5_features['structure']}."})
    else:
        why_not.append({'code': 'INSUFFICIENT_STRUCTURE', 'message': 'M5 structure is not defined.'})
    if m1_features.get('events'):
        why_trade.append({'code': 'LTF_STRUCTURE_EVENT', 'message': 'M1 structure event detected.'})
    else:
        why_not.append({'code': 'NO_LTF_CONFIRMATION', 'message': 'No M1 break or change of character is confirmed.'})
    ready = [candidate for candidate in candidates if candidate['decisionState'] == 'READY']
    blocked = [candidate for candidate in candidates if candidate['decisionState'] == 'BLOCKED']
    waiting_state = None
    if waiting_mechanism and candidates:
        waiting_state = waiting_mechanism.update(setup=candidates[0].get('setup', {}), market=market)
    best_score = max((candidate.get('score', 0) for candidate in candidates), default=0)
    if best_score:
        (why_trade if best_score >= 60 else why_not).append({
            'code': 'SCALP_SCORE',
            'message': f'Best context-driven scalp score is {best_score}/100.',
        })
    if ready:
        why_trade.append({'code': 'POI_ENTRY_ZONE_ACTIVE', 'message': f'{len(ready)} candidate zone(s) are active at the current price.'})
    else:
        why_not.append({'code': 'NO_READY_CANDIDATE', 'message': 'No candidate passed all scalping gates.'})
    known_codes = {item['code'] for item in why_trade + why_not}
    why_not.extend({'code': code, 'message': code.replace('_', ' ').title()} for candidate in candidates for code in candidate['reasonCodes'] if code not in known_codes)
    return {
        'events': [
            {'timestamp': m5_features.get('latestTime'), 'type': 'ANALYSIS', 'message': f"M5 structure = {m5_features.get('structure', 'UNKNOWN')}"},
            {'timestamp': m1_features.get('latestTime'), 'type': 'ANALYSIS', 'message': f"M1 structure = {m1_features.get('structure', 'UNKNOWN')}"},
            {'timestamp': None, 'type': 'SYSTEM', 'message': f'Current price = {current_price}.'},
            {'timestamp': None, 'type': 'DECISION', 'message': f'{len(ready)} ready, {len(blocked)} blocked, {len(candidates) - len(ready) - len(blocked)} observe.'},
        ],
        'whyTrade': why_trade,
        'whyNot': why_not,
        'gates': gates,
        'setupState': waiting_state,
    }
