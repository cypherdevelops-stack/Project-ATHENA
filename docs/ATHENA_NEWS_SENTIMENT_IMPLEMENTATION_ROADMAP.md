# ATHENA News and Sentiment Analysis Implementation Roadmap

## 1. Objective

Build the News and Sentiment Analysis subsystem as a fundamental-intelligence and execution-risk layer. It must explain what is happening fundamentally, identify affected assets, assess reliability and impact, compare news with technical structure, observe the market reaction, and issue an explicit execution-risk state.

The subsystem must never create a BUY or SELL decision by itself. The decision and execution layers remain responsible for strategy selection, risk approval, and order submission.

### Required outputs

Every analysis cycle should eventually provide:

1. **Fundamental bias**: asset-relative bullish, bearish, neutral, mixed, or uncertain.
2. **Confidence and impact**: reliability, relevance, sentiment confidence, and impact score.
3. **News risk and execution state**: clear, low, moderate, high, or critical, with an allow, wait, reduce, or block outcome.
4. **Expected versus actual reaction**: whether price and execution conditions behaved as expected after the event.

## 2. Current ATHENA Baseline

The first implementation exists at `backend/market/news_sentiment.py` and currently provides:

- JSON feed retrieval using `ATHENA_NEWS_FEED_URL`.
- Headline keyword scoring and aggregation.
- Basic relevance and high-impact detection.
- A fail-closed provider state when the feed is missing or unavailable.
- `news_locked`, `state`, `score`, `label`, `confidence`, `reason`, and headline details.
- Integration into the orchestration response, scalping news context, event stream, autonomous monitor, and Executioner display.

This baseline is a safety scaffold, not the finished financial NLP system. The roadmap below replaces its internal implementation incrementally while preserving its public contract.

## 3. Target Folder Structure

Create the following structure under `backend/intelligence/news/`:

```text
backend/
  intelligence/
    __init__.py
    news/
      __init__.py
      contracts.py          # Typed normalized event and intelligence objects
      config.py             # Thresholds, blackout windows, source policy
      providers/
        __init__.py
        base.py             # NewsProvider and CalendarProvider protocols
        json_feed.py        # Existing JSON feed adapter
        rss_feed.py         # RSS adapter
        economic_calendar.py
        official_releases.py
        registry.py         # Provider registration and health state
      ingestion.py          # Polling, retries, timeout, rate limits
      normalizer.py         # Provider payload -> canonical event
      deduplication.py      # Article hashes and event clustering
      classifier.py         # Event category and importance classification
      entities.py           # Currency, institution, country, and asset extraction
      sentiment.py          # Headline/article financial sentiment
      calendar.py           # Scheduled events and actual/forecast values
      surprise.py           # Normalized actual-vs-forecast surprise
      impact.py             # Relevance, impact, confidence, and asset mapping
      reaction.py           # Expected vs actual market reaction
      conflict.py           # Technical/fundamental alignment and conflict
      risk.py               # Blackout windows and execution-risk policy
      engine.py             # End-to-end orchestration of news intelligence
      serializers.py        # API, stream, journal, and AMEF representations
      tasks.py              # Scheduled refresh jobs when a scheduler is added
      migrations/           # Only if news persistence uses Django models
      tests/
        test_contracts.py
        test_providers.py
        test_normalizer.py
        test_deduplication.py
        test_classifier.py
        test_entities.py
        test_sentiment.py
        test_calendar.py
        test_surprise.py
        test_impact.py
        test_reaction.py
        test_conflict.py
        test_risk.py
        test_engine.py
```

Existing integration points remain in place:

```text
backend/market/news_sentiment.py          # Compatibility facade during migration
backend/execution/orchestrator.py         # Shared news context and decision gating
backend/execution/executioner_service.py  # Orchestrated analysis input
backend/execution/management/commands/    # Background monitoring input
backend/stream/event_bus.py                # NEWS_SENTIMENT and NEWS_RISK events
backend/journal/                           # Setup and trade news snapshots
frontend/src/executioner/                 # Executioner rendering
frontend/src/orchestration/               # Orchestration rendering
```

