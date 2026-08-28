"""
Execution Service - Bridges detector/candidates pipeline to the Executioner UI.
Provides real-time market analysis, signal generation, and decision streams.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from backend.smc.detector import advance_poi_state, detect_entry_confirmation, detect_features, detect_setup_evidence
from backend.strategies.scalping.candidates import build_decision_stream, generate_scalping_candidates
from backend.execution.paper_engine import build_paper_trade, PaperTradeError
from backend.execution.risk_engine import assess_risk
from backend.execution.xgboost_engine import XGBoostEngine
from backend.execution.trade_setup import build_trade_setup

if TYPE_CHECKING:
    from backend.accounts.models import Account


class ExecutionAnalysisUnavailable(ValueError):
    """Raised when execution analysis cannot be generated."""
    pass


def fetch_market_price(account: 'Account', symbol: str) -> dict:
    """
    Fetch current market price for a symbol from the account's market discovery.
    
    Args:
        account: Account object with market_discovery data
        symbol: Symbol name (e.g., 'XAUUSD')
    
    Returns:
        dict: {'bid': float, 'ask': float, 'spread': float, 'timestamp': str}
    """
    if not account.broker_symbol:
        raise ExecutionAnalysisUnavailable(f'No broker symbol discovered for {symbol}')
    
    discovery = account.market_discovery or {}
    symbols = discovery.get('symbols', [])
    
    symbol_data = next(
        (s for s in symbols if s.get('name') == account.broker_symbol),
        None,
    )
    
    if not symbol_data:
        raise ExecutionAnalysisUnavailable(f'Symbol {account.broker_symbol} not found in market discovery')
    
    bid = symbol_data.get('bid')
    ask = symbol_data.get('ask')
    
    if bid is None or ask is None:
        raise ExecutionAnalysisUnavailable(f'No live price data for {account.broker_symbol}')
    
    return {
        'bid': float(bid),
        'ask': float(ask),
        'spread': float(ask) - float(bid),
        'timestamp': symbol_data.get('timestamp', ''),
        'symbol': account.broker_symbol,
    }


def generate_execution_analysis(
    *,
    account: 'Account',
    m5_candles: list[dict],
    m1_candles: list[dict],
    current_price_data: dict | None = None,
    regime_context: dict | None = None,
    ml_engine: XGBoostEngine | None = None,
    news_sentiment: dict | None = None,
) -> dict:
    """
    Generate complete execution analysis: market structure, candidates, and decision stream.
    
    Args:
        account: Account object
        m5_candles: List of M5 candle dicts with 'open', 'close', 'high', 'low', 'time', 'volume'
        m1_candles: List of M1 candle dicts with same structure
    
    Returns:
        dict: {
            'status': 'READY' | 'INSUFFICIENT_DATA' | 'ERROR',
            'analysis': {
                'timeframe': str,
                'm5': {...detector output...},
                'm1': {...detector output...},
            },
            'candidates': [...list of candidate setups...],
            'decisionStream': {...why_trade, why_not, events...},
            'price': {...current price data...},
        }
    """
    try:
        # Detect market structure at both timeframes
        m5_features = detect_features(m5_candles, 'M5')
        m1_features = detect_features(m1_candles, 'M1')
        
        if m5_features['status'] == 'INSUFFICIENT_DATA' or m1_features['status'] == 'INSUFFICIENT_DATA':
            return {
                'status': 'INSUFFICIENT_DATA',
                'reason': 'Not enough candle data to analyze structure.',
                'm5Status': m5_features['status'],
                'm1Status': m1_features['status'],
            }
        
        # Get current price
        try:
            current_price_data = current_price_data or fetch_market_price(account, account.canonical_asset)
            current_price = current_price_data['ask']
        except ExecutionAnalysisUnavailable as e:
            return {
                'status': 'ERROR',
                'reason': str(e),
            }
        
        # Advance POI states based on current price
        m5_features['orderBlocks'] = [
            advance_poi_state(poi, current_price)
            for poi in m5_features.get('orderBlocks', [])
        ]
        m5_features['fairValueGaps'] = [
            advance_poi_state(poi, current_price)
            for poi in m5_features.get('fairValueGaps', [])
        ]
        
        m1_features['orderBlocks'] = [
            advance_poi_state(poi, current_price)
            for poi in m1_features.get('orderBlocks', [])
        ]
        m1_features['fairValueGaps'] = [
            advance_poi_state(poi, current_price)
            for poi in m1_features.get('fairValueGaps', [])
        ]
        
        # Generate scalping candidates
        derived_context = {**(regime_context or {}), **detect_setup_evidence(m1_candles)}
        candidates = generate_scalping_candidates(
            account=account,
            broker_symbol=account.broker_symbol,
            current_price=current_price,
            m1_features=m1_features,
            m5_features=m5_features,
            context=derived_context,
            ml_engine=ml_engine,
            m1_candles=m1_candles,
        )
        
        # Build decision stream (why trade, why not)
        decision_stream = build_decision_stream(
            candidates=candidates,
            m1_features=m1_features,
            m5_features=m5_features,
            current_price=current_price,
        )
        
        return {
            'status': 'READY',
            'analysis': {
                'timeframe': 'M1/M5',
                'm5': {
                    'structure': m5_features.get('structure'),
                    'status': m5_features.get('status'),
                    'events': m5_features.get('events', []),
                    'orderBlocks': m5_features.get('orderBlocks', []),
                    'fairValueGaps': m5_features.get('fairValueGaps', []),
                },
                'm1': {
                    'structure': m1_features.get('structure'),
                    'status': m1_features.get('status'),
                    'events': m1_features.get('events', []),
                    'orderBlocks': m1_features.get('orderBlocks', []),
                    'fairValueGaps': m1_features.get('fairValueGaps', []),
                },
            },
            'candidates': candidates,
            'decisionStream': decision_stream,
            'price': current_price_data,
            'regimeContext': regime_context,
        }
    
    except Exception as e:
        return {
            'status': 'ERROR',
            'reason': f'Analysis failed: {str(e)}',
        }


def generate_trade_signals(
    *,
    account: 'Account',
    m5_candles: list[dict],
    m1_candles: list[dict],
    current_price_data: dict | None = None,
    regime_context: dict | None = None,
    ml_engine: XGBoostEngine | None = None,
    news_sentiment: dict | None = None,
    pre_event_price: float | None = None,
    market_volatility: str | None = None,
) -> dict:
    """
    Generate trade signals and paper trade setup from analysis.
    
    Returns:
        dict: {
            'signal': 'BUY' | 'SELL' | 'NEUTRAL',
            'confidence': float (0-1),
            'entryZone': {'lower': float, 'upper': float},
            'stopLoss': float,
            'takeProfit': float,
            'riskReward': float,
            'reasoning': [str, ...],
            'paperTrade': {...paper trade details...},
        }
    """
    analysis = generate_execution_analysis(
        account=account,
        m5_candles=m5_candles,
        m1_candles=m1_candles,
        current_price_data=current_price_data,
        regime_context=regime_context,
        ml_engine=ml_engine,
    )
    
    if analysis['status'] != 'READY':
        return {
            'signal': 'NEUTRAL',
            'confidence': 0.0,
            'reasoning': [analysis.get('reason', 'No analysis available')],
        }
    
    candidates = analysis.get('candidates', [])
    ready_candidates = [c for c in candidates if c['decisionState'] == 'READY']
    
    # Determine primary signal
    if not ready_candidates:
        signal = 'NEUTRAL'
        confidence = 0.0
        reasoning = ['No active trade setup meets all criteria']
        risk_assessment = None
        entry_zone = None
        sl = None
        tp = None
        trade_setup = build_trade_setup(candidate=candidates[0] if candidates else {}, risk=None)
    else:
        # Use strongest candidate
        primary = max(ready_candidates, key=lambda c: c.get('strength', 0))
        signal = primary['direction']
        confidence = min(1.0, primary.get('strength', 0) + 0.3)  # Base confidence + setup strength
        entry_zone = primary['entryZone']
        
        # Calculate SL/TP from entry zone
        entry_mid = (entry_zone['lower'] + entry_zone['upper']) / 2
        range_width = entry_zone['upper'] - entry_zone['lower']
        
        if signal == 'BUY':
            sl = entry_zone['lower'] - range_width * 0.5
            tp = entry_zone['upper'] + range_width * 2.0
        else:  # SELL
            sl = entry_zone['upper'] + range_width * 0.5
            tp = entry_zone['lower'] - range_width * 2.0
        
        reasoning = [
            f'{primary["poiType"]} in {primary["regimeContext"]} regime',
            f'Strength: {primary.get("strength", 0):.0%}',
        ]
        risk_assessment = assess_risk(
            account=account,
            direction=signal,
            entry=entry_mid,
            stop_loss=sl,
            take_profit=tp,
        )
        if not risk_assessment['approved']:
            reasoning.append(risk_assessment['reason'])
            signal = 'NEUTRAL'
            confidence = 0.0
        trade_setup = build_trade_setup(candidate=primary, risk=risk_assessment)
    
    # Try to build paper trade
    paper_trade = None
    try:
        paper_trade = build_paper_trade(account)
        if signal != 'NEUTRAL' and risk_assessment and risk_assessment['approved']:
            paper_trade['suggestedDirection'] = signal
            paper_trade['suggestedEntry'] = entry_zone
            paper_trade['suggestedSL'] = sl
            paper_trade['suggestedTP'] = tp
            paper_trade['volume'] = risk_assessment['volume']
    except PaperTradeError:
        pass
    
    risk_reward = None
    if sl is not None and tp is not None and entry_zone is not None:
        entry = (entry_zone['lower'] + entry_zone['upper']) / 2
        price_risk = abs(entry - sl)
        reward = abs(tp - entry)
        if price_risk > 0:
            risk_reward = reward / price_risk
    
    return {
        'signal': signal,
        'confidence': confidence,
        'entryZone': entry_zone,
        'stopLoss': sl,
        'takeProfit': tp,
        'riskReward': risk_reward,
        'risk': risk_assessment,
        'tradeSetup': trade_setup,
        'reasoning': reasoning,
        'paperTrade': paper_trade,
        'fullAnalysis': analysis,
    }


def generate_orchestrated_execution_analysis(
    *,
    account: 'Account',
    m5_candles: list[dict],
    m1_candles: list[dict],
    m15_candles: list[dict] | None = None,
    h1_candles: list[dict] | None = None,
    h4_candles: list[dict] | None = None,
    current_price_data: dict | None = None,
    regime_context: dict | None = None,
    ml_engine: XGBoostEngine | None = None,
    news_sentiment: dict | None = None,
    pre_event_price: float | None = None,
    market_volatility: str | None = None,
) -> dict:
    """
    Generate unified execution analysis using the Strategy Orchestrator.
    
    This integrates both SCALPING and DAY_TRADING engines through a central
    orchestrator that manages their interaction without direct dependencies.
    
    Architecture:
    1. SCALPING ENGINE: Analyzes M5/M1 microstructure
    2. DAY_TRADING ENGINE: Analyzes H4/H1 trend and pullbacks
    3. ORCHESTRATOR: Coordinates both, produces unified decision
    4. PORTFOLIO GOVERNOR: Enforces shared risk/governance
    
    Returns:
        dict: {
            'status': 'READY' | 'ERROR' | 'OBSERVE',
            'orchestration': {...orchestrator output...},
            'scalping': {...scalping analysis...},
            'dayTrading': {...day trading analysis...},
            'price': {...current price...},
            'regime': {...market regime...},
        }
    """
    try:
        from backend.execution.orchestrator import StrategyOrchestrator
        from backend.execution.portfolio_governor import PortfolioGovernor
        from backend.strategies.day_trading.engine import generate_day_trading_analysis
        from backend.market.regime import evaluate_regime

        # Initialize orchestrator and portfolio governor
        orchestrator = StrategyOrchestrator()
        portfolio_governor = PortfolioGovernor(account=account)

        # Evaluate portfolio state
        current_equity = account.account_equity if hasattr(account, 'account_equity') else 100000
        portfolio_state = portfolio_governor.evaluate_portfolio_state(current_equity=current_equity)
        news_sentiment = news_sentiment or {}
        portfolio_state = {**portfolio_state, 'news_locked': news_sentiment.get('news_locked', True), 'news_reason': news_sentiment.get('reason', 'News sentiment is unavailable.'), 'news_sentiment': news_sentiment}

        # Set portfolio context on orchestrator
        orchestrator.set_portfolio_state(
            regime=regime_context.get('regime', 'UNKNOWN') if regime_context else 'UNKNOWN',
            state=portfolio_state,
        )

        # Generate SCALPING candidates
        m5_features = detect_features(m5_candles, 'M5') if m5_candles else {}
        m1_features = detect_features(m1_candles, 'M1') if m1_candles else {}

        try:
            current_price_data = current_price_data or fetch_market_price(account, account.canonical_asset)
            current_price = current_price_data['ask']
        except ExecutionAnalysisUnavailable:
            current_price = None

        from backend.intelligence.news.reaction import assess_market_reaction
        from backend.intelligence.news.risk import assess_execution_conditions
        execution_allowed, condition_codes, condition_reason = assess_execution_conditions(
            spread=(current_price_data or {}).get('spread'),
            volatility=market_volatility or (regime_context or {}).get('volatility'),
            max_spread=(regime_context or {}).get('max_spread'),
        )
        if not execution_allowed:
            portfolio_state = {**portfolio_state, 'execution_allowed': False, 'execution_reason': condition_reason}
            orchestrator.set_portfolio_state(
                regime=regime_context.get('regime', 'UNKNOWN') if regime_context else 'UNKNOWN',
                state=portfolio_state,
            )
        news_reaction = assess_market_reaction(
            expected_score=float(news_sentiment.get('score', 0)),
            before_price=pre_event_price,
            after_price=current_price,
            spread=(current_price_data or {}).get('spread'),
            volatility=market_volatility or (regime_context or {}).get('volatility', 'UNKNOWN'),
        ).as_dict()

        if current_price and m5_features.get('status') == 'READY' and m1_features.get('status') == 'READY':
            # Advance POI states
            m5_features['orderBlocks'] = [
                advance_poi_state(poi, current_price)
                for poi in m5_features.get('orderBlocks', [])
            ]
            m5_features['fairValueGaps'] = [
                advance_poi_state(poi, current_price)
                for poi in m5_features.get('fairValueGaps', [])
            ]
            m1_features['orderBlocks'] = [
                advance_poi_state(poi, current_price)
                for poi in m1_features.get('orderBlocks', [])
            ]
            m1_features['fairValueGaps'] = [
                advance_poi_state(poi, current_price)
                for poi in m1_features.get('fairValueGaps', [])
            ]

            derived_context = {
                **(regime_context or {}),
                **detect_setup_evidence(m1_candles),
                'news_locked': news_sentiment.get('news_locked', True),
                'news_state': news_sentiment.get('state', 'DEGRADED'),
                'news_reason': news_sentiment.get('reason', 'News sentiment is unavailable.'),
                'news_provider_available': news_sentiment.get('provider_available', False),
            }
            scalping_candidates = generate_scalping_candidates(
                account=account,
                broker_symbol=account.broker_symbol,
                current_price=current_price,
                m1_features=m1_features,
                m5_features=m5_features,
                context=derived_context,
                ml_engine=ml_engine,
                m1_candles=m1_candles,
            )

            # Ingest scalping candidate into orchestrator
            if scalping_candidates:
                primary_scalp = scalping_candidates[0]
                news_instrument = news_sentiment.get('instruments', {}).get(account.canonical_asset or 'XAUUSD')
                if news_instrument and primary_scalp.get('direction'):
                    from backend.intelligence.news.conflict import assess_conflict
                    alignment, conflict = assess_conflict(
                        technical_direction='BUY' if primary_scalp['direction'] == 'BUY' else 'SELL',
                        fundamental_score=float(news_instrument.get('news_pressure', news_sentiment.get('score', 0))),
                    )
                    news_instrument['technical_alignment'] = alignment
                    news_instrument['technical_conflict'] = conflict
                    if conflict:
                        news_instrument['recommended_action'] = 'WAIT'
                        news_instrument['execution_allowed'] = False
                        news_instrument.setdefault('reason_codes', []).append('TECHNICAL_FUNDAMENTAL_CONFLICT')
                ml_probability = 0.0
                if ml_engine:
                    try:
                        ml_probability = ml_engine.predict_win_probability({})
                    except:
                        pass
                orchestrator.ingest_scalping_candidate(primary_scalp, ml_probability=ml_probability)
        else:
            scalping_candidates = []

        # Generate DAY TRADING candidates (if we have HTF data)
        day_trading_result = {'status': 'OBSERVE', 'candidates': []}
        if h1_candles and m15_candles:
            h1_features = detect_features(h1_candles, 'H1') if h1_candles else {}
            m15_features = detect_features(m15_candles, 'M15') if m15_candles else {}
            h4_features = detect_features(h4_candles, 'H4') if h4_candles else {}

            day_trading_result = generate_day_trading_analysis(
                account=account,
                broker_symbol=account.broker_symbol,
                current_price=current_price or 0,
                m15_features=m15_features,
                h1_features=h1_features,
                h4_features=h4_features,
                context=derived_context if 'derived_context' in locals() else {},
                ml_engine=ml_engine,
                m15_candles=m15_candles,
                h1_candles=h1_candles,
            )

            # Ingest day trading candidate into orchestrator
            if day_trading_result.get('candidates'):
                orchestrator.ingest_day_trading_candidate(day_trading_result['candidates'][0])

        # Get orchestrator's unified decision
        orchestration = orchestrator.orchestrate_execution()
        decision = orchestration.get('decision') or {}
        if decision.get('action', '').endswith('_APPROVED'):
            from backend.execution.setup_service import build_approved_setup

            strategy = decision.get('strategy')
            candidate_source = scalping_candidates if strategy == 'SCALPING' else day_trading_result.get('candidates', [])
            candidate = next((item for item in candidate_source if item.get('direction')), None)
            try:
                if not candidate or current_price is None:
                    raise ValueError('Approved decision has no fresh executable candidate.')
                decision['setup'] = build_approved_setup(
                    account=account,
                    candidate=candidate,
                    strategy=strategy,
                    current_price=current_price,
                )
                decision['candidateId'] = candidate.get('candidateId')
                decision['direction'] = candidate.get('direction')
            except (TypeError, ValueError, KeyError) as error:
                orchestration['status'] = 'OBSERVE'
                orchestration['reason'] = str(error)
                orchestration['decision'] = {
                    'strategy': None,
                    'action': 'OBSERVE',
                    'reason': str(error),
                    'reasonCodes': ['SETUP_OR_RISK_VALIDATION_FAILED'],
                }

        return {
            'status': orchestration.get('status', 'OBSERVE'),
            'orchestration': orchestration,
            'scalping': {
                'status': 'READY' if scalping_candidates else 'OBSERVE',
                'candidates': scalping_candidates,
            },
            'dayTrading': {
                'status': day_trading_result.get('status', 'OBSERVE'),
                'candidates': day_trading_result.get('candidates', []),
            },
            # Keep the Executioner renderer compatible with the legacy analysis shape.
            'candidates': scalping_candidates,
            'price': current_price_data,
            'regime': regime_context,
            'regimeContext': regime_context,
            'news': news_sentiment,
            'newsReaction': news_reaction,
            'executionConditions': {
                'allowed': execution_allowed,
                'reason': condition_reason,
                'reasonCodes': list(condition_codes),
            },
            'portfolioState': portfolio_state,
        }

    except Exception as e:
        import traceback
        return {
            'status': 'ERROR',
            'reason': f'Orchestration analysis failed: {str(e)}',
            'traceback': traceback.format_exc(),
        }