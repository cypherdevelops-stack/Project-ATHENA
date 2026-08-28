import type { AuthSession } from '../types';

export type AccountProfile = {
  id: number;
  displayName: string;
  platform: string;
  login: string;
  broker: string;
  server: string;
  terminalPath: string;
  accountType: string;
  baseCurrency: string;
  leverage: number;
  enabled: boolean;
  isDefault: boolean;
  allowedInstruments: string[];
  canonicalAsset: string;
  brokerSymbol: string;
  marketDiscovery: MarketDiscovery;
  balance: string;
  equity: string;
  accountMode: string;
  tradeAllowed: boolean;
  terminalConnected: boolean;
  lastHandshakeAt: string | null;
  handshakeStatus: string;
  instrumentCapabilities: AccountInstrumentCapability[];
  riskPerTrade: string;
  maxDailyDrawdown: string;
  athenaSafetyDrawdown: string;
  maxOverallDrawdown: string;
  maxConcurrentPositions: number;
  liveExecutionEnabled: boolean;
  liveExecutionMode: string;
  allowedStrategies: string[];
  maxLiveOrdersPerDay: number;
  maxLiveRiskPerDay: string;
  maxOrderValue: string;
  requireFreshDecisionSeconds: number;
  reconciliationSafe: boolean;
  lastReconciliationAt: string | null;
  guardian: GuardianStatus;
};

export type GuardianStatus = {
  state: string;
  dailyDrawdown: string;
  dailyLimit: string;
  overallDrawdown: string;
  overallLimit: string;
  emergencyStop: boolean;
};

export type AccountInstrumentCapability = {
  canonicalAsset: string;
  brokerSymbol: string;
  symbolVisible: boolean;
  symbolSelected: boolean;
  tradeMode: number | null;
  executionMode: number | null;
  fillingModes: string[];
  orderModes: number | null;
  digits: number | null;
  point: string | null;
  tickSize: string | null;
  volumeMin: string | null;
  volumeMax: string | null;
  volumeStep: string | null;
  stopsLevel: number | null;
  freezeLevel: number | null;
  contractSize: string | null;
  lastDiscoveredAt: string;
};

export type AccountsResponse = {
  accounts: AccountProfile[];
};

export type AccountDiscovery = {
  broker: string;
  server: string;
  login: string;
  balance: string;
  currency: string;
  leverage: number;
  accountMode: string;
  platform: string;
  terminalConnected: boolean;
  tradeAllowed: boolean;
  marketData: string;
  existingPositions: number;
  executionValidation: string;
  canonicalAsset: string;
  brokerSymbol: string | null;
  marketDiscovery: MarketDiscovery;
};

export type MarketDiscovery = {
  canonicalAsset: string;
  brokerSymbol: string | null;
  symbols: Array<Record<string, unknown>>;
  assetMatches: string[];
  marketData: string;
};

export type DiscoveryResponse = {
  status: string;
  stage: string;
  completedStages: string[];
  discovery: AccountDiscovery;
};

export type PaperTrade = {
  accountId: number;
  accountName: string;
  canonicalAsset: string;
  brokerSymbol: string;
  direction: 'BUY' | 'SELL';
  entry: number;
  stopLoss: number;
  takeProfit: number;
  riskAmount: number;
  volume: number;
  fillingMode: string;
  status: string;
};

export type SmcScan = {
  status: string;
  accountId?: number;
  symbol?: string;
  timeframe?: 'M1' | 'M5';
  features?: { structure: string; events: Array<{ type: string; direction: string; level: number }>; orderBlocks: Array<{ direction: string; lowerBound: number; upperBound: number; strength: number }>; fairValueGaps: Array<{ direction: string; lowerBound: number; upperBound: number; strength: number }> };
  pois?: Array<{ id: number; type: string; direction: string; lowerBound: number; upperBound: number; strength: number; state: string; invalidationReason: string }>;
  reason?: string;
};

