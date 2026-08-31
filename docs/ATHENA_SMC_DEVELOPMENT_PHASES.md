# ATHENA SMC Development Phases

## Purpose

Smart Money Concepts (SMC) is ATHENA's price-action and market-structure evidence layer. It identifies structure, liquidity behavior, displacement, points of interest (POIs), and entry confirmation across configured timeframes. SMC produces deterministic evidence and candidate context; it does not authorize trades or call broker execution APIs.

## Current State

The initial SMC implementation exists in `backend/smc/detector.py` and is already consumed by the scalping candidate pipeline and `backend/execution/executioner_service.py`. It currently supports:

- swing-based bullish, bearish, and range structure detection;
- Break of Structure (BOS) events;
- order block and Fair Value Gap (FVG) detection;
- liquidity sweep, displacement, and Market Structure Shift (MSS) evidence;
- POI state progression and invalidation;
- POI-specific entry confirmation.

The implementation is useful but concentrated in one module. The next development step is to move SMC implementation scripts into a dedicated package without changing the external behavior of the existing detector API.

## Target Package Layout

New SMC implementation modules should be placed under `backend/smc/scripts/`:

```text
backend/smc/
    __init__.py
    apps.py
    models.py
    views.py
    urls.py
    scripts/
        __init__.py
        types.py              # Typed input, output, and evidence contracts
        normalization.py      # Candle validation and normalization
        swings.py             # Confirmed swing-point detection
        structure.py          # BOS, CHoCH/MSS, and directional structure
        liquidity.py          # Buy-side and sell-side liquidity events
        displacement.py       # Impulse and displacement measurements
        zones.py              # Order blocks, FVGs, and POI lifecycle
        confirmation.py       # POI retest and entry confirmation
        multi_timeframe.py    # Cross-timeframe SMC context
        analyzer.py           # Public composition boundary
```

`backend/smc/detector.py` should remain a compatibility facade while the migration is in progress. Existing callers should import the facade or the public analyzer boundary, not internal scripts. No strategy, orchestrator, or executioner module should import private SMC helpers.

## Phase 1: Contracts and Package Foundation

- Create `backend/smc/scripts/` with explicit package initialization.
- Define normalized candle, timeframe, swing, POI, event, evidence, and analysis result contracts.
- Standardize statuses such as `READY`, `INSUFFICIENT_DATA`, `INVALID_INPUT`, and `UNKNOWN`.
- Preserve the current dictionary response shape at the facade boundary during the transition.
- Define deterministic handling for missing fields, duplicate timestamps, unsorted candles, zero-range candles, and incomplete latest candles.
- Add contract tests before moving detection logic.

**Exit criteria:** SMC outputs are serializable, versionable, deterministic, and callers can distinguish unavailable evidence from negative evidence.

## Phase 2: Extract Deterministic Detection Scripts

- Move candle normalization and confirmed swing logic into `normalization.py` and `swings.py`.
- Move structure and BOS/MSS calculations into `structure.py`.
- Move liquidity sweeps and displacement calculations into their dedicated modules.
- Move order block and FVG detection into `zones.py`.
- Move POI state advancement and entry confirmation into `confirmation.py` or the appropriate zone/confirmation boundary.
- Make the compatibility facade delegate to the extracted scripts.
- Keep the latest unconfirmed candle from creating a confirmed structural event.

**Exit criteria:** Existing SMC and scalping tests pass unchanged, and each extracted script has focused unit tests for positive, negative, insufficient, invalid, and boundary inputs.

## Phase 3: POI Lifecycle and Evidence Quality

**Status: Completed.** Implemented in `backend/smc/scripts/lifecycle.py` and exposed through the analyzer compatibility boundary. POIs now carry explicit lifecycle metadata, age, freshness, mitigation, retest count, source event, invalidation reason, and active-state filtering.

- Define POI states and transitions explicitly: `DETECTED`, `MONITORING`, `REACTED`, `INVALIDATED`, and `EXPIRED` where applicable.
- Record invalidation reasons and the source event that created each POI.
- Add freshness, mitigation, retest count, age, and strength fields without changing the meaning of existing fields.
- Prevent invalidated or expired POIs from becoming active candidates.
- Keep zone boundaries stable after creation unless a documented lifecycle transition changes them.