## 4. Canonical Contracts

### 4.1 Normalized news event

```python
NewsEvent(
    event_id: str,
    event_cluster_id: str | None,
    timestamp: datetime,
    source: str,
    source_reliability: float,
    headline: str,
    summary: str,
    body: str | None,
    category: str,
    entities: list[str],
    affected_assets: list[str],
    importance: str,
    published_at: datetime | None,
    event_state: str,
)
```

Supported categories should include `ECONOMIC_DATA`, `CENTRAL_BANK`, `INTEREST_RATES`, `INFLATION`, `EMPLOYMENT`, `GDP`, `PMI`, `RETAIL_SALES`, `TRADE`, `GOVERNMENT`, `GEOPOLITICAL`, `WAR_CONFLICT`, `ENERGY`, `COMMODITIES`, `BANKING`, `FINANCIAL_MARKETS`, `CORPORATE`, `REGULATORY`, `CRYPTO`, and `OTHER`.

### 4.2 Instrument news intelligence

```python
InstrumentNewsState(
    symbol: str,
    fundamental_bias: str,
    sentiment: str,
    sentiment_confidence: float,
    news_pressure: float,
    impact_score: float,
    event_risk: str,
    technical_alignment: str,
    technical_conflict: bool,
    recommended_action: str,
    execution_allowed: bool,
    reason_codes: list[str],
    active_events: list[str],
)
```

### 4.3 Provider boundary

```python
class NewsProvider(Protocol):
    name: str

    def fetch_latest(self, *, symbols: list[str]) -> list[dict]: ...

class CalendarProvider(Protocol):
    name: str

    def fetch_events(self, *, start: datetime, end: datetime) -> list[dict]: ...
```

Providers must be replaceable, independently health-checked, timeout-bounded, and unable to authorize trades directly.

## 5. Implementation Phases

### Phase 1: Deterministic foundation

1. Move the current headline scorer behind `contracts.py`, `providers/base.py`, and `sentiment.py`.
2. Keep `backend/market/news_sentiment.py` as a compatibility facade.
3. Add provider configuration, timeout, retry, polling, and health state.
4. Support JSON and RSS adapters without coupling the analyzer to either format.
5. Normalize all provider payloads into `NewsEvent`.
6. Add source reliability configuration for official, primary financial, aggregator, and social sources.
7. Add deterministic category, importance, entity, and asset mapping rules.
8. Add explicit `CLEAR`, `LOW`, `MODERATE`, `HIGH`, and `CRITICAL` news-risk states.
9. Add configurable pre-event and post-event blackout windows.
10. Preserve fail-closed behavior for unknown or unavailable news state.

**Exit criteria:** provider failure, malformed payloads, duplicate headlines, and missing timestamps are handled deterministically; no unavailable provider can produce an execution approval.

### Phase 2: Economic calendar and event intelligence

1. Add calendar provider abstraction and canonical calendar events.
2. Store currency, expected time, previous, forecast, actual, importance, and category.
3. Calculate normalized surprise values rather than using raw values across indicators.
4. Add event-specific interpretation rules, including contextual inflation and rate implications.
5. Implement event lifecycle: `DETECTED`, `CLASSIFIED`, `ANALYZED`, `RELEVANT`, `ACTIVE`, `REACTING`, `DECAYING`, `EXPIRED`.
6. Add recency decay while allowing critical events to retain influence.
7. Add event clustering so repeated reports count as one underlying event with multiple source confirmations.

**Exit criteria:** a CPI, employment, GDP, and central-bank fixture each produce stable event classification, surprise, lifecycle, and asset impact outputs.

### Phase 3: Financial NLP

