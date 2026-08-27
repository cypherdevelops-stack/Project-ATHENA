from __future__ import annotations

from datetime import datetime


def format_market_header(*, symbol: str, bid: float, ask: float, spread: float) -> str:
    return f'{symbol}\nBid {bid:.2f} | Ask {ask:.2f} | Spread {spread:.2f}'


def format_event(event) -> str:
    timestamp = event.timestamp.astimezone().strftime('%H:%M:%S')
    data = event.data
    labels = {
        'REGIME_UPDATE': f"HTF REGIME      {data.get('regime', 'UNKNOWN')}",
        'GATE_RESULT': f"{data.get('gate', 'GATE')} GATE       {data.get('status', 'UNKNOWN')}",
        'LIQUIDITY_APPROACHING': '-> Sell-side liquidity approaching',
        'LIQUIDITY_SWEEP': f"Liquidity swept ({data.get('side', 'UNKNOWN')})",
        'MSS_DETECTED': f"{data.get('direction', 'UNKNOWN')} MSS detected",
        'POI_IDENTIFIED': '-> POI identified',
        'POI_RETEST': '-> Price entering POI',
        'SETUP_WAITING': f"-> {data.get('status', 'WAITING_FOR_SETUP')}: {data.get('waitingFor', 'setup')}",
        'SETUP_CONFIRMED': 'Entry confirmation',
        'RISK_APPROVED': '-> Risk approved',
        'ORDER_EXECUTED': f"{data.get('side', 'ORDER')} executed",
    }
    message = labels.get(event.type, data.get('message', event.type))
    return f'{timestamp}  {message}'


def format_orchestrated_analysis(payload: dict) -> str:
    """
    Format orchestrated execution analysis for console output.
    
    Produces the unified view showing:
    - Market regime
    - Day engine status
    - Scalping engine status
    - Portfolio state
    - AI probability
    - Risk parameters
    - Final decision
    
    Matches the format specified in the ATHENA architecture document.
    """
    if payload.get('status') == 'ERROR':
        return f"\n❌ ANALYSIS ERROR\n   {payload.get('reason', 'Unknown error')}\n"

    price = payload.get('price', {})
    regime = payload.get('regime', {})
    orchestration = payload.get('orchestration', {})
    scalping = payload.get('scalping', {})
    day_trading = payload.get('dayTrading', {})
    portfolio = orchestration.get('portfolio', {})

    # Build unified output
    lines = []
    
    # Market price header
    symbol = price.get('symbol', 'XAUUSD')
    bid = price.get('bid', 0)
    ask = price.get('ask', 0)
    spread = price.get('spread', 0)
    lines.append(f"\n{'='*70}")
    lines.append(f"{symbol:^70}")
    lines.append(f"{'='*70}")
    lines.append(f"Bid: {bid:.2f} | Ask: {ask:.2f} | Spread: {spread:.5f} ({spread/ask*10000:.1f} pips)")
    
    # Market regime
    regime_value = regime.get('regime', 'UNKNOWN')
    regime_emoji = {
        'TRENDING_BULLISH': '📈',
        'TRENDING_BEARISH': '📉',
        'VOLATILE': '⚡',
        'RANGING': '↔️',
        'UNKNOWN': '❓',
    }.get(regime_value, '?')
    lines.append(f"\nREGIME")
    lines.append(f"  H1: {regime_emoji} {regime_value}")
    
    # Day trading engine status
    day_status = day_trading.get('status', 'OBSERVE')
    day_direction = day_trading.get('direction', 'N/A')
    day_confidence = day_trading.get('confidence', 0)
    lines.append(f"\nDAY TRADING ENGINE")
    lines.append(f"  Status: {day_status:12} | Direction: {day_direction:6} | Confidence: {day_confidence:.0f}%")
    if day_trading.get('evidence'):
        evidence = day_trading['evidence']
        lines.append(f"  Evidence: {evidence.get('setup_state', 'N/A')}")
    
    # Scalping engine status
    scalp_status = scalping.get('status', 'OBSERVE')
    scalp_candidates = scalping.get('candidates', [])
    if scalp_candidates:
        primary_scalp = scalp_candidates[0]
        scalp_direction = primary_scalp.get('direction', 'N/A')
        scalp_score = primary_scalp.get('score', 0)
        setup_state = primary_scalp.get('setup', {}).get('state', 'OBSERVE')
        lines.append(f"\nSCALPING ENGINE")
        lines.append(f"  Status: {scalp_status:12} | Direction: {scalp_direction:6} | Score: {scalp_score:3.0f}")
        lines.append(f"  Setup: {setup_state}")
        
        # Setup requirements
        missing = primary_scalp.get('setup', {}).get('missing', [])
        if missing:
            lines.append(f"  Missing: {', '.join(missing)}")
        else:
            lines.append(f"  ✓ All requirements met")
    else:
        lines.append(f"\nSCALPING ENGINE")
        lines.append(f"  Status: {scalp_status:12} | No active setup")
    
    # AI advisory
    if scalp_candidates:
        ml_prob = scalp_candidates[0].get('evidence', {}).get('ml_probability', 0)
        lines.append(f"\nAI ADVISORY")
        lines.append(f"  Model: XGBoost | Probability: {ml_prob:.0%}")
    
    # Portfolio state
    lines.append(f"\nPORTFOLIO")
    lines.append(f"  Risk Available: {'✓ Yes' if portfolio.get('risk_available') else '✗ No':20} | Daily DD: {portfolio.get('daily_drawdown_pct', 0):.2f}%")
    lines.append(f"  Equity: ${portfolio.get('account_equity', 0):,.2f}")
    
    # Final decision
    decision = orchestration.get('decision', {})
    action = decision.get('action', 'OBSERVE')
    reason = decision.get('reason', 'No specific reason')
    decision_emoji = {
        'SCALP_LONG_APPROVED': '🟢 BUY',
        'SCALP_SHORT_APPROVED': '🔴 SELL',
        'DAY_BUY_DEVELOPING': '🟡 DAY DEVELOPING',
        'DAY_SELL_DEVELOPING': '🟡 DAY DEVELOPING',
        'OBSERVE': '⏸️  OBSERVE',
    }.get(action, action)
    
    lines.append(f"\n{'='*70}")
    lines.append(f"DECISION: {decision_emoji}")
    lines.append(f"Reason: {reason}")
    lines.append(f"{'='*70}\n")
    
    return '\n'.join(lines)

