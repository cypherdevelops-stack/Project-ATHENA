import React, { useEffect, useState } from 'react';
import './orchestration.css';
import { authService } from '../authentication/services/authService';

interface OrchestratorState {
  decisionId: string | null;
  regime: string;
  scalping_status: string;
  scalping_direction: string | null;
  scalping_score: number;
  scalping_confidence: number;
  day_trading_status: string;
  day_trading_direction: string | null;
  day_trading_score: number;
  day_trading_confidence: number;
  risk_available: boolean;
  daily_drawdown_pct: number;
  decision: string;
  decision_reason: string;
  reason_codes: string[];
  setup: Record<string, unknown> | null;
  price: {
    symbol: string;
    bid: number;
    ask: number;
    spread: number;
  };
  execution: Record<string, unknown> | null;
}

interface WebSocketMessage {
  type: string;
  payload?: Record<string, unknown>;
  severity?: string;
  alert_type?: string;
  title?: string;
  message?: string;
  timestamp?: string;
}

function toDashboardState(payload: Record<string, unknown>): OrchestratorState | null {
  const orchestration = (payload.orchestration as Record<string, unknown> | undefined) ?? payload;
  const dayTrading = (orchestration.day_engine as Record<string, unknown> | undefined) ?? {};
  const scalping = (orchestration.scalping_engine as Record<string, unknown> | undefined) ?? {};
  const portfolio = (orchestration.portfolio as Record<string, unknown> | undefined) ?? {};
  const decision = orchestration.decision;
  const price = (payload.price as Record<string, unknown> | undefined) ?? {};
  const decisionPayload = typeof decision === 'object' && decision !== null ? decision as Record<string, unknown> : {};

  if (typeof orchestration.market_regime !== 'string' || typeof price.bid !== 'number' || typeof price.ask !== 'number') {
    return null;
  }

  return {
    decisionId: String(payload.decisionId ?? decisionPayload.decisionId ?? '') || null,
    regime: orchestration.market_regime,
    scalping_status: String(scalping.status ?? 'OBSERVE'),
    scalping_direction: (scalping.direction as string | null | undefined) ?? null,
    scalping_score: Number(scalping.confidence ?? 0),
    scalping_confidence: Number(scalping.confidence ?? 0),
    day_trading_status: String(dayTrading.status ?? 'OBSERVE'),
    day_trading_direction: (dayTrading.direction as string | null | undefined) ?? null,
    day_trading_score: Number(dayTrading.confidence ?? 0),
    day_trading_confidence: Number(dayTrading.confidence ?? 0),
    risk_available: Boolean(portfolio.risk_available),
    daily_drawdown_pct: Number(portfolio.daily_drawdown_pct ?? 0),
    decision: typeof decision === 'object' && decision !== null
      ? String(decisionPayload.action ?? orchestration.status ?? 'OBSERVE')
      : String(decision ?? orchestration.status ?? 'OBSERVE'),
    decision_reason: typeof decision === 'object' && decision !== null
      ? String(decisionPayload.reason ?? orchestration.reason ?? '')
      : String(orchestration.reason ?? ''),
    reason_codes: Array.isArray(decisionPayload.reasonCodes) ? decisionPayload.reasonCodes.map(String) : [],
    setup: (decisionPayload.setup as Record<string, unknown> | null | undefined) ?? null,
    price: {
      symbol: String(price.symbol ?? 'XAUUSD'),
      bid: price.bid,
      ask: price.ask,
      spread: Number(price.spread ?? 0),
    },
    execution: (payload.execution as Record<string, unknown> | undefined) ?? null,
  };
}

