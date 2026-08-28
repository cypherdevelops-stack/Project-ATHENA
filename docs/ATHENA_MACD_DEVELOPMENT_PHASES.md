# ATHENA MACD Development Phases

## Purpose

MACD is a contextual momentum sensor for ATHENA. It contributes evidence about direction, transitions, momentum strength, acceleration, deceleration, divergence, and exhaustion. It must never independently authorize a BUY or SELL decision.

## Implementation Status

Phases 1 through 7 are implemented across the market, execution, strategy, Stream, journal, and snapshot boundaries. The current slice is deterministic and advisory; it does not generate trade actions. Historical attribution requires closed-outcome records supplied by the caller and does not modify decisions directly.

## Phase 1: Deterministic Analyzer Foundation

- Add a dedicated `MACDAnalyzer` with configurable fast, slow, and signal periods.
- Calculate MACD, signal, and histogram series from normalized closes without a third-party indicator dependency.
- Expose semantic states for direction, zero-line position, signal relationship, crossover, histogram polarity, and momentum behavior.
- Return explicit `UNKNOWN` and zero-confidence output when history is insufficient.
- Add unit tests for stable, trending, flat, invalid, and insufficient data.

**Exit criteria:** analyzer output is deterministic, serializable, and contains no trade action.

## Phase 2: Existing Regime Integration

- Replace the private regime MACD calculation with `MACDAnalyzer`.
- Preserve the existing regime API fields and behavior while adding richer MACD evidence to market context.
- Use MACD as one regime confirmation among structure and volatility, never as the sole regime authority.

**Exit criteria:** existing regime tests pass and MACD failures cannot silently produce an execution decision.

## Phase 3: Divergence and Exhaustion

- Detect price higher-high/MACD lower-high and price lower-low/MACD higher-low patterns using confirmed swing points.
- Score divergence strength from price and MACD displacement, then classify contextual exhaustion risk.
- Add configurable swing confirmation, lookback, minimum separation, and noise thresholds.
- Test divergence against synthetic and edge-case series, including incomplete latest swings.

**Exit criteria:** divergence is evidence only and is distinguishable from a signal-line crossover.

## Phase 4: Multi-Timeframe Momentum Map

**Status: Implemented.**

- Analyze configured H4, H1, M15, and M5 candle streams.
- Produce alignment, conflict, likely-retracement, and potential-reversal context without collapsing timeframes into one signal.
- Make higher-timeframe structure and regime precedence explicit in the interpretation layer.

**Exit criteria:** lower-timeframe bearish momentum can be represented as a retracement inside a bullish higher-timeframe context.

## Phase 5: Regime, Confluence, and Decision Consumption

**Status: Implemented.**

- Feed semantic MACD output into regime and confluence services.
- Adjust confidence as a bounded evidence contribution alongside structure, POI, liquidity, news, risk, AI, and memory.
- Add conflict explanations such as positive momentum with contracting histogram or bullish structure with bearish divergence.
- Keep hard execution gates outside the indicator module.

**Exit criteria:** no MACD field, crossover, or divergence can directly create an execution order.

## Phase 6: Stream, Journal, and AMEF Snapshots

**Status: Implemented.**

- Publish semantic MACD state through Stream and execution analysis responses.
- Store the relevant MACD state in journal and AMEF contextual snapshots at setup time.
- Associate entry-time momentum context with outcome, R multiple, excursion, duration, and exit reason.

**Exit criteria:** a historical trade can be inspected with the MACD context that existed at decision time.

## Phase 7: Historical Validation and Adaptive Weighting

**Status: Implemented.**

- Measure MACD configurations by symbol, timeframe, regime, POI type, and liquidity context.
- Validate statistical extremity only when sufficient historical samples exist; do not introduce universal MACD overbought/oversold thresholds.
- Use AMEF outcomes to inform bounded contextual weighting with minimum-sample and model-version safeguards.

**Exit criteria:** any adaptive weighting is auditable, leakage-resistant, and remains advisory to the governed decision engine.

## Guardrails

- `MACD > 0` is not an automatic BUY.
- `MACD < 0` is not an automatic SELL.
- A signal-line crossover is not an order instruction.
- Divergence is not reversal confirmation.
- MACD does not use RSI's 70/30 thresholds.
- Market structure, regime, POI, liquidity, news, risk, AI, and historical context retain decision authority.