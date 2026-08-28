import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import '../styles/executioner.css';
import { authService, type AccountProfile, type ExecutionAnalysis, type TradeSignal } from '../authentication/services/authService';

function formatPrice(value?: number | null) {
  if (value === undefined || value === null || !Number.isFinite(value)) {
    return '--';
  }
  return value >= 100 ? value.toFixed(2) : value.toFixed(4);
}

function getSignalBadgeClass(signal?: string | null) {
  if (!signal) return 'signal-neutral';
  if (signal === 'BUY') return 'signal-buy';
  if (signal === 'SELL') return 'signal-sell';
  return 'signal-neutral';
}

function TerminalLine({ label, value, tone = '' }: { label?: string; value: string; tone?: string }) {
  return <div className={`execution-terminal-line ${tone}`}><span>{label}</span>{label && ' : '}{value}</div>;
}

function ProgressiveAnalysis({ instrument, analysis, signal, modelStatus }: { instrument: string; analysis: ExecutionAnalysis | null; signal: TradeSignal | null; modelStatus: { version?: string | null; trainedAt?: string | null } | null }) {
  const candidate = analysis?.candidates?.[0] as Record<string, any> | undefined;
  const setup = candidate?.setup as Record<string, any> | undefined;
  const gates = (candidate?.gates ?? []) as Array<{ name: string; status: string }>;
  const regime = analysis?.regimeContext;
  const price = analysis?.price ?? signal?.fullAnalysis?.price;
  const entryZone = signal?.entryZone ?? candidate?.entryZone as { lower: number; upper: number } | undefined;
  const tradeSetup = signal?.tradeSetup;
  const paperTrade = signal?.paperTrade as Record<string, any> | null | undefined;
  const mlPrediction = candidate?.mlPrediction as { status?: string; probability?: number | null } | undefined;
  const news = analysis?.news;
  const newsReaction = analysis?.newsReaction;
  const executionConditions = analysis?.executionConditions;
  const setupMissing = (setup?.missing ?? []) as string[];
  const liquiditySide = candidate?.direction === 'SELL' ? 'BUY-SIDE ABOVE RECENT HIGHS' : 'SELL-SIDE BELOW RECENT LOWS';
  const analysisTimeframe = String(candidate?.timeframe ?? 'M1');
  const confirmationTimeframe = analysisTimeframe === 'M1' ? 'M1' : `${analysisTimeframe}/M1`;
  const liquidityPrice = candidate?.direction === 'SELL' ? entryZone?.upper : entryZone?.lower;
  const liquidityPriceText = typeof liquidityPrice === 'number' ? formatPrice(liquidityPrice) : 'level unavailable';
  const liquidityWaitingReason = `Watching ${confirmationTimeframe} candles for ${liquiditySide} to sweep near ${liquidityPriceText}, then displace and confirm MSS.`;
  const status = candidate?.decisionState === 'READY'
    ? `${candidate.direction === 'SELL' ? 'SHORT' : 'LONG'} CANDIDATE`
    : setupMissing.includes('LIQUIDITY_SWEEP') ? `WAITING FOR ${liquiditySide} SWEEP`
      : setupMissing.includes('MSS') || setupMissing.includes('DISPLACEMENT') ? 'WAITING FOR STRUCTURE CONFIRMATION'
        : setupMissing.includes('POI_RETEST') ? 'WAITING FOR RETRACEMENT' : 'WAITING FOR SETUP';
  const lines = [
    { section: '', rows: [
      <TerminalLine key="symbol" value={instrument} tone="terminal-symbol" />,
      <TerminalLine key="bid" label="BID" value={formatPrice(price?.bid)} />,
      <TerminalLine key="ask" label="ASK" value={formatPrice(price?.ask)} />,
      <TerminalLine key="spread" label="SPREAD" value={formatPrice(price?.spread)} />,
    ]},
    { section: 'HTF REGIME', rows: [
      <TerminalLine key="structure" label="H1 Structure" value={`${regime?.structure ?? 'UNKNOWN'} - ${regime?.structureReason ?? 'No structure explanation available.'}`} />,
      <TerminalLine key="macd" label="MACD" value={`${regime?.macd ?? 'UNKNOWN'} - ${regime?.macdReason ?? 'No MACD explanation available.'}`} />,
      <TerminalLine key="volatility" label="Volatility" value={`${regime?.volatility ?? 'UNKNOWN'} - ${regime?.volatilityReason ?? 'No volatility explanation available.'}`} />,
    ]},
    { section: 'XGBOOST MODEL', rows: [
      <TerminalLine key="model-version" label="Version" value={modelStatus?.version ?? 'UNKNOWN'} />,
      <TerminalLine key="model-trained" label="Trained" value={modelStatus?.trainedAt ? new Date(modelStatus.trainedAt).toLocaleString() : 'UNKNOWN'} />,
      <TerminalLine key="model-status" label="Status" value={mlPrediction?.status ?? 'UNKNOWN'} tone={mlPrediction?.status === 'PASS' ? 'terminal-pass' : mlPrediction?.status === 'BLOCK' ? 'terminal-block' : 'terminal-wait'} />,
      <TerminalLine key="model-probability" label="Probability" value={mlPrediction?.probability == null ? '--' : `${(mlPrediction.probability * 100).toFixed(1)}%`} />,
    ]},
    { section: 'NEWS SENTIMENT', rows: [
      <TerminalLine key="news-state" label="State" value={news?.state ?? 'UNKNOWN'} tone={news?.news_locked ? 'terminal-block' : 'terminal-pass'} />,
      <TerminalLine key="news-label" label="Bias" value={news?.label ?? 'UNKNOWN'} />,
      <TerminalLine key="news-score" label="Score" value={news ? `${(news.score * 100).toFixed(1)}%` : '--'} />,
      <TerminalLine key="news-reason" label="Reason" value={news?.reason ?? 'News sentiment unavailable.'} />,
      <TerminalLine key="news-reaction" label="Reaction" value={newsReaction ? `${newsReaction.expected_direction} expected / ${newsReaction.actual_direction} actual (${newsReaction.state})` : 'UNCONFIRMED'} />,
      <TerminalLine key="news-execution" label="Execution" value={executionConditions ? `${executionConditions.allowed ? 'ALLOWED' : 'BLOCKED'} - ${executionConditions.reason}` : 'UNKNOWN'} tone={executionConditions?.allowed ? 'terminal-pass' : 'terminal-block'} />,
      <TerminalLine key="news-adaptive" label="Adaptive" value={news?.adaptive_advice ? `${news.adaptive_advice.status} / ${news.adaptive_advice.sample_count} samples` : 'UNAVAILABLE'} />,
    ]},
    { section: 'GATES', rows: gates.map((gate) => (
      <TerminalLine key={gate.name} label={gate.name.replace(/_GATE$/, '').replaceAll('_', ' ')} value={`${gate.status === 'PASS' ? '✓' : gate.status === 'BLOCK' ? '✕' : '…'} ${gate.status}`} tone={gate.status === 'PASS' ? 'terminal-pass' : gate.status === 'BLOCK' ? 'terminal-block' : 'terminal-wait'} />
    ))},
    { section: 'SCALP STATE', rows: [
      <TerminalLine key="bias" label="Bias" value={candidate?.direction === 'SELL' ? 'SHORT' : candidate?.direction === 'BUY' ? 'LONG' : 'UNKNOWN'} />,
      <TerminalLine key="liquidity" label="Liquidity" value={setupMissing.includes('LIQUIDITY_SWEEP') ? `${liquiditySide} - NOT SWEPT` : `${liquiditySide} - SWEPT`} />,
      <TerminalLine key="liquidity-timeframe" label="Sweep timeframe" value={`${confirmationTimeframe} near ${liquidityPriceText}`} />,
      <TerminalLine key="poi" label="POI" value={candidate?.poiType ? `${candidate.poiType} ${candidate.entryZone ? `${formatPrice(candidate.entryZone.lower)} - ${formatPrice(candidate.entryZone.upper)}` : ''}` : 'NOT CONFIRMED'} />,
    ]},
    { section: 'STATUS', rows: [
      <TerminalLine key="status" value={`${candidate?.decisionState === 'READY' ? '🟢' : '⏳'} ${status}`} tone={candidate?.decisionState === 'READY' ? 'terminal-ready' : ''} />,
      ...(setupMissing.includes('LIQUIDITY_SWEEP') ? [<TerminalLine key="liquidity-wait" label="Waiting on" value={liquidityWaitingReason} />] : []),
    ] },
    ...(candidate?.score ? [{ section: 'SETUP SCORE', rows: [<TerminalLine key="score" value={`${candidate.score} / 100`} />] }] : []),
    ...(entryZone && signal?.stopLoss && signal.takeProfit ? [{ section: 'RISK ENGINE', rows: [
      <TerminalLine key="entry" label="Entry" value={formatPrice((entryZone.lower + entryZone.upper) / 2)} />,
      <TerminalLine key="sl" label="SL" value={formatPrice(signal.stopLoss)} />,
      <TerminalLine key="tp" label="TP" value={formatPrice(signal.takeProfit)} />,
      <TerminalLine key="tp1" label="TP1" value={formatPrice(tradeSetup?.takeProfit1)} />,
      <TerminalLine key="tp2" label="TP2" value={formatPrice(tradeSetup?.takeProfit2)} />,
      <TerminalLine key="volume" label="Volume" value={formatPrice(tradeSetup?.volume)} />,
      <TerminalLine key="risk" label="Risk" value={tradeSetup?.riskPercent ? `${tradeSetup.riskPercent}%` : '--'} />,
      <TerminalLine key="rr" label="R:R" value={signal.riskReward ? `1:${signal.riskReward.toFixed(1)}` : '--'} />,
      <TerminalLine key="target-reason" label="Target basis" value="TP1 = POI boundary; TP2 = projected 2R objective." />,
      <TerminalLine key="approved" value="✓ Risk approved" tone="terminal-pass" />,
    ] }] : []),
    ...(paperTrade ? [{ section: 'EXECUTIONER', rows: [
      <TerminalLine key="sending" value={`Sending ${paperTrade.direction ?? signal?.signal ?? 'NEUTRAL'} ${paperTrade.brokerSymbol ?? ''}`} />,
      <TerminalLine key="volume" label="Volume" value={String(paperTrade.volume ?? '--')} />,
      <TerminalLine key="entry" label="Entry" value={String(paperTrade.suggestedEntry ?? '--')} />,
      <TerminalLine key="sl" label="Stop loss" value={formatPrice(paperTrade.suggestedSL)} />,
      <TerminalLine key="tp" label="Take profit" value={formatPrice(paperTrade.suggestedTP)} />,
      <TerminalLine key="target-reason" label="Target basis" value="Uses the risk-engine projected target; broker receives the validated SL/TP setup." />,
      <TerminalLine key="accepted" value={paperTrade.status === 'PAPER_READY' ? '✓ Order accepted' : String(paperTrade.status ?? 'Order pending')} tone="terminal-pass" />,
    ] }] : []),
  ];
  const [visibleLines, setVisibleLines] = useState(0);
  const [changedSection, setChangedSection] = useState<string | null>(null);
  const initialRevealStarted = useRef(false);
  const lineCount = lines.reduce((total, group) => total + group.rows.length + (group.section ? 1 : 0), 0);
  const sectionSignatures = {
    MARKET: price,
    'HTF REGIME': regime,
    'XGBOOST MODEL': { modelStatus, mlPrediction },
    GATES: gates,
    'SCALP STATE': { direction: candidate?.direction, poi: candidate?.poiType, entryZone: candidate?.entryZone, missing: setupMissing },
    STATUS: { state: candidate?.decisionState, status },
    'SETUP SCORE': candidate?.score,
    'RISK ENGINE': { tradeSetup, stopLoss: signal?.stopLoss, takeProfit: signal?.takeProfit, riskReward: signal?.riskReward },
    EXECUTIONER: paperTrade,
  };
  const previousSignatures = useRef<Record<string, string>>({});

  useEffect(() => {
    if (initialRevealStarted.current) {
      setVisibleLines((current) => Math.max(current, lineCount));
      return;
    }
    initialRevealStarted.current = true;
    const timer = window.setInterval(() => setVisibleLines((current) => Math.min(current + 1, lineCount)), 180);
    return () => window.clearInterval(timer);
  }, [lineCount]);

  useEffect(() => {
    const changed = Object.entries(sectionSignatures).find(([section, value]) => {
      const signature = JSON.stringify(value);
      const previous = previousSignatures.current[section];
      previousSignatures.current[section] = signature;
      return previous !== undefined && previous !== signature;
    });
    if (!changed) return;
    setChangedSection(changed[0]);
    const timer = window.setTimeout(() => setChangedSection(null), 1400);
    return () => window.clearTimeout(timer);
  }, [JSON.stringify(sectionSignatures)]);

  let lineIndex = 0;
  return <div className="execution-terminal" aria-live="polite">
    {lines.map((group) => {
      const sectionVisible = lineIndex < visibleLines;
      if (group.section) lineIndex += 1;
      return <div className="execution-terminal-group" key={group.section || 'market'}>
        {group.section && <div className={`execution-terminal-section ${sectionVisible ? '' : 'terminal-hidden'} ${changedSection === group.section ? 'terminal-section-changed' : ''}`}>{group.section}{changedSection === group.section && <span className="terminal-updated"> UPDATED</span>}</div>}
        {group.rows.map((row) => { const visible = lineIndex++ < visibleLines; return <div className={visible ? '' : 'terminal-hidden'} key={row.key}>{row}</div>; })}
      </div>;
    })}
  </div>;
}