export const OrchestratorDashboard: React.FC<{ accountId?: number }> = ({ accountId }) => {
  const [state, setState] = useState<OrchestratorState | null>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [dataError, setDataError] = useState<string | null>(null);
  const [activeAccountId, setActiveAccountId] = useState<number | undefined>(accountId);
  const [accountProfile, setAccountProfile] = useState<Awaited<ReturnType<typeof authService.getAccounts>>['accounts'][number] | null>(null);
  const [executionResult, setExecutionResult] = useState<Record<string, unknown> | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [audit, setAudit] = useState<{ page: number; limit: number; eventCount: number; attemptCount: number; intentCount: number; events: Array<Record<string, unknown>>; attempts: Array<Record<string, unknown>>; intents: Array<Record<string, unknown>>; positions: Array<Record<string, unknown>> }>({ page: 1, limit: 20, eventCount: 0, attemptCount: 0, intentCount: 0, events: [], attempts: [], intents: [], positions: [] });
  const [auditPage, setAuditPage] = useState(1);
  const [auditStateFilter, setAuditStateFilter] = useState('');
  const [reconciling, setReconciling] = useState(false);

  useEffect(() => {
    setActiveAccountId(accountId);
    if (accountId === undefined) {
      void authService.getAccounts().then(({ accounts }) => {
        const selected = accounts.find((item) => item.id === accountId) ?? accounts.find((item) => item.isDefault && item.enabled) ?? accounts.find((item) => item.enabled);
        setAccountProfile(selected ?? null);
        setActiveAccountId(selected?.id);
      }).catch(() => setActiveAccountId(undefined));
    } else {
      void authService.getAccounts().then(({ accounts }) => {
        setAccountProfile(accounts.find((item) => item.id === accountId) ?? null);
      }).catch(() => setAccountProfile(null));
    }
  }, [accountId]);

  useEffect(() => {
    if (activeAccountId === undefined) return;
    void authService.getExecutionAudit(activeAccountId, { page: auditPage, state: auditStateFilter || undefined }).then(setAudit).catch(() => setAudit({ page: auditPage, limit: 20, eventCount: 0, attemptCount: 0, intentCount: 0, events: [], attempts: [], intents: [], positions: [] }));
  }, [activeAccountId, executionResult, auditPage, auditStateFilter]);

  useEffect(() => {
    // Connect to WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = activeAccountId
      ? `${protocol}//${window.location.host}/ws/orchestration/XAUUSD/${activeAccountId}/`
      : `${protocol}//${window.location.host}/ws/orchestration/XAUUSD/`;

    const websocket = new WebSocket(wsUrl);

    async function fetchAnalysis() {
      const accountQuery = activeAccountId ? `?accountId=${activeAccountId}` : '';
      try {
        const response = await fetch(`/api/execution/orchestration${accountQuery}`, { credentials: 'include' });
        if (!response.ok) {
          const errorPayload = await response.json().catch(() => ({})) as { reason?: string; detail?: string };
          setDataError(errorPayload.reason ?? errorPayload.detail ?? `Orchestration request failed (${response.status})`);
          return;
        }
        const payload = await response.json() as Record<string, unknown>;
        const nextState = toDashboardState(payload);
        if (nextState) {
          setState(nextState);
          setLastUpdate(new Date());
          setDataError(null);
        }
      } catch {
        setDataError('Unable to reach the orchestration API.');
      }
    }

    void fetchAnalysis();
    const pollTimer = window.setInterval(() => void fetchAnalysis(), 15000);

    websocket.onopen = () => {
      setConnected(true);
      console.log('WebSocket connected');
    };

    websocket.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      if (message.type === 'orchestration_update' && message.payload) {
        const nextState = toDashboardState(message.payload);
        if (nextState) {
          setState(nextState);
          setLastUpdate(new Date());
          setDataError(null);
        }
      } else if (message.type === 'alert') {
        setAlerts(prev => [
          {
            severity: message.severity,
            alert_type: message.alert_type,
            title: message.title,
            message: message.message,
            timestamp: message.timestamp,
            id: Date.now(),
          },
          ...prev.slice(0, 9), // Keep last 10 alerts
        ]);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnected(false);
    };

    websocket.onclose = () => {
      setConnected(false);
      console.log('WebSocket closed');
    };

    return () => {
      window.clearInterval(pollTimer);
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.close();
      }
    };
  }, [activeAccountId]);

  async function confirmDemoOrder() {
    if (!state?.decisionId) return;
    setConfirming(true);
    setExecutionError(null);
    setExecutionResult(null);
    try {
      const idempotencyKey = typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : `${state.decisionId}-${Date.now()}`;
      setExecutionResult(await authService.confirmDemoOrder(state.decisionId, idempotencyKey));
    } catch (error) {
      setExecutionError(error instanceof Error ? error.message : 'Demo order was rejected.');
    } finally {
      setConfirming(false);
    }
  }

  async function refreshReconciliation() {
    if (activeAccountId === undefined) return;
    setReconciling(true);
    try {
      await authService.reconcileExecution(activeAccountId);
      setAccountProfile((await authService.getAccounts()).accounts.find((item) => item.id === activeAccountId) ?? null);
      setAuditPage(1);
      setAudit(await authService.getExecutionAudit(activeAccountId, { state: auditStateFilter || undefined }));
    } catch (error) {
      setExecutionError(error instanceof Error ? error.message : 'Reconciliation failed.');
    } finally {
      setReconciling(false);
    }
  }

  if (!state) {
    return (
      <div className="orchestrator-dashboard loading">
        <div className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? 'Connected - waiting for orchestration data' : 'Disconnected'}
        </div>
        {dataError && <p className="orchestration-data-error" role="alert">{dataError}</p>}
      </div>
    );
  }

  const regimeEmoji = {
    TRENDING_BULLISH: '📈',
    TRENDING_BEARISH: '📉',
    VOLATILE: '⚡',
    RANGING: '↔️',
    UNKNOWN: '❓',
  }[state.regime] || '?';

  const decisionEmoji = {
    SCALP_LONG_APPROVED: '🟢',
    SCALP_SHORT_APPROVED: '🔴',
    DAY_BUY_DEVELOPING: '🟡',
    DAY_SELL_DEVELOPING: '🟡',
    OBSERVE: '⏸️',
    BLOCKED: '⛔',
  }[state.decision] || '⚪';

  return (
    <div className="orchestrator-dashboard">
      {/* Status Bar */}
      <div className="status-bar">
        <div className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '● Live' : '○ Offline'}
        </div>
        <div className="last-update">
          {lastUpdate && `Updated: ${lastUpdate.toLocaleTimeString()}`}
        </div>
      </div>

      {/* Main Grid */}
      <div className="main-grid">
        {/* Market Price */}
        <section className="market-section">
          <h3>{state.price.symbol}</h3>
          <div className="price-display">
            <div className="price-row">
              <span className="label">Bid</span>
              <span className="value">{state.price.bid.toFixed(2)}</span>
            </div>
            <div className="price-row">
              <span className="label">Ask</span>
              <span className="value">{state.price.ask.toFixed(2)}</span>
            </div>
            <div className="price-row spread">
              <span className="label">Spread</span>
              <span className="value">{state.price.spread.toFixed(5)}</span>
            </div>
          </div>
        </section>

        {/* Regime */}
        <section className="regime-section">
          <h3>Market Regime</h3>
          <div className="regime-display">
            <span className="regime-emoji">{regimeEmoji}</span>
            <span className="regime-text">{state.regime}</span>
          </div>
        </section>

        {/* Scalping Engine */}
        <section className="strategy-section scalping">
          <h3>Scalping Engine</h3>
          <div className="strategy-content">
            <div className="row">
              <span className="label">Status</span>
              <span className={`status ${state.scalping_status.toLowerCase()}`}>
                {state.scalping_status}
              </span>
            </div>
            <div className="row">
              <span className="label">Direction</span>
              <span className="value">{state.scalping_direction || '—'}</span>
            </div>
            <div className="row">
              <span className="label">Score</span>
              <div className="progress-bar">
                <div className="progress" style={{ width: `${state.scalping_score}%` }}></div>
                <span className="label-overlay">{state.scalping_score}/100</span>
              </div>
            </div>
            <div className="row">
              <span className="label">Confidence</span>
              <span className="value">{state.scalping_confidence.toFixed(0)}%</span>
            </div>
          </div>
        </section>

        {/* Day Trading Engine */}
        <section className="strategy-section day-trading">
          <h3>Day Trading Engine</h3>
          <div className="strategy-content">
            <div className="row">
              <span className="label">Status</span>
              <span className={`status ${state.day_trading_status.toLowerCase()}`}>
                {state.day_trading_status}
              </span>
            </div>
            <div className="row">
              <span className="label">Direction</span>
              <span className="value">{state.day_trading_direction || '—'}</span>
            </div>
            <div className="row">
              <span className="label">Score</span>
              <div className="progress-bar">
                <div className="progress" style={{ width: `${state.day_trading_score}%` }}></div>
                <span className="label-overlay">{state.day_trading_score}/100</span>
              </div>
            </div>
            <div className="row">
              <span className="label">Confidence</span>
              <span className="value">{state.day_trading_confidence.toFixed(0)}%</span>
            </div>
          </div>
        </section>

        {/* Portfolio */}
        <section className="portfolio-section">
          <h3>Portfolio</h3>
          <div className="portfolio-content">
            <div className="row">
              <span className="label">Risk Available</span>
              <span className={`status ${state.risk_available ? 'available' : 'unavailable'}`}>
                {state.risk_available ? '✓ Yes' : '✗ No'}
              </span>
            </div>
            <div className="row">
              <span className="label">Daily Drawdown</span>
              <span className={`value ${state.daily_drawdown_pct > 2 ? 'warning' : ''}`}>
                {state.daily_drawdown_pct.toFixed(2)}%
              </span>
            </div>
          </div>
        </section>

        <section className="policy-section">
          <h3>Execution Policy</h3>
          <div className="policy-content">
            <div className="row">
              <span className="label">Mode</span>
              <span className={`status ${accountProfile?.liveExecutionMode === 'AUTOMATIC' ? 'warning' : 'available'}`}>
                {accountProfile?.liveExecutionMode ?? 'UNKNOWN'}
              </span>
            </div>
            <div className="row">
              <span className="label">Server switch</span>
              <span className={`status ${accountProfile?.liveExecutionEnabled ? 'available' : 'unavailable'}`}>
                {accountProfile?.liveExecutionEnabled ? 'ENABLED' : 'DISABLED'}
              </span>
            </div>
            <div className="row">
              <span className="label">Strategies</span>
              <span className="value">{accountProfile?.allowedStrategies.join(', ') || 'None'}</span>
            </div>
            <div className="row">
              <span className="label">Reconciliation</span>
              <span className={`status ${accountProfile?.reconciliationSafe ? 'available' : 'unavailable'}`}>
                {accountProfile?.reconciliationSafe ? 'SAFE' : 'HALTED'}
              </span>
            </div>
            <div className="row">
              <span className="label">Last broker sync</span>
              <span className="value">{accountProfile?.lastReconciliationAt ? new Date(accountProfile.lastReconciliationAt).toLocaleTimeString() : 'Not run'}</span>
            </div>
            <button type="button" className="reconcile-button" onClick={() => void refreshReconciliation()} disabled={reconciling || activeAccountId === undefined}>
              {reconciling ? 'Reconciling...' : 'Refresh broker reconciliation'}
            </button>
            {accountProfile?.guardian.emergencyStop && <div className="halt-banner" role="alert">Emergency stop active. New execution is halted.</div>}
          </div>
        </section>

        {/* Decision */}
        <section className="decision-section">
          <h3>Decision</h3>
          <div className="decision-display">
            <span className="decision-emoji">{decisionEmoji}</span>
            <div className="decision-text">
              <h4>{state.decision}</h4>
              <p>{state.decision_reason}</p>
              <div className="decision-metadata">
                <span>Decision ID: {state.decisionId ?? 'Unavailable'}</span>
                <span>Reasons: {state.reason_codes.join(', ') || 'None reported'}</span>
              </div>
              {state.setup && <div className="setup-summary">
                <strong>Validated setup</strong>
                <span>{String(state.setup.direction)} {String(state.setup.symbol)} | Entry {Number(state.setup.entry).toFixed(2)}</span>
                <span>SL {Number(state.setup.stopLoss).toFixed(2)} | TP2 {Number(state.setup.takeProfit2).toFixed(2)} | Volume {String(state.setup.volume)}</span>
              </div>}
              {state.decision.endsWith('_APPROVED') && state.decisionId && accountProfile?.liveExecutionMode === 'CONFIRMATION_REQUIRED' && (
                <button type="button" className="demo-execution-button" onClick={() => void confirmDemoOrder()} disabled={confirming}>
                  {confirming ? 'Submitting demo order...' : 'Confirm demo order'}
                </button>
              )}
              {executionResult && <p className="execution-result" role="status">Demo execution: {String(executionResult.status)} {executionResult.order ? `(Order ${String(executionResult.order)})` : ''}</p>}
              {executionError && <p className="orchestration-data-error" role="alert">{executionError}</p>}
            </div>
          </div>
        </section>
      </div>

      <section className="audit-section">
        <div className="audit-header">
          <h3>Execution Audit</h3>
          <span>{audit.intentCount} intents · {audit.attemptCount} attempts · {audit.eventCount} events</span>
        </div>
        <div className="audit-controls">
          <label>State <select value={auditStateFilter} onChange={(event) => { setAuditStateFilter(event.target.value); setAuditPage(1); }}><option value="">All</option><option value="SUBMITTING">Submitting</option><option value="ACCEPTED">Accepted</option><option value="REJECTED">Rejected</option><option value="ACTIVE">Active</option><option value="CLOSED">Closed</option><option value="RECONCILIATION_REQUIRED">Reconciliation required</option></select></label>
          <button type="button" onClick={() => setAuditPage((page) => Math.max(1, page - 1))} disabled={auditPage === 1}>Previous</button>
          <span>Page {auditPage}</span>
          <button type="button" onClick={() => setAuditPage((page) => page + 1)} disabled={auditPage * audit.limit >= Math.max(audit.eventCount, audit.attemptCount)}>Next</button>
        </div>
        {audit.intents.length > 0 && <div className="intent-strip">{audit.intents.map((intent) => <span key={String(intent.id)}>INTENT {String(intent.status)} · {String(intent.strategy)} {String(intent.direction)} · {String(intent.symbol)}</span>)}</div>}
        {audit.attempts.length === 0 ? <p className="audit-empty">No broker attempts recorded.</p> : (
          <div className="audit-table-wrap">
            <table className="audit-table">
              <thead><tr><th>Status</th><th>Strategy</th><th>Order</th><th>Deal</th><th>Reason</th><th>Time</th></tr></thead>
              <tbody>{audit.attempts.map((attempt) => <tr key={String(attempt.id)}>
                <td><span className={`audit-status audit-${String(attempt.status).toLowerCase()}`}>{String(attempt.status)}</span></td>
                <td>{String(attempt.strategy)}</td>
                <td>{attempt.order ? String(attempt.order) : '—'}</td>
                <td>{attempt.deal ? String(attempt.deal) : '—'}</td>
                <td>{String(attempt.reason || '—')}</td>
                <td>{new Date(String(attempt.createdAt)).toLocaleTimeString()}</td>
              </tr>)}</tbody>
            </table>
          </div>
        )}
        {audit.events.length > 0 && <div className="event-strip">{audit.events.slice(0, 8).map((event) => <span key={String(event.id)}>{String(event.type)} · {new Date(String(event.createdAt)).toLocaleTimeString()}</span>)}</div>}
        {audit.positions.length > 0 && <div className="position-table-wrap"><h4>Broker Positions</h4><table className="audit-table"><thead><tr><th>State</th><th>Ticket</th><th>Direction</th><th>Volume</th><th>Open</th><th>SL / TP</th><th>Observed</th></tr></thead><tbody>{audit.positions.map((position) => <tr key={String(position.ticket)}><td><span className={`audit-status audit-${String(position.state).toLowerCase()}`}>{String(position.state)}</span></td><td>{String(position.ticket)}</td><td>{String(position.direction)}</td><td>{String(position.volume)}</td><td>{String(position.priceOpen)}</td><td>{String(position.stopLoss)} / {String(position.takeProfit)}</td><td>{new Date(String(position.observedAt)).toLocaleTimeString()}</td></tr>)}</tbody></table></div>}
      </section>

      {/* Alerts */}
      {alerts.length > 0 && (
        <section className="alerts-section">
          <h3>Recent Alerts</h3>
          <div className="alerts-list">
            {alerts.map((alert) => (
              <div key={alert.id} className={`alert alert-${alert.severity.toLowerCase()}`}>
                <div className="alert-header">
                  <span className="alert-type">{alert.alert_type}</span>
                  <span className="alert-time">
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="alert-title">{alert.title}</div>
                <div className="alert-message">{alert.message}</div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

export default OrchestratorDashboard;
