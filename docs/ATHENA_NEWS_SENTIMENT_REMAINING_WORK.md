# ATHENA News and Sentiment: Remaining Work

## Purpose

This document records the work still required after Phases 1 through 7. The current system has a governed news-intelligence foundation, but it is not yet a complete production-grade autonomous news system.

The existing foundation includes:

- Provider abstraction and JSON/RSS adapters.
- Canonical news-event contracts.
- Event normalization, classification, entity extraction, and asset mapping.
- Contextual baseline sentiment analysis.
- Economic surprise and recency calculations.
- News-risk and blackout evaluation.
- Technical/fundamental conflict detection.
- Expected-versus-actual reaction classification.
- Durable news snapshots and AMEF-ready reaction observations.
- Adaptive historical reaction statistics with minimum-sample protection.
- Orchestration, Stream, Journal, and Executioner integration.

## Priority 1: Real Provider and Calendar Infrastructure

### Multiple provider integrations

Implement production adapters under `backend/intelligence/news/providers/` for:

- Economic calendar data.
- Official central-bank announcements.
- Government economic releases.
- Established financial news sources.
- Commodity and instrument-specific feeds where required.

Each adapter must implement the existing provider protocol and return data that can be normalized into `NewsEvent`.

### Provider health and failover

Add:

- Provider authentication through existing credential-management conventions.
- Request timeout and retry policies.
- Rate-limit handling.
- Provider health status and last-success timestamps.
- Source failover when one provider is unavailable.
- Duplicate suppression across providers.
- Explicit degraded and fail-closed states.

No single provider should be able to silently become the sole source of execution-critical information.

### Calendar completeness

Add calendar support for:

- Event name and category.
- Currency and affected assets.
- Scheduled time and timezone.
- Previous, forecast, and actual values.
- Importance level.
- Revision status.
- Event cancellation or delay.

## Priority 2: Background Collection and Event Lifecycle

### Scheduled collection

Add a background worker or scheduler for:

- News polling.
- Calendar polling.
- Provider health checks.
- Event lifecycle updates.
- Pre-event snapshot capture.
- Post-event reaction sampling.

The worker must not submit orders directly. It only updates intelligence and risk state consumed by orchestration.

### Event lifecycle

Complete the lifecycle transitions:

```text
DETECTED
  -> CLASSIFIED
  -> ANALYZED
  -> RELEVANT
  -> ACTIVE
  -> REACTING
  -> DECAYING
  -> EXPIRED
```

Add deterministic rules for timestamps, expiration, critical-event retention, revisions, and stale events.

### Event clustering

Replace the current basic headline grouping with robust clustering using:

- Normalized headline similarity.
- Entity overlap.
- Time proximity.
- Category and currency overlap.
- Provider agreement.
- Underlying event identifiers where supplied.

Multiple reports of one event must not be counted as independent market signals.

## Priority 3: Financial NLP and Contextual Understanding

### Full article analysis

Support separate analysis of:

- Headline.
- Summary.
- Article body.
- Quotes.
- Structured calendar values.
- Corrections and revisions.

Store headline sentiment and article sentiment separately before producing a final contextual result.

### Financial-domain model interface

Add a model interface under `backend/intelligence/news/sentiment.py` that supports:

- Rule-based fallback.
- Financial-domain transformer inference.
- Model version and checksum.
- Confidence score.
- Model availability state.
- Safe fallback when inference fails.

The model must remain advisory and cannot authorize execution.

### Contextual sentiment fixtures

Expand tests for:

- Negation.
- Comparisons with forecasts.
- “Less bad” and “more than expected” wording.
- Mixed and uncertain language.
- Conflicting sources.
- Headline/body disagreement.
- Central-bank language.
- Event-specific economic interpretation.

## Priority 4: Asset-Relative Impact and Currency Intelligence

### Relationship map

Implemented baseline: `backend/intelligence/news/relationships.py` now provides configurable relationships for major currency pairs, gold, oil, indices, and crypto, with `ATHENA_NEWS_RELATIONSHIPS_JSON` overrides. The remaining work is broad validation and calibration against production observations.

Create a configurable relationship map for:

- Currency pairs.
- Gold and commodities.
- Safe-haven assets.
- Equity indices.
- Energy-linked currencies.
- Crypto instruments where enabled.

The map should describe contextual relationships, not direct trading instructions.

### Relative currency strength

For forex instruments, calculate the relative effect on both sides of the pair. A positive USD event must be interpreted differently for `EURUSD`, `USDJPY`, and `XAUUSD`.

The result should include:

- Affected entities.
- Asset-relative score.
- Fundamental bias.
- Confidence.
- Relevance.
- Reason codes.

### Conflict and confluence

Complete integration with technical context:

- Structure direction.
- MACD and momentum.
- Volatility regime.
- Liquidity and POI state.
- Technical/fundamental alignment.
- Technical/fundamental conflict.

News may modify contextual confidence or produce a wait state, but it must not replace technical setup generation.

## Priority 5: Market Reaction and Execution Safety

### Automated reaction sampling

Capture market state before and after relevant events:

- Bid and ask.
- Spread.
- Price displacement.
- Volatility.
- Liquidity where available.
- Slippage during execution.
- Sampling timestamp and timeframe.

Persist each observation against the originating news snapshot and event cluster.

### Expected versus actual reaction

Record:

- Expected direction.
- Actual direction.
- Expected magnitude.
- Actual magnitude.
- Reaction state: `CONFIRMED`, `CONTRARY`, `MIXED`, or `UNCONFIRMED`.
- Market regime at the time of reaction.
- Spread and volatility response.