type InstrumentExecutionData = {
  instrument: string;
  account: AccountProfile | null;
  analysis: ExecutionAnalysis | null;
  signal: TradeSignal | null;
  loading: boolean;
  error: string | null;
};

export function Executioner() {
  const [accounts, setAccounts] = useState<AccountProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [instruments, setInstruments] = useState<string[]>(['XAUUSD']);
  const [instrumentData, setInstrumentData] = useState<Record<string, InstrumentExecutionData>>({});
  const [latestEvents, setLatestEvents] = useState<Record<string, string>>({});
  const [modelStatus, setModelStatus] = useState<{ version?: string | null; trainedAt?: string | null } | null>(null);
  const [paperPositions, setPaperPositions] = useState<Record<string, any>>({});
  const [executionAudit, setExecutionAudit] = useState<{ intents: Array<Record<string, unknown>>; attempts: Array<Record<string, unknown>>; positions: Array<Record<string, unknown>> }>({ intents: [], attempts: [], positions: [] });
  const [paperError, setPaperError] = useState<string | null>(null);
  const [isAddingInstrument, setIsAddingInstrument] = useState(false);
  const [instrumentDraft, setInstrumentDraft] = useState('');

  // Load accounts on mount
  useEffect(() => {
    authService.getModelStatus().then(setModelStatus).catch(() => setModelStatus(null));
  }, []);

  useEffect(() => {
    authService.getAccounts()
      .then(({ accounts: availableAccounts }) => setAccounts(availableAccounts))
      .catch(() => setError('Unable to load trading accounts.'))
      .finally(() => setLoading(false));
  }, []);

  const defaultAccount = useMemo(
    () => accounts.find((account) => account.isDefault && account.enabled) ?? accounts.find((account) => account.enabled),
    [accounts],
  );

  useEffect(() => {
    if (!defaultAccount) return;
    void authService.getExecutionAudit(defaultAccount.id, { limit: 8 })
      .then((audit) => setExecutionAudit(audit))
      .catch(() => setExecutionAudit({ intents: [], attempts: [], positions: [] }));
  }, [defaultAccount]);

  useEffect(() => {
    if (!defaultAccount) return;
    const stream = new EventSource(authService.getExecutionEventsUrl(defaultAccount.canonicalAsset || 'XAUUSD'), { withCredentials: true });
    const eventTypes = ['MARKET_UPDATE', 'REGIME_UPDATE', 'NEWS_SENTIMENT', 'NEWS_REACTION', 'NEWS_RISK', 'GATE_RESULT', 'SETUP_WAITING', 'SETUP_CONFIRMED', 'RISK_RESULT'];
    const handleEvent = (event: Event) => {
      const message = event as MessageEvent<string>;
      try {
        const payload = JSON.parse(message.data) as { type: string; data?: { status?: string; gate?: string; state?: string } };
        const detail = payload.data?.gate ?? payload.data?.status ?? payload.data?.state ?? payload.type;
        setLatestEvents((current) => ({ ...current, [defaultAccount.canonicalAsset || 'XAUUSD']: `${payload.type}: ${detail}` }));
      } catch {
        setLatestEvents((current) => ({ ...current, [defaultAccount.canonicalAsset || 'XAUUSD']: 'STREAM: INVALID EVENT' }));
      }
    };
    eventTypes.forEach((type) => stream.addEventListener(type, handleEvent));
    stream.onerror = () => setLatestEvents((current) => ({ ...current, [defaultAccount.canonicalAsset || 'XAUUSD']: 'STREAM: RECONNECTING' }));
    return () => {
      eventTypes.forEach((type) => stream.removeEventListener(type, handleEvent));
      stream.close();
    };
  }, [defaultAccount]);

  // Fetch execution data for each instrument
  useEffect(() => {
    if (!defaultAccount || instruments.length === 0) return;

    let cancelled = false;
    const abortControllers = new Map<string, AbortController>();

    const fetchInstrumentData = async (instrument: string) => {
      const controller = new AbortController();
      abortControllers.set(instrument, controller);

      setInstrumentData((prev) => {
        const current = prev[instrument] ?? {
          instrument,
          account: defaultAccount,
          analysis: null,
          signal: null,
          loading: false,
          error: null,
        };

        return {
          ...prev,
          [instrument]: {
            ...current,
            instrument,
            account: defaultAccount,
            loading: true,
            error: null,
          },
        };
      });

      try {
        // Fetch analysis and signals in parallel
        const [analysisResult, signalResult] = await Promise.all([
          authService.getOrchestrationAnalysis(defaultAccount.id),
          authService.getTradeSignals(defaultAccount.id),
        ]);

        if (!cancelled && !controller.signal.aborted) {
          setInstrumentData((prev) => {
            const current = prev[instrument] ?? {
              instrument,
              account: defaultAccount,
              analysis: null,
              signal: null,
              loading: false,
              error: null,
            };

            return {
              ...prev,
              [instrument]: {
                ...current,
                analysis: analysisResult,
                signal: signalResult,
                loading: false,
                error: analysisResult.status === 'ERROR' ? (analysisResult.reason ?? 'Execution analysis unavailable.') : null,
              },
            };
          });
        }
      } catch (err) {
        if (!cancelled && !controller.signal.aborted) {
          setInstrumentData((prev) => {
            const current = prev[instrument] ?? {
              instrument,
              account: defaultAccount,
              analysis: null,
              signal: null,
              loading: false,
              error: null,
            };

            return {
              ...prev,
              [instrument]: {
                ...current,
                loading: false,
                error: err instanceof Error ? err.message : 'Failed to fetch execution data',
              },
            };
          });
        }
      }
    };

    // Fetch data for all instruments
    instruments.forEach((instrument) => void fetchInstrumentData(instrument));

    // Refresh every 5 seconds
    const interval = window.setInterval(() => {
      instruments.forEach((instrument) => void fetchInstrumentData(instrument));
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
      abortControllers.forEach((controller) => controller.abort());
    };
  }, [defaultAccount, instruments]);

  useEffect(() => {
    if (!defaultAccount) return;
    const refresh = () => authService.getPaperPositions(defaultAccount.id).then(({ positions }) => {
      const active = positions.find((position) => ['ACTIVE', 'TP1_HIT'].includes(position.state));
      setPaperPositions((current) => ({ ...current, [defaultAccount.canonicalAsset || 'XAUUSD']: active }));
    }).catch(() => undefined);
    refresh();
    const interval = window.setInterval(refresh, 2000);
    return () => window.clearInterval(interval);
  }, [defaultAccount]);

  async function openPaperTrade() {
    if (!defaultAccount) return;
    setPaperError(null);
    try {
      const position = await authService.openPaperPosition(defaultAccount.id);
      setPaperPositions((current) => ({ ...current, [defaultAccount.canonicalAsset || 'XAUUSD']: position }));
    } catch (error) {
      setPaperError(error instanceof Error ? error.message : 'Paper position was not opened.');
    }
  }

  function addInstrument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const instrument = instrumentDraft.trim().toUpperCase();
    if (!instrument) return;

    const match = defaultAccount && (defaultAccount.canonicalAsset === instrument || defaultAccount.allowedInstruments.includes(instrument));
    if (!match) {
      setError(`No enabled default-account mapping was found for ${instrument}.`);
      return;
    }

    if (!instruments.includes(instrument)) {
      setInstruments((current) => [...current, instrument]);
    }
    setInstrumentDraft('');
    setIsAddingInstrument(false);
    setError(null);
  }

  const instrumentDetails = instruments.map((instrument) => {
    const data = instrumentData[instrument];
    const account = data?.account || defaultAccount;
    const analysis = data?.analysis;
    const signal = data?.signal;
    const isLoading = data?.loading;
    const dataError = data?.error;
    const latestEvent = latestEvents[instrument];
    const paperPosition = paperPositions[instrument];

    // Extract price data
    const currentPrice = analysis?.price?.ask ?? signal?.fullAnalysis?.price?.ask ?? null;
    const bid = analysis?.price?.bid ?? signal?.fullAnalysis?.price?.bid ?? null;
    const priceData = analysis?.price ?? signal?.fullAnalysis?.price;

    // Extract signal information
    const signalType = signal?.signal ?? 'NEUTRAL';
    const confidence = signal?.confidence ?? 0;
    const stopLoss = signal?.stopLoss;
    const takeProfit = signal?.takeProfit;
    const riskReward = signal?.riskReward;
    const entryZone = signal?.entryZone;

    // Extract structure information
    const m5Structure = analysis?.analysis?.m5?.structure ?? 'UNKNOWN';
    const m1Structure = analysis?.analysis?.m1?.structure ?? 'UNKNOWN';

    // Get decision stream
    const decisionStream = analysis?.decisionStream;

    return {
      instrument,
      account,
      analysis,
      signal,
      isLoading,
      dataError,
      currentPrice,
      bid,
      mt5Time: priceData?.mt5Time ?? priceData?.timestamp ?? null,
      receivedAt: priceData?.receivedAt ?? null,
      latencyMs: priceData?.latencyMs ?? null,
      signalType,
      confidence,
      stopLoss,
      takeProfit,
      riskReward,
      entryZone,
      m5Structure,
      m1Structure,
      decisionStream,
      latestEvent,
      paperPosition,
    };
  });

  return (
    <main className="dashboard-shell operational-page">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">EXECUTION PLANE / INSTRUMENTS</p>
          <h1>ATHENA / Executioner</h1>
        </div>
        {defaultAccount && <span className="account-chip">{defaultAccount.login} / {defaultAccount.displayName}</span>}
      </header>

      <section className="execution-intent-console" aria-label="Execution intent status">
        <div className="execution-intent-console-heading">
          <span>ORCHESTRATOR / EXECUTIONER BRIDGE</span>
          <span>{executionAudit.intents.length} intents / {executionAudit.attempts.length} attempts</span>
        </div>
        {executionAudit.intents.length === 0 ? <span className="execution-intent-empty">No persisted execution intent for this account.</span> : executionAudit.intents.slice(0, 3).map((intent) => (
          <div className="execution-intent-row" key={String(intent.id)}>
            <span className={`execution-intent-state intent-${String(intent.status).toLowerCase()}`}>{String(intent.status)}</span>
            <span>{String(intent.symbol)} / {String(intent.direction)} / {String(intent.strategy)}</span>
            <span>{String(intent.decisionId)}</span>
          </div>
        ))}
        {executionAudit.positions.length > 0 && <div className="execution-position-summary">BROKER POSITIONS: {executionAudit.positions.map((position) => `${String(position.ticket)} ${String(position.state)} ${String(position.direction)} ${String(position.volume)}`).join(' | ')}</div>}
      </section>

      <section className="execution-instrument-board" aria-label="Executioner instruments">
        <div className="execution-board-shell">
          {/* Header Row - Instrument Tabs */}
          <div className="execution-grid-row execution-grid-header">
            <div className="execution-left-handle">
              <button
                type="button"
                className="execution-plus"
                aria-label="Add instrument"
                title="Add instrument"
                onClick={() => setIsAddingInstrument((current) => !current)}
              >
                +
              </button>
              {isAddingInstrument && (
                <form className="execution-add-form" onSubmit={addInstrument}>
                  <input
                    aria-label="Instrument symbol"
                    value={instrumentDraft}
                    onChange={(event) => setInstrumentDraft(event.target.value)}
                    placeholder="e.g. EURUSD"
                    autoFocus
                  />
                  <button type="submit" className="instrument-action">Add</button>
                  <button type="button" className="instrument-action instrument-action-muted" onClick={() => setIsAddingInstrument(false)}>
                    Cancel
                  </button>
                </form>
              )}
            </div>

            {instrumentDetails.map(({ instrument, isLoading, dataError }) => (
              <div key={instrument} className="execution-tab-cell">
                <div className="execution-header-tab">
                  <span className="execution-symbol">{instrument}</span>
                  <span className={`execution-live-badge ${dataError ? 'status-error' : isLoading ? 'status-loading' : 'status-live'}`}>
                    {isLoading ? 'LOADING' : dataError ? 'ERROR' : 'LIVE'}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Mapping Row - Account & Real-Time Prices */}
          <div className="execution-grid-row execution-grid-mapping">
            <div className="execution-left-handle execution-left-label">MAP</div>
            {instrumentDetails.map(({ instrument, analysis, signal, account, paperPosition, latestEvent, isLoading, dataError }) => (
              <div key={`${instrument}-mapping`} className="execution-mapping-cell">
                {isLoading && !analysis ? <div className="execution-terminal-loading">Connecting to live analysis...</div> : dataError ? <div className="execution-terminal-error">{dataError}</div> : <ProgressiveAnalysis instrument={instrument} analysis={analysis} signal={signal} modelStatus={modelStatus} />}
                {latestEvent && <span className="execution-terminal-live-event">{latestEvent}</span>}
                {paperPosition && <span className="execution-terminal-live-event">PAPER {paperPosition.state}: {paperPosition.direction} {formatPrice(paperPosition.entry)} / SL {formatPrice(paperPosition.stop_loss)} / TP2 {formatPrice(paperPosition.take_profit2)}</span>}
                <span className="execution-terminal-source">{account?.brokerSymbol || 'Not mapped'} / {account?.login || 'No account'}</span>
              </div>
            ))}
          </div>

          {paperError && <p className="execution-error" role="alert">{paperError}</p>}
          <div className="paper-execution-actions"><button type="button" className="model-training-button" onClick={() => void openPaperTrade()} disabled={!defaultAccount || instrumentDetails.some((detail) => detail.paperPosition)} title="Open a risk-approved paper position">Open paper position</button></div>

          {/* Stream Row - Signals, SL/TP, Decision Context */}
          <div className="execution-grid-row execution-grid-stream">
            <div className="execution-left-handle execution-left-label">STREAM</div>
            {instrumentDetails.map(({ instrument, signalType, confidence, stopLoss, takeProfit, riskReward, entryZone, m5Structure, m1Structure, decisionStream, isLoading }) => (
              <div key={`${instrument}-stream`} className="execution-stream-cell">
                {isLoading ? (
                  <div className="execution-stream-block">
                    <span className="execution-stream-label">Analyzing...</span>
                  </div>
                ) : (
                  <>
                    {/* Signal Badge */}
                    <div className="execution-stream-block">
                      <span className="execution-stream-label">Signal:</span>
                      <span className={`execution-stream-value ${getSignalBadgeClass(signalType)}`}>
                        {signalType} ({Math.round(confidence * 100)}%)
                      </span>
                    </div>

                    {/* Structure Context */}
                    <div className="execution-stream-block">
                      <span className="execution-stream-label">Context:</span>
                      <small className="execution-context-label">
                        M5: {m5Structure} / M1: {m1Structure}
                      </small>
                    </div>

                    {/* SL/TP or Entry Zone */}
                    {stopLoss && takeProfit ? (
                      <div className="execution-stream-ticks">
                        <span>Entry: {formatPrice(entryZone?.lower)} - {formatPrice(entryZone?.upper)}</span>
                        <span>SL: {formatPrice(stopLoss)}</span>
                        <span>TP: {formatPrice(takeProfit)}</span>
                        {riskReward && <span>R:R: {riskReward.toFixed(2)}</span>}
                      </div>
                    ) : (
                      <div className="execution-stream-range">
                        Range: {entryZone ? `${formatPrice(entryZone.lower)} - ${formatPrice(entryZone.upper)}` : 'Awaiting setup'}
                      </div>
                    )}

                    {/* Decision Stream Summary */}
                    {decisionStream && (
                      <div className="execution-decision-stream">
                        <div className="decision-summary">
                          {decisionStream.whyTrade.length > 0 && (
                            <div className="decision-why-trade">
                              <span className="decision-label">✓ {decisionStream.whyTrade.length} reasons to trade</span>
                            </div>
                          )}
                          {decisionStream.whyNot.length > 0 && (
                            <div className="decision-why-not">
                              <span className="decision-label">✗ {decisionStream.whyNot.length} reasons to wait</span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>

        {loading && <p className="instrument-board-status">Loading default account mapping...</p>}
        {!loading && !defaultAccount && <p className="instrument-board-status">No enabled default account is available.</p>}
      </section>

      {error && <p className="execution-error" role="alert">{error}</p>}
    </main>
  );
}