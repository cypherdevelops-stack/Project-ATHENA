from __future__ import annotations

from django.utils import timezone
from .detector import generate_day_trading_candidates
from backend.execution.xgboost_engine import XGBoostEngine


def evaluate_day_trading_state(account, risk_state) -> dict:
    """
    Legacy evaluation function for account state only.
    
    Kept for backward compatibility. For full day trading analysis,
    use generate_day_trading_candidates() which returns structured candidates
    compatible with the Strategy Orchestrator.
    """
    reasons = []
    if not account.enabled:
        return {'decisionState': 'BLOCKED', 'state': 'ACCOUNT_DISABLED', 'reasonCodes': ['ACCOUNT_DISABLED']}
    if not account.terminal_connected or not account.trade_allowed:
        reasons.append('ACCOUNT_TRADE_NOT_ALLOWED')
    if account.guardian_state() in {'HALT', 'ACCOUNT_LOCK', 'DAILY_LOCK'}:
        reasons.append(f'GUARDIAN_{account.guardian_state()}')
    if risk_state.session_locked:
        reasons.append('DAY_SESSION_LOCKED')
    if risk_state.cooldown_until and risk_state.cooldown_until > timezone.now():
        reasons.append('DAY_STRATEGY_COOLDOWN')
    if reasons:
        return {'decisionState': 'BLOCKED', 'state': risk_state.state, 'reasonCodes': reasons}
    return {'decisionState': 'OBSERVE', 'state': risk_state.state, 'reasonCodes': ['DAY_ENGINE_AWAITING_CANDIDATE']}


def generate_day_trading_analysis(*, account, broker_symbol: str, current_price: float,
                                   m15_features: dict, h1_features: dict, h4_features: dict | None = None,
                                   context: dict | None = None, ml_engine: XGBoostEngine | None = None,
                                   m15_candles: list[dict] | None = None,
                                   h1_candles: list[dict] | None = None) -> dict:
    """
    Generate complete day trading analysis.
    
    Integrates with the execution pipeline and returns candidates
    compatible with the Strategy Orchestrator.
    
    Parameters:
    - account: Trading account
    - broker_symbol: e.g., 'XAUUSD'
    - current_price: Current market price
    - m15_features: Extracted features from M15 candles
    - h1_features: Extracted features from H1 candles
    - h4_features: Extracted features from H4 candles (optional)
    - context: Market context (regime, gates, etc.)
    - ml_engine: XGBoost model (optional, for advisory only)
    - m15_candles: Raw M15 candle data
    - h1_candles: Raw H1 candle data
    
    Returns:
    {
        'status': 'ERROR' | 'BLOCKED' | 'OBSERVE' | 'DEVELOPING',
        'reason': str,
        'candidates': list[dict],  # Empty if no valid candidates
    }
    """
    # Account-level checks
    if not account.enabled:
        return {
            'status': 'ERROR',
            'reason': 'Account disabled',
            'candidates': [],
        }

    if not account.terminal_connected or not account.trade_allowed:
        return {
            'status': 'BLOCKED',
            'reason': 'Terminal disconnected or trade not allowed',
            'candidates': [],
        }

    # Generate candidates from detector
    candidates = generate_day_trading_candidates(
        account=account,
        broker_symbol=broker_symbol,
        current_price=current_price,
        m15_features=m15_features,
        h1_features=h1_features,
        h4_features=h4_features,
        context=context,
        ml_engine=ml_engine,
        m15_candles=m15_candles,
        h1_candles=h1_candles,
    )

    status = 'OBSERVE'
    if candidates:
        status = candidates[0].get('decisionState', 'OBSERVE')

    return {
        'status': status,
        'reason': 'Day trading candidate(s) generated' if candidates else 'No day trading setup',
        'candidates': candidates,
    }