export type ScalpingCandidate = { candidateId: string; asset: string; brokerSymbol: string; module: string; direction: 'BUY' | 'SELL' | null; poiType: string | null; entryZone: { lower: number; upper: number } | null; regimeContext: string; decisionState: 'OBSERVE' | 'READY' | 'BLOCKED'; riskEligibility: boolean; reasonCodes: string[]; currentPrice: number; strength: number };
export type DecisionReason = { code: string; message: string };
export type DecisionStream = { events: Array<{ timestamp: number | null; type: 'ANALYSIS' | 'SYSTEM' | 'DECISION'; message: string }>; whyTrade: DecisionReason[]; whyNot: DecisionReason[] };
export type ScalpingCandidateScan = { status: string; accountId?: number; symbol?: string; candidates: ScalpingCandidate[]; decisionStream?: DecisionStream; reason?: string; reasonCodes?: string[] };
export type DayTradingState = { status: 'OBSERVE' | 'BLOCKED'; accountId?: number; module?: string; riskState?: { state: string; consecutiveLosses: number; dailyRiskUsed: string; cooldownUntil: string | null; sessionLocked: boolean }; reasonCodes?: string[] };

export type Mt5Health = {
  accounts: Array<{
    id: number;
    name: string;
    server: string;
    terminalConnected: boolean;
    tradeAllowed: boolean;
    balance: string;
    equity: string;
    handshakeStatus: string;
    lastHandshakeAt: string | null;
  }>;
};

export type MarketContext = {
  symbol?: string;
  bid?: number | null;
  ask?: number | null;
  timeframe?: string;
  candleCount?: number;
  latestCandle?: { time: number; open: number; high: number; low: number; close: number; volume: number } | null;
  regime?: { state: string; confidence: number; reason: string };
  status: string;
  reason?: string;
};

export type BacktestingMarketData = {
  status: 'HEALTHY' | 'UNAVAILABLE';
  reason?: string;
  accountId?: number;
  accountName?: string;
  canonicalAsset?: string;
  brokerSymbol?: string;
  timeframe?: string;
  candles?: Array<{ time: number; open: number; high: number; low: number; close: number; volume: number }>;
  price?: { bid: number; ask: number; spread: number; timestamp: string | null };
  receivedAt?: string;
};

export type SavedBacktestingDrawing = {
  id: number;
  type: 'trendline' | 'horizontal' | 'vertical' | 'ray' | 'rectangle' | 'triangle' | 'ellipse' | 'long_position' | 'short_position';
  start: { time: number; price: number };
  end?: { time: number; price: number } | null;
  symbol: string;
  timeframe: string;
  updatedAt: string;
};

export type ReplaySession = {
  id: number;
  accountId: number;
  symbol: string;
  timeframe: string;
  cursor: number;
  totalCandles: number;
  status: 'PAUSED' | 'PLAYING' | 'COMPLETE';
  speed: number;
  slippage: number;
  commission: number;
  currentTime?: number | null;
  candles: BacktestingMarketData['candles'];
  trades: ReplayTrade[];
};

export type ReplayTrade = {
  id: number;
  direction: 'BUY' | 'SELL';
  entry: number;
  stopLoss?: number | null;
  takeProfit?: number | null;
  volume: number;
  status: 'OPEN' | 'CLOSED';
  outcome: 'OPEN' | 'WIN' | 'LOSS' | 'BREAKEVEN';
  pnl: number;
  openedAt: number;
  exitPrice?: number | null;
  closedAt?: number | null;
  closeReason?: string;
  costs: number;
};

export type ReplayMetrics = { trades: number; wins: number; losses: number; winRate: number; netPnl: number; expectancy: number; profitFactor: number | null; maxDrawdown: number; ruleOnly: { trades: number; netPnl: number }; rulePlusMl: { trades: number; netPnl: number; note: string } };

export type HistoricalDataset = {
  id: number;
  accountId: number;
  source: string;
  symbol: string;
  timezone: string;
  timeframe: string;
  startTime: number;
  endTime: number;
  version: string;
  rowCount: number;
  filename?: string;
};

export type ReplayResponse = { session: ReplaySession; analysis: ExecutionAnalysis | Record<string, unknown>; signals: TradeSignal | Record<string, unknown>; metrics?: ReplayMetrics };

