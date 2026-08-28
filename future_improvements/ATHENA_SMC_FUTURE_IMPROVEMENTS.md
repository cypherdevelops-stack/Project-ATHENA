# ATHENA SMC Future Improvements

## Purpose

Phases 1 through 9 establish the deterministic SMC foundation, strategy integration, orchestration wiring, execution traceability, replay support, and bounded validation layer. This document captures the remaining work required to move SMC from a functional integrated subsystem toward a more complete, production-grade research and decision-support engine.

SMC remains an evidence layer. None of the improvements below may bypass risk controls, portfolio governance, account safety, news controls, or guarded execution.

## Priority Order

1. Improve structure and liquidity detection.
2. Strengthen POI lifecycle and confluence quality.
3. Build dedicated SMC replay and labelled evaluation data.
4. Add sessions, dealing ranges, and richer context.
5. Improve explainability, configuration, monitoring, and performance.
6. Introduce carefully governed adaptive weighting only after the preceding evidence is reliable.

## 1. Advanced Market Structure

### Remaining Work

- Detect internal and external structure separately.
- Add CHoCH as a distinct event from BOS and MSS.
- Track protected highs, protected lows, and invalidated structural points.
- Detect inducement and distinguish inducement breaks from meaningful structural breaks.
- Support equal highs and equal lows as structural liquidity references.
- Add swing strength, displacement quality, confirmation age, and event confidence.
- Handle nested structure across H4, H1, M15, M5, and M1 without flattening timeframes.
- Define explicit rules for ties, overlapping swings, gaps, and range conditions.
- Add configurable lookback, confirmation window, minimum displacement, and noise thresholds.

### Completion Criteria

- BOS, CHoCH, MSS, inducement, and range events have distinct schemas and reason codes.
- Confirmed and unconfirmed structure cannot be confused by downstream consumers.
- Structural history is reproducible from the same candle sequence and configuration.
- Tests cover trend, range, reversal, equal-level, noisy, insufficient, and incomplete-candle cases.

## 2. Liquidity and Raid Intelligence

### Remaining Work

- Build explicit liquidity pools from equal highs, equal lows, recent extremes, and session extremes.
- Classify buy-side and sell-side raids by sweep depth, close location, rejection, and displacement.
- Rank likely liquidity targets above and below current price.
- Track whether liquidity was untouched, probed, swept, reclaimed, or invalidated.
- Distinguish a genuine liquidity sweep from a simple high or low break.
- Add liquidity age, source timeframe, strength, and target state to the evidence contract.
- Expose liquidity conflicts when lower-timeframe raids oppose higher-timeframe context.

### Completion Criteria

- Every liquidity event identifies its source level, side, timeframe, timestamp, and lifecycle state.
- Sweep classifications are deterministic and explainable.
- Liquidity evidence can be replayed without future candles.
- Candidate generation can consume ranked liquidity evidence without SMC authorizing a trade.

## 3. Premium, Discount, and Dealing Ranges

### Remaining Work

- Define dealing ranges from confirmed structural legs.
- Calculate equilibrium, premium, and discount zones.
- Support daily and weekly range context where data is available.
- Score POI location relative to the relevant dealing range.
- Preserve range origin, anchor events, timeframe, and invalidation state.
- Handle overlapping and conflicting dealing ranges explicitly.

### Completion Criteria

- Premium/discount classification is tied to a named structural range.
- Range calculations are stable and look-ahead safe.
- POI location quality is visible in candidate evidence and reason codes.
- Missing range anchors produce `UNKNOWN` or `INSUFFICIENT_DATA`, not inferred certainty.

## 4. POI Lifecycle and Confluence Quality

### Remaining Work

- Add mitigation depth and partial-fill tracking.
- Track retest sequence, rejection quality, and repeated mitigation.
- Define zone freshness and expiry policies per timeframe and POI type.
- Rank overlapping order blocks and FVGs by source event, freshness, strength, and timeframe alignment.
- Detect nested POI confluence across higher and lower timeframes.
- Add zone merge and separation rules for overlapping boundaries.
- Prevent invalidated, expired, or over-mitigated POIs from downstream promotion.
- Persist POI lifecycle transitions when they are used in a decision.

### Completion Criteria

- POI state transitions are explicit, monotonic where required, and auditable.
- Active POIs have stable boundaries and a deterministic ranking.
- Repeated retests cannot silently reset freshness or validity.
- Candidate evidence identifies exactly which POIs contributed to confluence.

## 5. Entry Confirmation Quality

### Remaining Work

- Separate rejection, displacement, micro-MSS, and entry confirmation into independently scored evidence.
- Require closed-candle confirmation where the strategy configuration demands it.
- Measure body-to-range quality, wick rejection, follow-through, and close location.
- Add false-break and failed-displacement detection.
- Add optional tick-volume or volume context without making volume universally authoritative.
- Distinguish first confirmation from late confirmation and exhausted confirmation.
- Include confirmation age and expiry in candidate evidence.

### Completion Criteria

- A candidate can explain every confirmation component independently.
- Incomplete latest candles cannot create a final confirmation.
- Weak, late, and failed confirmations are represented as different states.
- Confirmation metrics are available for historical evaluation.

## 6. Session and Range Context

### Remaining Work

- Add configurable timezone-aware London, New York, and Asia session windows.
- Detect session highs, lows, opens, closes, and range expansion.
- Support kill-zone and session-overlap context where configured.
- Connect news proximity and session context without duplicating the news subsystem.
- Represent weekends, holidays, daylight-saving transitions, and missing session data safely.
- Add session-specific reason codes and evidence fields to the SMC context.

### Completion Criteria

