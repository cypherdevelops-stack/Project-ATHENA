import { useEffect, useState } from 'react';
import { Bell, BrainCircuit, X } from 'lucide-react';
import { authService, type AccountProfile, type MarketContext, type Mt5Health } from '../authentication/services/authService';
export function Dashboard() {
  const [health, setHealth] = useState<Mt5Health | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [marketContext, setMarketContext] = useState<MarketContext | null>(null);
  const [accounts, setAccounts] = useState<AccountProfile[]>([]);
  const [defaultAccountId, setDefaultAccountId] = useState<number | null>(null);
  const [defaultAccountError, setDefaultAccountError] = useState<string | null>(null);
  const [training, setTraining] = useState(false);
  const [trainingResult, setTrainingResult] = useState<string | null>(null);
  const [trainingJob, setTrainingJob] = useState<Awaited<ReturnType<typeof authService.getTrainingStatus>> | null>(null);
  const [modelStatus, setModelStatus] = useState<Awaited<ReturnType<typeof authService.getModelStatus>> | null>(null);
  const [showTrainingModal, setShowTrainingModal] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<{ accuracy?: number; precision?: number; recall?: number; winRate?: number; validationSamples?: number; reason?: string } | null>(null);

  useEffect(() => {
    let active = true;
    const refresh = () => authService.getMt5Health()
      .then((result) => { if (active) { setHealth(result); setHealthError(false); } })
      .catch(() => { if (active) setHealthError(true); });
    refresh();
    const interval = window.setInterval(refresh, 2000);
    return () => { active = false; window.clearInterval(interval); };
  }, []);

  useEffect(() => {
    authService.getAccounts().then(({ accounts: availableAccounts }) => {
      setAccounts(availableAccounts);
      setDefaultAccountId(availableAccounts.find((account) => account.isDefault)?.id ?? availableAccounts[0]?.id ?? null);
    }).catch(() => setDefaultAccountError('Accounts unavailable.'));
  }, []);

  useEffect(() => {
    authService.getModelStatus().then((result) => {
      setModelStatus(result);
      if (!result.trained) setShowTrainingModal(true);
    }).catch(() => setModelStatus({ trained: false }));
  }, []);

  async function selectDefaultAccount(accountId: number) {
    try {
      const updated = await authService.setDefaultAccount(accountId);
      setAccounts((current) => current.map((account) => account.id === updated.id ? updated : { ...account, isDefault: false }));
      setDefaultAccountId(updated.id);
      setDefaultAccountError(null);
    } catch {
      setDefaultAccountError('Unable to set the default account.');
    }
  }

  async function trainModel() {
    if (!defaultAccountId || training) return;
    setTraining(true);
    setTrainingResult(null);
    try {
      const result = await authService.trainExecutionModel(defaultAccountId);
      setTrainingJob(result);
    } catch (error) {
      setTrainingResult(error instanceof Error ? error.message : 'Model training failed.');
      setTraining(false);
    }
  }

  async function validateModel() {
    if (validating || !modelStatus?.trained) return;
    setValidating(true);
    try {
      setValidationResult(await authService.validateExecutionModel());
    } catch (error) {
      setValidationResult({ reason: error instanceof Error ? error.message : 'Validation failed.' });
    } finally {
      setValidating(false);
    }
  }

  useEffect(() => {
    if (!trainingJob?.jobId || ['COMPLETE', 'ERROR'].includes(trainingJob.phase ?? '')) return;
    const refresh = () => authService.getTrainingStatus(trainingJob.jobId).then((result) => {
      setTrainingJob(result);
      if (result.phase === 'COMPLETE') {
        setTraining(false);
        setTrainingResult(`Model active / ${result.result?.samples ?? 0} samples / ${result.result?.positiveLabels ?? 0} positive outcomes`);
        authService.getModelStatus().then(setModelStatus);
      } else if (result.phase === 'ERROR') {
        setTraining(false);
        setTrainingResult(result.error ?? result.message ?? 'Model training failed.');
      }
    }).catch(() => { setTraining(false); setTrainingResult('Unable to read training progress.'); });
    refresh();
    const interval = window.setInterval(refresh, 700);
    return () => window.clearInterval(interval);
  }, [trainingJob?.jobId, trainingJob?.phase]);

  function formatTrainingDate(value?: string | null) {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
  }

  useEffect(() => {
    authService.getMarketContext()
      .then(setMarketContext)
      .catch(() => setMarketContext({ status: 'UNAVAILABLE', reason: 'Market context is unavailable.' }));
  }, []);

  const healthAccounts = health?.accounts ?? [];
  const connected = healthAccounts.filter((account) => account.terminalConnected).length;
  const trading = healthAccounts.filter((account) => account.terminalConnected && account.tradeAllowed).length;
  const credentialsBlocked = healthAccounts.length > 0 && healthAccounts.every((account) => account.handshakeStatus === 'CREDENTIALS_UNAVAILABLE');
  const status = healthError ? 'UNAVAILABLE' : credentialsBlocked ? 'CREDENTIALS REQUIRED' : connected === healthAccounts.length && healthAccounts.length > 0 ? 'CONNECTED' : connected > 0 ? 'PARTIAL' : 'RECONNECTING';
  const recoveryState = (account: Mt5Health['accounts'][number]) => {
    if (account.terminalConnected && account.tradeAllowed) return { label: 'READY', progress: 100, tone: 'good', detail: 'MT5 connected and trading enabled.' };
    if (account.handshakeStatus === 'CREDENTIALS_UNAVAILABLE') return { label: 'CREDENTIALS REQUIRED', progress: 0, tone: 'warn', detail: 'Reconnect is paused until broker credentials are available.' };
    if (account.handshakeStatus === 'AUTH_FAILED') return { label: 'AUTHENTICATION FAILED', progress: 25, tone: 'warn', detail: 'The terminal is open, but the account login was rejected.' };
    if (account.handshakeStatus === 'RECONNECTING') return { label: 'RECONNECTING', progress: 50, tone: 'warn', detail: 'Launching MT5 and waiting for the next connection attempt.' };
    if (account.handshakeStatus === 'RECONNECT_FAILED') return { label: 'RECONNECT FAILED', progress: 0, tone: 'warn', detail: 'The configured MT5 terminal could not be launched. Check the terminal path.' };
    if (account.terminalConnected) return { label: 'CONNECTED / BLOCKED', progress: 75, tone: 'warn', detail: 'MT5 is connected, but trading permission is unavailable.' };
    return { label: 'CHECKING', progress: 10, tone: 'warn', detail: 'Waiting for the MT5 monitor.' };
  };

  return (
    <main className="dashboard-shell">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">PROJECT ATHENA / v2.7</p>
          <h1>Trading OS</h1>
        </div>
        <button type="button" className="notification-button" aria-label="Notifications" title="Notifications">
          <Bell size={20} strokeWidth={1.8} aria-hidden="true" />
        </button>
      </header>
      <section className="dashboard-intro">
        <p className="eyebrow">PHASE 1 / FOUNDATION</p>
        <h2>Command center ready.</h2>
        <p>Account, market context, risk and journal surfaces will appear here as the deterministic core comes online.</p>
      </section>
      <section className="default-account-card">
        <div><p className="eyebrow">COMMAND ACCOUNT</p><h2>Default trading account</h2><p>Primary account for scans, context, and execution commands. Other enabled accounts remain available for command fan-out.</p></div>
        <div className="dashboard-account-actions"><label><span className="sr-only">Default trading account</span><select value={defaultAccountId ?? ''} onChange={(event) => void selectDefaultAccount(Number(event.target.value))} disabled={!accounts.length}><option value="" disabled>Select account</option>{accounts.map((account) => <option value={account.id} key={account.id}>{account.displayName} / {account.login}</option>)}</select></label><button type="button" className="model-training-button" onClick={() => { setShowTrainingModal(true); setTrainingResult(null); void trainModel(); }} disabled={!defaultAccountId || training}><BrainCircuit size={16} aria-hidden="true" />Train model</button><button type="button" className="model-validation-button" onClick={() => void validateModel()} disabled={!modelStatus?.trained || validating}>{validating ? 'Validating...' : 'Validate model'}</button></div>
        {defaultAccountError && <p className="execution-error" role="alert">{defaultAccountError}</p>}
        {modelStatus?.trained && <p className="model-training-result" aria-live="polite">Model trained {formatTrainingDate(modelStatus.trainedAt)}{modelStatus.candleCount ? ` / ${modelStatus.candleCount} candles` : ''}</p>}
        {validationResult && !validationResult.reason && <p className="model-validation-result" aria-live="polite">Validation: {Math.round((validationResult.accuracy ?? 0) * 100)}% accuracy / {Math.round((validationResult.winRate ?? 0) * 100)}% win rate / {validationResult.validationSamples ?? 0} unseen samples</p>}
        {validationResult?.reason && <p className="model-training-result model-training-failed" role="alert">{validationResult.reason}</p>}
        {trainingResult && !showTrainingModal && <p className="model-training-result model-training-failed" aria-live="polite">{trainingResult}</p>}
      </section>
      <section className="mt5-health-card" aria-live="polite">
        <div className="mt5-health-heading"><div><p className="eyebrow">BROKER RUNTIME / MT5</p><h2>Terminal health</h2></div><span className={`mt5-health-status mt5-health-${status.toLowerCase()}`}>{status}</span></div>
        <div className="mt5-health-metrics"><span><strong>{connected}</strong>/{healthAccounts.length} terminals connected</span><span><strong>{trading}</strong> accounts trade-enabled</span></div>
        {healthAccounts.length > 0 && <ul className="mt5-health-accounts">{healthAccounts.map((account) => { const state = recoveryState(account); const needsCredentials = account.handshakeStatus === 'CREDENTIALS_UNAVAILABLE'; return <li key={account.id}><div className="mt5-health-account-title"><span>{account.name}</span><b className={state.tone === 'good' ? 'health-good' : 'health-warn'}>{state.label}</b></div><small>{account.server} / {account.handshakeStatus}</small><div className="mt5-health-progress" role="progressbar" aria-label={`${account.name} connection progress`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={state.progress}><span style={{ width: `${state.progress}%` }} /></div><div className="mt5-health-account-values"><small>Balance {account.balance}</small><small>Equity {account.equity}</small></div><small>{state.detail}</small>{needsCredentials && <button type="button" className="mt5-health-credentials-button" onClick={() => { window.location.href = `/settings?accountId=${account.id}`; }}>Update credentials</button>}</li>; })}</ul>}
        {healthAccounts.length === 0 && <p className="mt5-health-empty">No trading accounts have been added.</p>}
      </section>
      <section className="market-context-card" aria-live="polite">
        <div><p className="eyebrow">DETERMINISTIC MARKET CONTEXT</p><h2>Market regime</h2></div>
        {marketContext?.status === 'HEALTHY' ? <div className="market-context-values"><strong>{marketContext.regime?.state}</strong><span>{marketContext.symbol} / {marketContext.timeframe} / {marketContext.candleCount} candles</span><span>Confidence {Math.round((marketContext.regime?.confidence ?? 0) * 100)}%</span></div> : <p className="mt5-health-empty">{marketContext?.reason ?? 'Loading market context.'}</p>}
      </section>
      {showTrainingModal && <div className="training-modal-backdrop" role="presentation"><section className="training-modal" role="dialog" aria-modal="true" aria-labelledby="training-modal-title"><div className="training-modal-header"><div><p className="eyebrow">ATHENA MODEL ENGINE</p><h2 id="training-modal-title">{modelStatus?.trained && !training ? 'Model training' : 'Model not trained'}</h2></div><button type="button" className="modal-close" aria-label="Close training dialog" onClick={() => setShowTrainingModal(false)}><X size={18} /></button></div>{training ? <><div className="training-progress-track"><span style={{ width: `${trainingJob?.progress ?? 5}%` }} /></div><strong className="training-progress-value">{trainingJob?.progress ?? 5}%</strong><p className="training-current-phase">{trainingJob?.phase?.replaceAll('_', ' ') ?? 'STARTING'}</p><p className="training-current-message">{trainingJob?.message ?? 'Preparing model training.'}</p></> : trainingResult ? <p className="training-current-message model-training-failed">{trainingResult}</p> : modelStatus?.trained ? <p className="training-current-message">Model is trained and connected to execution. Last trained {formatTrainingDate(modelStatus.trainedAt)}.</p> : <p className="training-current-message">No trained model is available. Train ATHENA before relying on model-assisted analysis.</p>}<div className="training-modal-actions">{training && <button type="button" className="model-training-button" onClick={() => setShowTrainingModal(false)}>Continue in background</button>}{!training && !modelStatus?.trained && <button type="button" className="model-training-button" onClick={() => void trainModel()} disabled={!defaultAccountId}><BrainCircuit size={16} aria-hidden="true" />Start training</button>}{!training && (modelStatus?.trained || trainingResult) && <button type="button" className="model-training-button" onClick={() => setShowTrainingModal(false)}>Close</button>}</div></section></div>}
    </main>
  );
}