1. Separate headline sentiment from article/body sentiment.
2. Add financial-domain sentiment labels: `BULLISH`, `BEARISH`, `NEUTRAL`, `MIXED`, and `UNCERTAIN`.
3. Add entity extraction for currencies, central banks, countries, commodities, indices, and instruments.
4. Add contextual phrase handling so wording such as “inflation fell less than expected” is interpreted as an economic surprise, not a naive keyword result.
5. Add model confidence and preserve rule-based fallback behavior.
6. Introduce a pluggable model interface so a financial transformer can replace the baseline without changing downstream contracts.
7. Treat social sentiment as low-reliability context only.

**Exit criteria:** benchmark fixtures cover negation, comparison with forecast, mixed sentiment, source disagreement, and low-confidence classification.

### Phase 4: Asset-relative impact and technical confluence

1. Build a configurable currency/entity relationship map.
2. Map source-event implications to each affected instrument independently.
3. Distinguish fundamental sentiment from observed market sentiment.
4. Add technical/fundamental matrix states: `ALIGNED`, `CONFLICT`, `TECHNICAL_LED`, and `UNCERTAIN`.
5. Feed technical regime, direction, volatility, and setup state into conflict assessment, without allowing news to generate a setup.
6. Let confluence modify contextual confidence, but keep execution permission in risk governance.

**Exit criteria:** the same USD-positive event produces distinct contextual effects for XAUUSD, EURUSD, USDJPY, and USD-denominated assets; opposing technical/news direction produces an explicit conflict and wait/block action.

### Phase 5: Market reaction and execution safety

1. Capture a pre-event market snapshot: price, spread, volatility, and liquidity.
2. Capture post-event snapshots at configurable intervals.
3. Compare expected asset reaction with actual direction and magnitude.
4. Classify reaction as `CONFIRMED`, `CONTRARY`, `MIXED`, or `UNCONFIRMED`.
5. Detect abnormal spread, slippage, displacement, and volatility.
6. Implement risk policy outcomes: `ALLOW`, `WAIT`, `REDUCE_RISK`, and `BLOCK`.
7. Keep the risk policy configurable and separate from the parser and sentiment model.
8. Require the Executioner and automatic monitor to consume the final upstream execution state.

**Exit criteria:** a technically valid setup is blocked during a configured blackout or abnormal spread condition; a technically valid setup is not automatically approved merely because news sentiment agrees.

### Phase 6: Persistence, stream, journal, and AMEF

1. Persist normalized events, clusters, source reliability, model outputs, risk decisions, and reaction observations.
2. Snapshot news context with every candidate, execution intent, paper trade, live attempt, and closed trade.
3. Publish `NEWS_EVENT`, `NEWS_SENTIMENT`, `NEWS_RISK`, and `NEWS_REACTION` events through the stream.
4. Render concise news reasoning in the Orchestration dashboard and Executioner.
5. Add journal fields for fundamental bias, impact, alignment, conflict, risk, and reaction.
6. Add AMEF records for event, asset, regime, expected reaction, actual reaction, and trade outcome.
7. Ensure historical records are immutable snapshots even when current sentiment later changes.

**Exit criteria:** a completed trade can be reviewed with the exact news context and risk state that existed when its decision was made.

### Phase 7: Adaptive intelligence

1. Measure provider quality and source agreement over time.
2. Learn event-class and regime-specific reaction statistics.
3. Evaluate asset-specific impact models using historical outcomes.
4. Train or fine-tune financial NLP and event models only on leakage-resistant, time-ordered data.
5. Keep learned outputs advisory until validated against a deterministic baseline and approved by model governance.
6. Never let an adaptive model bypass guardian, portfolio, blackout, or execution safety gates.

## 6. Integration Rules

### Orchestrator

The orchestrator receives `InstrumentNewsState` as shared context and exposes it in the unified response. It may block or delay execution based on `execution_allowed`, event risk, and blackout policy. It must not convert fundamental bias directly into a strategy candidate.

### Risk governance

Risk governance owns blackout windows, reduced-risk policy, abnormal market-condition checks, and final execution permission. Signal validity and execution permission remain separate concepts.