- Session calculations are timezone-aware and deterministic.
- Session context is optional and fails closed when configuration or data is unavailable.
- Session levels can participate in liquidity ranking and POI quality without directly authorizing candidates.

## 7. Dedicated SMC Replay and Labelled Data

### Remaining Work

- Build a dedicated SMC replay path independent of trade profitability.
- Recalculate structure, liquidity, POIs, and confirmations using only candles visible at each timestamp.
- Persist event-level replay output with analyzer schema and configuration versions.
- Create labelled datasets for structure events, liquidity sweeps, POI validity, confirmation quality, and eventual outcomes.
- Add chronological train, validation, and test partitions.
- Measure event precision, recall, false-confirmation rate, stale-zone rate, POI survival, and slippage separately.
- Add replay tests for look-ahead leakage, duplicate events, incomplete candles, and out-of-order data.

### Completion Criteria

- Historical output can reconstruct exactly what SMC knew at decision time.
- Labels use forward data only after the point-in-time feature snapshot.
- Replay results are deterministic across repeated runs.
- Dataset lineage, source range, symbol, timeframe, timezone, and configuration are recorded.

## 8. Validation and Governance Integration

### Remaining Work

- Connect `evaluate_smc_records()` to persistent labelled datasets and replay outputs.
- Add minimum sample requirements by symbol, timeframe, regime, POI type, and setup type.
- Add confidence intervals or uncertainty ranges where sample sizes permit.
- Require chronological validation and analyzer-version compatibility before comparing results.
- Persist validation reports, configuration hashes, and approval decisions.
- Add explicit rollback and deprecation paths for analyzer configurations.
- Route any future weighting changes through the existing model governance process.
- Keep all weighting advisory, bounded, and unable to bypass hard gates.

### Completion Criteria

- Every validation report is reproducible and versioned.
- Insufficient or incompatible data produces no adaptation.
- Weight changes have an audit record, owner, reason, baseline, and rollback path.
- Live behavior remains unchanged unless a separately approved governed configuration is active.

## 9. Explainability and Evidence Contracts

### Remaining Work

- Define versioned schemas for structure events, liquidity events, POIs, confirmations, and multi-timeframe context.
- Add stable reason codes for accepted, rejected, waiting, blocked, expired, and unknown states.
- Include source candle timestamps and source timeframes for every derived event.
- Add analyzer configuration identifiers and output hashes to snapshots.
- Provide concise human-readable interpretations alongside machine-readable evidence.
- Ensure UI, journal, orchestration, and replay consumers use the same contract.
- Add compatibility tests for schema evolution.

### Completion Criteria

- A decision can be traced from raw candles to SMC evidence, candidate, governance result, risk result, setup, and execution response.
- Consumers do not need to infer state from missing fields.
- Schema changes are backward-compatible or explicitly versioned.

## 10. Streaming, Persistence, and Monitoring

### Remaining Work

- Publish only meaningful SMC state transitions, not repeated unchanged snapshots.
- Add event IDs, source timestamps, analyzer version, and deduplication keys.
- Persist SMC context separately when full orchestration snapshots are unavailable.
- Track analyzer latency, input size, invalid-input rate, and failure rate.
- Add alerts for repeated data-quality degradation, stale POIs, and unexpected event volume.
- Preserve event ordering and replayability across SSE, WebSocket, journal, and database consumers.

### Completion Criteria

- Stream consumers receive ordered, deduplicated, versioned SMC events.
- Monitoring distinguishes market conditions from analyzer failures.
- Persistence can reconstruct the point-in-time SMC state for any recorded decision.

## 11. Performance and Reliability

### Remaining Work

- Profile multi-timeframe analysis over realistic candle windows.
- Avoid repeated normalization and duplicate calculations within one analysis cycle.
- Add bounded memory and event-history policies.
- Define behavior for malformed, missing, duplicated, unsorted, and extreme-value candles.
- Add property-based or generated tests for numerical and lifecycle edge cases.
- Add deterministic configuration loading and validation.
- Confirm that SMC scripts never import broker, paper execution, risk-sizing, or live-order modules.

### Completion Criteria

- Analysis latency and memory use remain within documented limits.
- Malformed inputs fail closed with actionable diagnostics.
- The SMC package remains independently testable without broker connectivity.
- No performance optimization changes evidence semantics without regression coverage.

## 12. Research and Adaptive Extensions

These items should only begin after the deterministic and labelled evaluation work is complete.

- Compare alternative swing and displacement definitions offline.
- Evaluate symbol- and regime-specific thresholds with minimum sample safeguards.
- Test bounded contextual weighting against a frozen baseline.
- Use walk-forward evaluation and out-of-sample periods.
- Measure whether added SMC complexity improves evidence quality, not only trade count or profitability.
- Reject changes that improve backtest results while degrading explainability, stability, or execution safety.

### Completion Criteria

- Every research change has a frozen baseline and out-of-sample report.
- Improvements are statistically and operationally meaningful.
- Rollback is possible without code surgery or database reconstruction.
- No adaptive result becomes live by default.

## Recommended Next Build Sequence

1. Expand structure events and liquidity pools.
2. Add premium/discount dealing ranges.
3. Improve POI ranking and mitigation quality.
4. Build dedicated SMC replay and labelled event storage.
5. Connect persistent evaluation to the validator.
6. Add session context and richer explainability.
7. Add monitoring and performance limits.
8. Evaluate bounded adaptive weighting offline.

## Final Guardrail

SMC can become more detailed, more predictive, and more measurable, but it must remain a transparent evidence provider. The final authority remains distributed across strategy qualification, portfolio governance, risk controls, account safety, and guarded execution.