export type ExecutionGate = { name: string; status: 'PASS' | 'BLOCK'; reason: string };
export type ExecutionAnalysis = {
  status: string;
  reason?: string;
  analysis?: {
    timeframe?: string;
    m5?: { structure?: string; status?: string; events?: Array<Record<string, unknown>>; orderBlocks?: Array<Record<string, unknown>>; fairValueGaps?: Array<Record<string, unknown>> };
    m1?: { structure?: string; status?: string; events?: Array<Record<string, unknown>>; orderBlocks?: Array<Record<string, unknown>>; fairValueGaps?: Array<Record<string, unknown>> };
  };
  candidates?: Array<Record<string, unknown>>;
  scalping?: { status?: string; candidates?: Array<Record<string, unknown>> };
  dayTrading?: { status?: string; candidates?: Array<Record<string, unknown>> };
  decisionStream?: DecisionStream;
  regimeContext?: { structure?: string; structureReason?: string; macd?: string; macdReason?: string; volatility?: string; volatilityReason?: string; regime?: string; htf_bias?: string };
  price?: {
    symbol?: string;
    bid?: number | null;
    ask?: number | null;
    spread?: number | null;
    timestamp?: string | null;
    mt5Time?: string | null;
    receivedAt?: string | null;
    latencyMs?: number | null;
  };
  news?: NewsSentiment;
  newsReaction?: { expected_direction: string; actual_direction: string; state: string; price_change?: number | null; volatility: string; spread?: number | null; reason: string };
  executionConditions?: { allowed: boolean; reason: string; reasonCodes: string[] };
};

export type NewsSentiment = { provider_available: boolean; state: string; score: number; label: string; confidence: number; news_locked: boolean; reason: string; headlines?: Array<{ title: string; source: string; score: number; label: string; high_impact: boolean }>; events?: Array<Record<string, unknown>>; instruments?: Record<string, Record<string, unknown>>; adaptive_advice?: { status: string; expected_reaction: string; confidence: number; sample_count: number; confirmation_rate: number; reason: string } };

export type TradeSignal = {
  signal: 'BUY' | 'SELL' | 'NEUTRAL';
  confidence: number;
  entryZone?: { lower: number; upper: number } | null;
  stopLoss?: number | null;
  takeProfit?: number | null;
  riskReward?: number | null;
  reasoning?: string[];
  paperTrade?: Record<string, unknown> | null;
  fullAnalysis?: ExecutionAnalysis;
  tradeSetup?: { state: string; direction?: string | null; entry?: number | null; stopLoss?: number | null; takeProfit1?: number | null; takeProfit2?: number | null; volume?: number | null; riskPercent?: number | null; riskAmount?: number | null; riskReward?: number | null; score?: number; expiresAt?: string | null; evidence?: Record<string, boolean> };
};
export type PaperPosition = { position_id: string; account_id: number; symbol: string; direction: string; entry: number; stop_loss: number; take_profit1: number; take_profit2: number; volume: number; state: string; opened_at: string; closed_at?: string | null };
export type ModelTrainingResult = { status: string; jobId?: string; phase?: string; progress?: number; message?: string; samples?: number; positiveLabels?: number; features?: string[]; model?: string; trainedAt?: string; result?: { trainedAt?: string; samples?: number; positiveLabels?: number }; error?: string; reason?: string };
export type ModelStatus = { trained: boolean; trainedAt?: string | null; samples?: number; positiveLabels?: number; candleCount?: number; model?: string | null; version?: string | null; featureSchema?: string[]; trainingPeriod?: { from: number; to: number }; checksum?: string; validation?: { accuracy?: number; precision?: number; recall?: number; winRate?: number } };

export type JournalEvent = { id: number; eventType: string; body: string; createdAt: string };
export type JournalSession = { id: number; accountId: number | null; canonicalAsset: string; marketSession: string; regime: string; title: string; status: string; startedAt: string; updatedAt: string; events: JournalEvent[] };

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export function executionEventsUrl(symbol = 'XAUUSD') {
  return `${API_BASE_URL}/execution/events?symbol=${encodeURIComponent(symbol)}`;
}