Do not overwrite historical observations when a later provider update changes current sentiment.

### Risk policy completion

Move configurable policy ownership into risk governance:

- Pre-event blackout duration.
- Post-event blackout duration.
- Reduced-risk mode.
- High-confidence-only mode.
- Existing-positions-only mode.
- Abnormal spread threshold.
- Abnormal volatility threshold.
- Recovery conditions after an event.

The final execution state must be explicit: `ALLOW`, `WAIT`, `REDUCE_RISK`, or `BLOCK`.

### Execution enforcement

Ensure every execution path checks upstream news risk:

- Paper execution.
- Confirmed demo execution.
- Automatic monitoring.
- Live order submission.
- Replay execution where news data is available.

Manual confirmation must never bypass a news block, stale decision, guardian state, or portfolio risk limit.

## Priority 6: Persistence, APIs, Journal, and AMEF

### Query APIs

Add authenticated endpoints for:

- Current instrument news state.
- Recent news events.
- Economic calendar events.
- News-risk history.
- Reaction observations.
- Adaptive statistics.
- Provider health.

Filter by account, symbol, category, risk level, event state, and time range.

### Journal enrichment

Attach immutable news context to:

- Setup creation.
- Orchestration decision.
- Execution intent.
- Paper position.
- Live execution attempt.
- Position closure.

Include sentiment, impact, event risk, technical alignment, conflict, expected reaction, actual reaction, and provider/model versions.

### AMEF integration

Create a stable AMEF record containing:

```text
Event
Event cluster
Category
Importance
Source and reliability
Affected assets
Fundamental bias
Sentiment confidence
Impact score
Market regime
Technical state
Expected reaction
Actual reaction
Execution state
Trade outcome
```

AMEF records must be point-in-time and suitable for leakage-resistant historical analysis.

## Priority 7: Adaptive Intelligence Hardening

### Provider quality statistics

Track provider performance using:

- Availability.
- Latency.
- Duplicate rate.
- Source agreement.
- Classification quality.
- Historical reaction usefulness.

Use these statistics to adjust confidence only after validation.

### Adaptive model validation

Before promoting a financial NLP or impact model:

1. Use chronologically ordered data.
2. Separate training, validation, and test periods.
3. Prevent future news and future prices from entering historical features.
4. Compare against the deterministic baseline.
5. Record model version, checksum, training period, and validation metrics.
6. Require measurable improvement before promotion.
7. Retain rollback capability.

### Minimum-history and uncertainty rules

Adaptive output must remain `INSUFFICIENT_HISTORY` or `UNCERTAIN` when:

- The sample count is too small.
- Sources disagree materially.
- The provider is degraded.
- The event category is unknown.
- Asset relevance is weak.
- The reaction is not measurable.

Adaptive output must never directly set execution approval.

## Priority 8: User Interface and Stream Completion

### Executioner

Add compact display sections for:

- Active event and countdown.
- Asset-relative fundamental bias.
- News risk level.
- Technical/news alignment.
- Execution state and reason codes.
- Expected versus actual reaction.
- Adaptive history status.

### Orchestration dashboard

Add:

- News event timeline.
- Calendar view.
- Affected assets.
- Source reliability.
- Impact and confidence.
- Conflict/confluence state.
- Blackout countdown.
- Reaction history.

### Stream

Publish and render:

- `NEWS_EVENT`.
- `NEWS_SENTIMENT`.
- `NEWS_RISK`.
- `NEWS_REACTION`.
- `NEWS_PROVIDER_HEALTH`.
- `NEWS_MODEL_STATUS`.

## Validation Gates Before Production

### Phase 5 status

- [x] Phase 5 baseline market-reaction and execution-safety implementation is complete.
- [ ] Production automation still requires scheduled pre/post sampling, replay integration, and broker slippage outcome capture.

The News Engine should not be considered production-ready until all of the following are true:

- [ ] At least two replaceable news sources are operational.
- [ ] An economic calendar source is operational.
- [x] Provider outages fail closed and are observable.
- [x] Normalized events and clusters are persisted.
- [x] Source reliability is configurable and recorded.
- [ ] Calendar surprise is event-aware and normalized.
- [ ] Asset-relative impact is tested across supported instruments.
- [x] Technical/news conflicts produce wait or block states.
- [x] Pre-event and post-event blackout windows are configurable.
- [ ] Spread and volatility protections are enforced on every execution path.
- [ ] Market reaction observations are captured automatically.
- [ ] News context is attached to journal and AMEF records.
- [x] Adaptive advice requires sufficient chronological history.
- [ ] Adaptive models are validated against a deterministic baseline.
- [x] Frontend and Stream expose risk reasoning clearly.
- [ ] Replay/backtesting uses only point-in-time news data.
- [x] No news component can independently authorize a trade.
- [x] A configurable baseline relationship map exists for supported asset classes.

## Recommended Implementation Order

1. Add real provider and calendar adapters.
2. Add background polling and provider health.
3. Complete event lifecycle, clustering, and persistence APIs.
4. Harden asset-relative mapping and contextual NLP.
5. Automate pre/post-event market reaction sampling.
6. Enforce news risk across every execution path.
7. Complete Journal and AMEF outcome records.
8. Validate and harden adaptive models.
9. Complete dashboard and Stream views.
10. Run historical replay, paper trading, and supervised demo validation before any autonomous use.

## Final Safety Rule

```text
News informs context and risk.
News does not generate an order.
The decision engine selects a valid setup.
Risk governance grants execution permission.
The Executioner executes only a fresh, approved decision.
```