**Exit criteria:** A POI can be audited from formation through invalidation, and stale or invalidated zones cannot be promoted by downstream strategy code.

## Phase 4: Multi-Timeframe SMC Context

**Status: Completed.** Implemented in `backend/smc/scripts/multi_timeframe.py` and exposed through `analyze_multi_timeframe()`. The analyzer preserves per-timeframe evidence and reports higher-timeframe context, alignment, retracement, conflict, data quality, liquidity, and active POIs.

- Analyze configured H4, H1, M15, M5, and M1 candle streams independently.
- Produce a structured context containing per-timeframe bias, structure, latest confirmed event, active POIs, liquidity state, and data quality.
- Represent alignment, conflict, retracement, and unresolved context explicitly rather than collapsing all timeframes into one direction.
- Define precedence: higher-timeframe structure supplies context; lower-timeframe events may confirm or invalidate an entry sequence but do not rewrite higher-timeframe history.
- Reuse the existing momentum map as a parallel context signal rather than embedding momentum assumptions into SMC detection.

**Exit criteria:** The same candle inputs always produce the same multi-timeframe context, and conflicting timeframes remain visible to orchestration.

## Phase 5: Scalping Candidate Integration

**Status: Completed.** Implemented through `backend/smc/context_service.py` and the scalping candidate adapter. Scalping now consumes unified M1/M5 SMC context, lifecycle-filtered active POIs, extracted evidence, alignment, and interpretation while retaining strategy-owned scoring, gates, and candidate decisions. Focused SMC and scalping validation passes with 23 tests.

- Replace direct private-helper usage in `backend/strategies/scalping/candidates.py` with the public SMC analyzer contract.
- Map SMC evidence into candidate fields such as `poiType`, `entryZone`, `confirmation`, `scoreComponents`, and `reasonCodes`.
- Keep scoring and strategy-specific thresholds in the scalping strategy package, not in generic SMC scripts.
- Ensure SMC can return evidence-only and `OBSERVE` results when setup requirements are incomplete.
- Add integration tests for active, waiting, blocked, invalidated, and no-POI scenarios.

**Exit criteria:** SMC detects and explains evidence; the scalping engine decides whether that evidence forms a scalping candidate.

## Phase 6: Orchestrator Wiring

**Status: Completed.** Implemented shared SMC context wiring in `backend/execution/executioner_service.py` and `backend/execution/orchestrator.py`. SMC remains evidence-only: the orchestrator retains namespaced context and candidate evidence, while portfolio governance still controls the final action. Focused SMC, orchestration, and scalping validation passes with 25 tests.

- Add SMC context to the shared context assembled by `StrategyOrchestrator` without making SMC a competing strategy engine.
- Extend candidate evidence with a namespaced `smc` payload containing analyzer version, timeframes used, events, POI lifecycle state, and reason codes.
- Keep candidate ingestion strategy-specific: the orchestrator receives candidates, not raw SMC instructions.
- Define conflict behavior when SMC evidence disagrees with regime, momentum, news, or another strategy.
- Ensure the portfolio governor can block execution while retaining the SMC explanation for audit and UI display.
- Publish an `SMC_CONTEXT_UPDATE` or equivalent event only after the event contract and deduplication rules are defined.

**Exit criteria:** The orchestrator can explain how SMC contributed to a decision, but no SMC event, score, or direction directly creates an execution decision.

## Phase 7: Executioner Integration and Trade Contract

**Status: Completed.** Implemented SMC evidence propagation through `backend/execution/executioner_service.py`, `backend/execution/setup_service.py`, `backend/execution/trade_setup.py`, and `backend/execution/snapshot_service.py`. Canonical setups, orchestration responses, snapshots, and lifecycle events retain namespaced point-in-time SMC context while risk, account safety, governance, and guarded execution remain authoritative.

- Update `backend/execution/executioner_service.py` to consume the public SMC analyzer boundary through the existing analysis flow.
- Keep the executioner responsible for composing market context, candidates, risk assessment, trade setup construction, and execution eligibility.
- Pass SMC evidence into `build_trade_setup()` and journal/snapshot payloads as immutable decision-time context.
- Keep risk sizing, account safety, guardian checks, spread checks, slippage checks, idempotency, and live broker calls outside `backend/smc/scripts/`.
- Require an approved canonical trade setup before paper or live execution; SMC output alone must never satisfy that requirement.
- Preserve the existing `/execution/analysis/` and `/execution/orchestration/` behavior while adding SMC evidence fields compatibly.