function csrfToken() {
  const token = document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith('csrftoken='));
  return token ? decodeURIComponent(token.split('=').slice(1).join('=')) : '';
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.method && options.method !== 'GET' ? { 'X-CSRFToken': csrfToken() } : {}),
      ...options?.headers,
    },
    credentials: 'include',
    ...options,
  });

  if (!response.ok) {
    let detail = `Authentication request failed: ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string; reason?: string; message?: string };
      if (payload.detail || payload.reason || payload.message) {
        detail = payload.detail ?? payload.reason ?? payload.message ?? detail;
      }
    } catch {
      // Keep the status message when the backend does not return JSON.
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const authService = {
  getSession: () => request<AuthSession>('/auth/session'),
  login: (email: string, password: string) =>
    request<AuthSession>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  signup: (email: string, password: string, passwordConfirmation: string) =>
    request<AuthSession>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password, passwordConfirmation }),
    }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  requestPasswordReset: (email: string) =>
    request<{ detail: string }>('/auth/password-reset', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
  getAccount: () => request<AccountProfile>('/account/'),
  getAccounts: () => request<AccountsResponse>('/account/list'),
  setDefaultAccount: (accountId: number) => request<AccountProfile>('/account/default', { method: 'POST', body: JSON.stringify({ accountId }) }),
  getMt5Health: () => request<Mt5Health>('/account/mt5/health'),
  getMarketContext: (accountId?: number) => request<MarketContext>(`/market/context${accountId ? `?accountId=${accountId}` : ''}`),
  getBacktestingMarketData: (accountId?: number, timeframe = 'M5') => request<BacktestingMarketData>(`/backtesting/market-data?timeframe=${timeframe}${accountId ? `&accountId=${accountId}` : ''}`),
  getBacktestingDrawings: (accountId: number, timeframe: string, symbol?: string) => request<{ drawings: SavedBacktestingDrawing[] }>(`/backtesting/drawings?accountId=${accountId}&timeframe=${timeframe}${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ''}`),
  createBacktestingDrawing: (accountId: number, timeframe: string, payload: Pick<SavedBacktestingDrawing, 'type' | 'start' | 'end'>, symbol?: string) => request<SavedBacktestingDrawing>(`/backtesting/drawings?accountId=${accountId}&timeframe=${timeframe}${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ''}`, { method: 'POST', body: JSON.stringify(payload) }),
  clearBacktestingDrawings: (accountId: number, timeframe: string, symbol?: string) => request<void>(`/backtesting/drawings?accountId=${accountId}&timeframe=${timeframe}${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ''}`, { method: 'DELETE' }),
  createReplay: (accountId: number, timeframe: string, candleCount = 500) => request<ReplaySession>('/backtesting/replay', { method: 'POST', body: JSON.stringify({ accountId, timeframe, candleCount }) }),
  replayAction: (sessionId: number, action: 'step' | 'reset' | 'play' | 'pause' | 'execute', amount = 1) => request<ReplayResponse>(`/backtesting/replay?sessionId=${sessionId}`, { method: 'POST', body: JSON.stringify({ action, amount }) }),
  getHistoricalDatasets: (accountId?: number) => request<{ datasets: HistoricalDataset[] }>(`/backtesting/datasets${accountId ? `?accountId=${accountId}` : ''}`),
  uploadHistoricalDataset: async (accountId: number, file: File, options: { timeframe: string; timezone: string; symbol?: string; version?: string }) => {
    const form = new FormData();
    form.set('accountId', String(accountId)); form.set('timeframe', options.timeframe); form.set('timezone', options.timezone);
    if (options.symbol) form.set('symbol', options.symbol);
    if (options.version) form.set('version', options.version);
    form.set('file', file);
    const response = await fetch(`${API_BASE_URL}/backtesting/datasets`, { method: 'POST', body: form, credentials: 'include', headers: { 'X-CSRFToken': csrfToken() } });
    if (!response.ok) { const payload = await response.json().catch(() => ({})) as { detail?: string }; throw new Error(payload.detail ?? `Dataset upload failed: ${response.status}`); }
    return response.json() as Promise<HistoricalDataset>;
  },
  createDatasetReplay: (accountId: number, datasetId: number, startDate?: string, endDate?: string) => request<ReplaySession>('/backtesting/replay', { method: 'POST', body: JSON.stringify({ accountId, datasetId, startDate, endDate }) }),
  getExecutionAnalysis: (accountId?: number) => request<ExecutionAnalysis>(`/execution/analysis${accountId ? `?accountId=${accountId}` : ''}`),
  getOrchestrationAnalysis: (accountId?: number) => request<ExecutionAnalysis>(`/execution/orchestration${accountId ? `?accountId=${accountId}` : ''}`),
  getExecutionEventsUrl: executionEventsUrl,
  trainExecutionModel: (accountId?: number) => request<ModelTrainingResult>(`/execution/train-model${accountId ? `?accountId=${accountId}` : ''}`, { method: 'POST', body: JSON.stringify({}) }),
  getTrainingStatus: (jobId?: string) => request<ModelTrainingResult>(`/execution/train-model/status${jobId ? `?jobId=${encodeURIComponent(jobId)}` : ''}`),
  getModelStatus: () => request<ModelStatus>('/execution/model-status'),
  validateExecutionModel: () => request<ModelTrainingResult & { accuracy?: number; precision?: number; recall?: number; winRate?: number; validationSamples?: number }>('/execution/validate-model', { method: 'POST', body: JSON.stringify({}) }),
  getTradeSignals: (accountId?: number) => request<TradeSignal>(`/execution/signals${accountId ? `?accountId=${accountId}` : ''}`),
  getExecutionPrice: (accountId?: number) => request<{ status: string; bid?: number | null; ask?: number | null; spread?: number | null; timestamp?: string | null; symbol?: string; reason?: string }>(`/execution/price${accountId ? `?accountId=${accountId}` : ''}`),
  openPaperPosition: (accountId?: number) => request<PaperPosition>(`/execution/paper/position${accountId ? `?accountId=${accountId}` : ''}`, { method: 'POST', body: JSON.stringify({}) }),
  getPaperPositions: (accountId?: number) => request<{ positions: PaperPosition[] }>(`/execution/paper/positions${accountId ? `?accountId=${accountId}` : ''}`),
  sendLiveOrder: (accountId: number, idempotencyKey: string, maxSlippage = 0) => request<Record<string, unknown>>(`/execution/live/order?accountId=${accountId}`, { method: 'POST', body: JSON.stringify({ confirm: true, idempotencyKey, maxSlippage }) }),
  confirmDemoOrder: (decisionId: string, idempotencyKey: string, maxSlippage = 0) => request<Record<string, unknown>>('/execution/live/demo-order', { method: 'POST', body: JSON.stringify({ decisionId, confirm: true, idempotencyKey, maxSlippage }) }),
  getExecutionAudit: (accountId: number, options: { page?: number; limit?: number; eventType?: string; state?: string } = {}) => {
    const params = new URLSearchParams({ accountId: String(accountId), page: String(options.page ?? 1), limit: String(options.limit ?? 20) });
    if (options.eventType) params.set('eventType', options.eventType);
    if (options.state) params.set('state', options.state);
    return request<{ page: number; limit: number; eventCount: number; attemptCount: number; intentCount: number; events: Array<Record<string, unknown>>; attempts: Array<Record<string, unknown>>; intents: Array<Record<string, unknown>>; positions: Array<Record<string, unknown>> }>(`/execution/audit?${params.toString()}`);
  },
  reconcileExecution: (accountId: number) => request<Record<string, unknown>>('/execution/reconcile', { method: 'POST', body: JSON.stringify({ accountId }) }),
  getJournalSessions: () => request<{ sessions: JournalSession[] }>('/journal/sessions'),
  createJournalSession: (payload: { accountId?: number; canonicalAsset?: string; regime?: string; title?: string }) =>
    request<JournalSession>('/journal/sessions/create', { method: 'POST', body: JSON.stringify(payload) }),
  createJournalEvent: (sessionId: number, payload: { eventType: string; body: string }) =>
    request<JournalEvent>(`/journal/sessions/${sessionId}/events`, { method: 'POST', body: JSON.stringify(payload) }),
  createAccount: (account: { accountNickname: string; platform: string; login: string; password: string; server: string; canonicalAsset?: string; brokerSymbol?: string; marketDiscovery?: MarketDiscovery; allowedInstruments?: string[] }) =>
    request<AccountProfile>('/account/create', {
      method: 'POST',
      body: JSON.stringify(account),
    }),
  discoverAccount: (account: { platform: string; login: string; password: string; server: string }) =>
    request<DiscoveryResponse>('/account/onboarding/discover', {
      method: 'POST',
      body: JSON.stringify(account),
    }),
  getGuardian: () => request<GuardianStatus>('/account/guardian'),
  createPaperTrade: (accountId: number) =>
    request<PaperTrade>('/account/paper-trade', {
      method: 'POST',
      body: JSON.stringify({ accountId }),
    }),
  scanSmc: (accountId: number, timeframe: 'M1' | 'M5') => request<SmcScan>(`/smc/scan?accountId=${accountId}&timeframe=${timeframe}`),
  scanScalpingCandidates: (accountId: number) => request<ScalpingCandidateScan>(`/strategies/scalping/candidates?accountId=${accountId}`),
  getDayTradingState: (accountId: number) => request<DayTradingState>(`/strategies/day-trading/state?accountId=${accountId}`),
  updateAccount: (updates: Record<string, unknown> & { accountId?: number }) =>
    request<AccountProfile>('/account/update', {
      method: 'PATCH',
      body: JSON.stringify(updates),
    }),
  deleteAccount: (accountId: number) =>
    request<void>('/account/delete', {
      method: 'DELETE',
      body: JSON.stringify({ id: accountId }),
    }),
};