### Executioner

The Executioner displays the upstream news state and obeys the final execution decision. It does not fetch, classify, or reinterpret news locally. Manual confirmation cannot bypass a news block.

### Stream and dashboard

Show event, affected instrument, bias, confidence, impact, risk, conflict/alignment, expected reaction, actual reaction, and reason codes. Keep the display concise enough for live scanning.

### Journal and AMEF

Record immutable point-in-time news context on every setup and trade. Do not replace historical context when a later article changes the current aggregate state.

## 7. Configuration

Initial configuration should be environment-backed and later move to validated account or system settings:

```env
ATHENA_NEWS_FEED_URL=
ATHENA_NEWS_CALENDAR_URL=
ATHENA_NEWS_POLL_SECONDS=30
ATHENA_NEWS_REQUEST_TIMEOUT_SECONDS=3
ATHENA_NEWS_PRE_EVENT_BLACKOUT_MINUTES=15
ATHENA_NEWS_POST_EVENT_BLACKOUT_MINUTES=10
ATHENA_NEWS_MIN_SOURCE_RELIABILITY=0.70
ATHENA_NEWS_HIGH_IMPACT_THRESHOLD=0.80
ATHENA_NEWS_CRITICAL_THRESHOLD=0.95
ATHENA_NEWS_FAIL_CLOSED=true
```

Secrets must remain outside source control. Provider credentials should be read through the existing configuration and credential-management conventions.

## 8. Testing and Validation Strategy

- Unit test every analyzer with deterministic fixtures and frozen timestamps.
- Test provider timeouts, malformed JSON/RSS, empty feeds, duplicate events, conflicting sources, and unavailable providers.
- Test surprise signs for inflation, employment, GDP, and rates independently.
- Test asset-relative mapping for both sides of currency pairs and commodities.
- Test recency decay and critical-event retention.
- Test technical/news alignment and conflict without creating a trade signal.
- Test blackout boundaries immediately before, during, and after an event.
- Test spread and volatility post-event blocks.
- Test orchestration, monitor, stream, journal, paper execution, and live-order rejection paths.
- Test that stale or missing news cannot result in an approved automatic order.
- Add contract tests to ensure the compatibility facade and frontend payload remain stable.
- Use replay/backtesting fixtures for expected-versus-actual reaction analysis; never use future news data in a historical decision.

## 9. Delivery Checklist

- [ ] Provider interfaces and health states exist.
- [ ] JSON, RSS, calendar, and official-release adapters are independently replaceable.
- [ ] All input is normalized into canonical events.
- [ ] Source reliability, duplication, clustering, and recency decay are implemented.
- [ ] Event category, entities, importance, surprise, and affected assets are available.
- [ ] Sentiment supports contextual and asset-relative analysis.
- [ ] Fundamental sentiment and market reaction are separate outputs.
- [ ] Technical/fundamental alignment and conflict are explicit.
- [ ] News-risk policy supports clear, low, moderate, high, and critical states.
- [ ] Pre-event and post-event protections are configurable.
- [ ] Orchestrator and automatic monitor consume the same news contract.
- [ ] Executioner displays and obeys upstream news execution state.
- [ ] Stream events, journal snapshots, and AMEF records are persisted.
- [ ] Historical and live tests pass with time-ordered data.
- [ ] No news model can authorize a trade independently.

## 10. Core Rule

```text
NEWS
  -> normalize and verify
  -> classify the event
  -> identify affected assets
  -> assess contextual sentiment and impact
  -> compare with technical structure
  -> observe actual market reaction
  -> calculate news risk
  -> issue execution permission to risk governance
  -> let the decision engine choose whether a strategy is valid
  -> let the Executioner execute only an approved decision
```

ATHENA must never trade simply because news is bullish or bearish. News is fundamental awareness, confluence context, reaction intelligence, and execution-risk control. It is not an independent signal generator.