**Exit criteria:** Every executed or rejected setup can be traced to its SMC context, strategy candidate, risk result, governance decision, and final execution response.

## Phase 8: Persistence, Streaming, and Backtesting

**Status: Completed.** Implemented deterministic chronological candle ordering in `backend/backtesting/replay.py`, deduplicated `SMC_CONTEXT_UPDATE` publishing in the orchestrated event stream, and retained point-in-time SMC context through the existing orchestration snapshot payload. Focused Phase 8 and replay validation passes with 4 tests.

- Store the point-in-time SMC context with orchestration snapshots, journal events, and trade outcomes.
- Publish only meaningful SMC state transitions to SSE/WebSocket streams to avoid duplicate event noise.
- Add replay support that calculates SMC only from candles available at each historical timestamp.
- Test for look-ahead leakage, incomplete-candle contamination, duplicate events, and deterministic replay.
- Measure SMC evidence by symbol, timeframe, regime, POI type, setup state, and outcome without changing live decisions automatically.

**Exit criteria:** Historical analysis can reconstruct exactly what SMC knew at decision time, and backtests do not use future candles.

## Phase 9: Validation and Bounded Adaptation

**Status: Completed.** Implemented `backend/smc/scripts/validation.py` with versioned SMC output, chronological holdout evaluation, minimum-sample fail-closed behavior, confusion metrics, false-confirmation rate, stale-POI rate, slippage tracking, and a bounded advisory adjustment. Adaptation remains explicitly advisory and does not alter live execution authority.

- Build a labelled evaluation set for structure events, POI validity, confirmation quality, and candidate outcomes.
- Track precision, recall, false confirmations, stale-zone rate, and execution slippage separately from strategy profitability.
- Version analyzer configuration and output schema.
- Introduce adaptive weighting only through the governed model-validation path, with minimum samples, chronological validation, rollback, and audit records.
- Keep adaptive weighting advisory and bounded; it must not bypass hard gates or portfolio governance.

**Exit criteria:** SMC changes are measurable, reversible, auditable, and cannot silently weaken execution controls.

## Integration Flow

```text
Market candles
    |
    v
SMC scripts/analyzer
    |
    +--> Evidence-only multi-timeframe context
    |
    v
Strategy candidate generator
    |
    v
Strategy Orchestrator
    |
    v
Portfolio Governor and execution gates
    |
    v
Canonical trade setup
    |
    v
Executioner: paper or guarded live execution
```

## Non-Negotiable Guardrails

- SMC is not an execution engine.
- BOS, CHoCH/MSS, liquidity sweeps, displacement, order blocks, and FVGs are evidence, not orders.
- A bullish or bearish SMC bias cannot bypass regime, news, spread, risk, account, guardian, or execution gates.
- No module under `backend/smc/scripts/` may call broker, paper-trade, risk-sizing, or live-order APIs.
- No latest unconfirmed candle may create a confirmed historical event.
- Every candidate must retain the evidence and reason codes that led to `READY`, `WAITING`, `BLOCKED`, or `OBSERVE`.
- SMC must fail closed when required candle data or contract fields are unavailable.

## Testing Strategy

1. Unit tests for each deterministic script and each state transition.
2. Contract tests for the public analyzer and compatibility facade.
3. Scalping integration tests for candidate mapping and scoring.
4. Orchestrator tests for SMC evidence, strategy conflicts, and portfolio blocking.
5. Executioner tests proving SMC output cannot bypass risk or execution gates.
6. Replay tests for chronological integrity and look-ahead prevention.
7. Regression tests for `/execution/analysis/` and `/execution/orchestration/` response compatibility.

## Completion Definition

SMC development is complete when its scripts are isolated under `backend/smc/scripts/`, the public analyzer contract is consumed by strategy code, orchestration receives explainable SMC-backed candidates, the executioner records point-in-time SMC context, and all execution authority remains in risk, governance, and guarded execution layers.