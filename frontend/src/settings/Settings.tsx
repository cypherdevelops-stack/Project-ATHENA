import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { authService, type AccountDiscovery, type AccountProfile } from '../authentication/services/authService';
import { ConfirmModal } from '../modals/ConfirmModal';
import { Plus, Settings2, ShieldCheck, Trash2 } from 'lucide-react';
import { getTheme, setTheme, type Theme } from '../theme';

type AccountWizardStep = 1 | 2 | 3 | 4 | 5 | 6;

type AccountDraft = {
  accountNickname: string;
  platform: string;
  login: string;
  password: string;
  server: string;
  connectionMethod: 'BROKER' | 'METAAPI';
  apiAccountId?: string;
};

export function Settings() {
  const [accounts, setAccounts] = useState<AccountProfile[]>([]);
  const [account, setAccount] = useState<AccountProfile | null>(null);
  const [activeTab, setActiveTab] = useState('Account Management');
  const [theme, setThemeValue] = useState<Theme>(() => getTheme());
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [connectionMethod, setConnectionMethod] = useState<AccountDraft['connectionMethod']>('BROKER');
  const [modalStep, setModalStep] = useState<AccountWizardStep>(1);
  const [handshakeComplete, setHandshakeComplete] = useState(false);
  const [handshakeLoading, setHandshakeLoading] = useState(false);
  const [accountDraft, setAccountDraft] = useState<AccountDraft | null>(null);
  const [discovery, setDiscovery] = useState<AccountDiscovery | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingAccount, setEditingAccount] = useState<AccountProfile | null>(null);
  const [pendingDelete, setPendingDelete] = useState<AccountProfile | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);
  const [updatingAccountId, setUpdatingAccountId] = useState<number | null>(null);

  useEffect(() => {
    authService.getAccounts()
      .then(({ accounts: availableAccounts }) => {
        setAccounts(availableAccounts);
        setAccount(availableAccounts[0] ?? null);
        const accountId = Number(new URLSearchParams(window.location.search).get('accountId'));
        const requestedAccount = availableAccounts.find((item) => item.id === accountId);
        if (requestedAccount) setEditingAccount(requestedAccount);
      })
      .catch(() => setError('Account settings are unavailable.'));
  }, []);

  async function toggleAccountTrading(targetAccount: AccountProfile) {
    setUpdatingAccountId(targetAccount.id);
    try {
      const updated = await authService.updateAccount({ accountId: targetAccount.id, enabled: !targetAccount.enabled });
      setAccounts((current) => current.map((item) => item.id === updated.id ? updated : item));
      setAccount((current) => current?.id === updated.id ? updated : current);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to update account settings.');
    } finally {
      setUpdatingAccountId(null);
    }
  }

  function changeTheme(nextTheme: Theme) {
    setThemeValue(nextTheme);
    setTheme(nextTheme);
  }

  function handleAccountToggle(event: React.MouseEvent<HTMLButtonElement>, availableAccount: AccountProfile) {
    event.stopPropagation();
    void toggleAccountTrading(availableAccount);
  }

  function handleAccountCardKeyDown(event: React.KeyboardEvent<HTMLElement>, availableAccount: AccountProfile) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      setAccount(availableAccount);
    }
  }

  async function saveAccountConfig(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingAccount) return;
    const data = new FormData(event.currentTarget);
    const password = String(data.get('password') ?? '');
    setConfigSaving(true);
    try {
      const updates: Record<string, unknown> & { accountId: number } = {
        accountId: editingAccount.id,
        display_name: String(data.get('displayName') ?? ''),
        account_type: String(data.get('accountType') ?? 'DEMO'),
        risk_per_trade: String(data.get('riskPerTrade') ?? '0.25'),
        max_daily_drawdown: String(data.get('maxDailyDrawdown') ?? '3'),
        athena_safety_drawdown: String(data.get('athenaSafetyDrawdown') ?? '3'),
        max_overall_drawdown: String(data.get('maxOverallDrawdown') ?? '10'),
        max_concurrent_positions: Number(data.get('maxConcurrentPositions') ?? 1),
        allowed_instruments: String(data.get('allowedInstruments') ?? '')
          .split(',').map((instrument) => instrument.trim()).filter(Boolean),
        terminal_path: String(data.get('terminalPath') ?? '').trim(),
        enabled: data.get('enabled') === 'on',
      };
      if (password) updates.password = password;
      const updated = await authService.updateAccount(updates);
      setAccounts((current) => current.map((item) => item.id === updated.id ? updated : item));
      setAccount((current) => current?.id === updated.id ? updated : current);
      setEditingAccount(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to save account settings.');
    } finally {
      setConfigSaving(false);
    }
  }

  async function deleteAccount() {
    if (!pendingDelete) return;
    const accountToDelete = pendingDelete;
    setDeleteLoading(true);
    try {
      await authService.deleteAccount(accountToDelete.id);
      const remaining = accounts.filter((item) => item.id !== accountToDelete.id);
      setAccounts(remaining);
      setAccount((current) => current?.id === accountToDelete.id ? (remaining[0] ?? null) : current);
      if (editingAccount?.id === accountToDelete.id) setEditingAccount(null);
      setPendingDelete(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to delete account.');
    } finally {
      setDeleteLoading(false);
    }
  }

  function closeAccountModal() {
    setShowCreateForm(false);
    setConnectionMethod('BROKER');
    setModalStep(1);
    setHandshakeComplete(false);
    setHandshakeLoading(false);
    setAccountDraft(null);
    setDiscovery(null);
    setError(null);
  }

  function handleConnect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const server = String(data.get('server') ?? '').toLowerCase();
    const connectionMethod = String(data.get('connectionMethod') ?? 'BROKER') as AccountDraft['connectionMethod'];

    const draft = {
      accountNickname: String(data.get('accountNickname') ?? ''),
      platform: String(data.get('platform') ?? 'MT5'),
      login: connectionMethod === 'METAAPI' ? String(data.get('apiAccountId') ?? '') : String(data.get('login') ?? ''),
      password: String(data.get(connectionMethod === 'METAAPI' ? 'apiToken' : 'password') ?? ''),
      server: String(data.get('server') ?? ''),
      connectionMethod,
      ...(connectionMethod === 'METAAPI' ? { apiAccountId: String(data.get('apiAccountId') ?? '') } : {}),
    };
    setAccountDraft(draft);

    if (connectionMethod === 'METAAPI') {
      setModalStep(2);
      setHandshakeLoading(true);
      setError(null);
      authService.discoverAccount(draft)
        .then((response) => {
          setDiscovery(response.discovery);
          setAccountDraft((current) => current ? {
            ...current,
            platform: response.discovery.platform,
            login: response.discovery.login,
            server: response.discovery.server,
          } : current);
        })
        .catch((requestError) => setError(requestError instanceof Error ? requestError.message : 'Unable to discover account.'))
        .finally(() => setHandshakeLoading(false));
      return;
    }

    if (server.includes('demo')) {
      setModalStep(2);
      setHandshakeLoading(true);
      authService.discoverAccount(draft)
        .then((response) => setDiscovery(response.discovery))
        .catch((requestError) => setError(requestError instanceof Error ? requestError.message : 'Unable to discover account.'))
        .finally(() => setHandshakeLoading(false));
      return;
    }

    if (server.includes('ive')) {
      setError('Live accounts are not yet supported.');
      return;
    }

    setError('Enter a server containing "demo" or "ive" to continue.');
  }

  function advanceWizard(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (modalStep === 2 && !handshakeComplete && discovery) {
      setHandshakeComplete(true);
      return;
    }
    if (modalStep < 6) setModalStep((current) => (current + 1) as AccountWizardStep);
  }

  async function activateAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accountDraft) return;
    try {
      const created = await authService.createAccount({
        ...accountDraft,
        canonicalAsset: discovery?.canonicalAsset ?? '',
        brokerSymbol: discovery?.brokerSymbol ?? '',
        marketDiscovery: discovery?.marketDiscovery,
        allowedInstruments: discovery?.canonicalAsset ? [discovery.canonicalAsset] : [],
      });
      setAccounts((current) => [...current, created]);
      setAccount(created);
      closeAccountModal();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to activate account.');
    }
  }

  return (
    <main className="dashboard-shell">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">PROJECT ATHENA / CONTROL PLANE</p>
          <h1>Settings</h1>
        </div>
        <span className="status-badge">POLICY CONTROL</span>
      </header>
      <nav className="settings-tabs" aria-label="Settings sections">
        {['Account Management', 'Strategies', 'Instruments', 'Sessions', 'Security', 'System Settings'].map((tab) => (
          <button type="button" className={activeTab === tab ? 'settings-tab-active' : ''} onClick={() => setActiveTab(tab)} key={tab}>
            {tab}
          </button>
        ))}
      </nav>
      {activeTab === 'Account Management' ? <>
      <section className="account-management">
        <div className="account-section-heading">
          <div>
            <p className="eyebrow">AVAILABLE ACCOUNTS</p>
            <h2>Trading accounts</h2>
          </div>
          <button type="button" className="add-account-button" onClick={() => setShowCreateForm(true)} title="Add trading account">
            <Plus size={20} aria-hidden="true" />
            <span>Add account</span>
          </button>
        </div>
          {accounts.length ? <div className="account-cards">
          {accounts.map((availableAccount) => (
            <article className={`account-card ${account?.id === availableAccount.id ? 'account-card-active' : ''}`} onClick={() => setAccount(availableAccount)} onKeyDown={(event) => handleAccountCardKeyDown(event, availableAccount)} tabIndex={0} key={availableAccount.id}>
              <span className="account-card-icon"><ShieldCheck size={20} aria-hidden="true" /></span>
              <strong>{availableAccount.displayName}</strong>
              <span>{availableAccount.platform} / Login {availableAccount.login}{availableAccount.connectionMethod === 'METAAPI' ? ' / MetaAPI' : ''}</span>
              <small>{availableAccount.server}</small>
              <div className="account-card-actions">
                <button type="button" className={`account-trade-toggle ${availableAccount.enabled ? 'account-trade-toggle-on' : ''}`} onClick={(event) => handleAccountToggle(event, availableAccount)} disabled={updatingAccountId === availableAccount.id} aria-pressed={availableAccount.enabled} title={`${availableAccount.enabled ? 'Disable' : 'Enable'} trading for ${availableAccount.displayName}`}>
                  {availableAccount.enabled ? 'ON' : 'OFF'}
                </button>
                <button type="button" className="account-action-button" onClick={(event) => { event.stopPropagation(); setEditingAccount(availableAccount); }} title={`Configure ${availableAccount.displayName}`} aria-label={`Configure ${availableAccount.displayName}`}><Settings2 size={16} aria-hidden="true" /></button>
                <button type="button" className="account-action-button account-delete-button" onClick={(event) => { event.stopPropagation(); setPendingDelete(availableAccount); }} title={`Delete ${availableAccount.displayName}`} aria-label={`Delete ${availableAccount.displayName}`}><Trash2 size={16} aria-hidden="true" /></button>
              </div>
            </article>
          ))}
        </div> : <div className="accounts-empty">
          <span className="empty-plus" aria-hidden="true"><Plus size={32} /></span>
          <h2>No trading accounts yet</h2>
          <p>Add an account to configure broker access and risk policy.</p>
          <button type="button" className="add-account-button" onClick={() => setShowCreateForm(true)}><Plus size={20} aria-hidden="true" /> Add trading account</button>
        </div>}
        {showCreateForm && <div className="account-modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setShowCreateForm(false)}>
          <form className="account-modal" onSubmit={modalStep === 1 ? handleConnect : modalStep === 6 ? activateAccount : advanceWizard} role="dialog" aria-modal="true" aria-labelledby="account-modal-title">
          <div className="account-modal-header"><div><p className="eyebrow">NEW TRADING ACCOUNT / STEP {modalStep} OF 6</p><h2 id="account-modal-title">{modalStep === 1 ? 'Connect' : modalStep === 2 && !handshakeComplete ? 'Establishing handshake' : modalStep === 2 ? 'Discovered' : modalStep === 3 ? 'Account Policy' : modalStep === 4 ? 'Risk & Restrictions' : modalStep === 5 ? 'Trading Scope' : 'Review'}</h2></div><button type="button" className="modal-close" onClick={closeAccountModal} aria-label="Close">×</button></div>
          {modalStep === 1 && <>
            <p className="wizard-lead">Let's connect your trading account.</p>
            <label>Account nickname<input name="accountNickname" required placeholder="Primary gold account" /></label>
            <label>Connection method<select name="connectionMethod" value={connectionMethod} onChange={(event) => setConnectionMethod(event.target.value as AccountDraft['connectionMethod'])}><option value="BROKER">Broker login</option><option value="METAAPI">MetaAPI</option></select></label>
            {connectionMethod === 'BROKER' && <label>Platform<select name="platform" defaultValue="MT5"><option value="MT4">MT4</option><option value="MT5">MT5</option><option value="CTRADER">cTrader</option><option value="TRADINGVIEW">TradingView</option></select></label>}
            {connectionMethod === 'METAAPI' ? <>
              <label>MetaAPI account ID<input name="apiAccountId" required autoComplete="off" /></label>
              <label>MetaAPI API token<input name="apiToken" type="password" required autoComplete="new-password" /></label>
              <p className="wizard-lead">MetaAPI must be deployed. ATHENA will verify balance, equity, leverage, trading permission, open positions, and available symbols before onboarding.</p>
            </> : <>
              <label>Login<input name="login" required autoComplete="username" /></label>
              <label>Password<input name="password" type="password" required autoComplete="current-password" /></label>
              <label>Server<input name="server" required placeholder="Demo server or live server" /></label>
            </>}
            {error && <p role="alert">{error}</p>}
            <div><button type="submit" className="add-account-button">Connect & Discover</button><button type="button" className="form-cancel" onClick={closeAccountModal}>Cancel</button></div>
          </>}
          {modalStep === 2 && !handshakeComplete && <div className="modal-message"><span className="handshake-pulse" aria-hidden="true" /><p>{handshakeLoading ? 'Establishing a secure handshake with the demo trading server.' : error ? 'Handshake failed. Check the connection details and try again.' : 'Handshake complete. Continue to review the discovered account.'}</p>{error && <p className="onboarding-error-detail" role="alert">{error}</p>}<button type="submit" className="add-account-button" disabled={handshakeLoading || !discovery}>{handshakeLoading ? 'Connecting...' : 'Continue'}</button></div>}
          {modalStep === 2 && handshakeComplete && discovery && <><p className="wizard-lead">ATHENA found your account.</p><div className="discovery-list"><span>Broker <b>{discovery.broker}</b></span><span>Server <b>{discovery.server}</b></span><span>Account <b>********</b></span><span>Balance <b>${Number(discovery.balance).toLocaleString()}</b></span><span>Currency <b>{discovery.currency}</b></span><span>Leverage <b>1:{discovery.leverage}</b></span><span>Account mode <b>{discovery.accountMode}</b></span><span>Platform <b>{discovery.platform}</b></span><span>Market data <b>{discovery.marketData}</b></span><span>Existing positions <b>{discovery.existingPositions}</b></span></div><div><button type="submit" className="add-account-button">Continue</button></div></>}
          {modalStep === 3 && <><p className="wizard-lead">How should ATHENA manage this account?</p><label>Account purpose<select defaultValue="PERSONAL"><option>Personal</option><option>Funded</option><option>Evaluation</option></select></label><label>Risk mode<select defaultValue="CONSERVATIVE"><option>Conservative</option><option>Balanced</option><option>Custom</option></select></label><label>Execution authority<select defaultValue="SEMI_AUTONOMOUS"><option value="MANUAL">Manual</option><option value="SEMI_AUTONOMOUS">Semi-Autonomous</option><option value="AUTONOMOUS">Autonomous</option></select></label><div><button type="submit" className="add-account-button">Continue</button></div></>}
          {modalStep === 4 && <><p className="wizard-lead">Set the account safety boundaries.</p><div className="wizard-fields"><label>Daily loss limit<input type="number" defaultValue="3" min="0" step="0.1" /></label><label>Overall loss limit<input type="number" defaultValue="10" min="0" step="0.1" /></label><label>Risk/trade<input type="number" defaultValue="0.25" min="0" step="0.05" /></label><label>Maximum exposure<input type="number" defaultValue="1" min="0" /></label><label>Maximum positions<input type="number" defaultValue="1" min="1" /></label><label>News restrictions<select defaultValue="HIGH_IMPACT"><option>High impact only</option><option>All scheduled news</option><option>None</option></select></label><label>Weekend policy<select defaultValue="CLOSE"><option>Close before weekend</option><option>Hold positions</option></select></label></div><div><button type="submit" className="add-account-button">Continue</button></div></>}
          {modalStep === 5 && <><p className="wizard-lead">Choose the trading scope.</p><label>Assets<input defaultValue="XAUUSD" /></label><label>Strategies<select defaultValue="SCALPING_DAY"><option>Scalping + Day Trading</option><option>Scalping only</option><option>Day Trading only</option></select></label><label>Sessions<select defaultValue="LONDON_NEW_YORK"><option>London + New York</option><option>All sessions</option><option>Custom</option></select></label><label>Correlation<select defaultValue="ENABLED"><option>Enabled</option><option>Disabled</option></select></label><label>Execution preferences<select defaultValue="COST_AWARE"><option>Cost aware</option><option>Standard</option></select></label><div><button type="submit" className="add-account-button">Continue</button></div></>}
          {modalStep === 6 && <><p className="wizard-lead">ACCOUNT READY</p><div className="review-list"><span>Connection <b>✓</b></span><span>Broker constraints <b>✓</b></span><span>Risk policy <b>✓</b></span><span>Trading permissions <b>✓</b></span><span>Safety gates <b>✓</b></span></div><label>ATHENA Authority<select defaultValue="SEMI_AUTONOMOUS"><option>Semi-Autonomous</option><option>Manual</option><option>Autonomous</option></select></label><div><button type="submit" className="add-account-button">Activate Account</button></div></>}
          </form>
        </div>}
        {editingAccount && <div className="account-modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setEditingAccount(null)}>
          <form className="account-modal" onSubmit={saveAccountConfig} role="dialog" aria-modal="true" aria-labelledby="account-config-title">
            <div className="account-modal-header"><div><p className="eyebrow">ACCOUNT CONFIGURATION</p><h2 id="account-config-title">{editingAccount.displayName}</h2></div><button type="button" className="modal-close" onClick={() => setEditingAccount(null)} aria-label="Close">×</button></div>
            <label>Account name<input name="displayName" defaultValue={editingAccount.displayName} required /></label>
            <label>Account type<select name="accountType" defaultValue={editingAccount.accountType}><option value="PERSONAL">Personal</option><option value="DEMO">Demo</option><option value="FUNDED">Funded</option></select></label>
            <label>Allowed instruments<input name="allowedInstruments" defaultValue={editingAccount.allowedInstruments.join(', ')} placeholder="XAUUSD, EURUSD" /></label>
            <label>Broker password<input name="password" type="password" autoComplete="new-password" placeholder="Enter to update saved credentials" /></label>
            <label>MT5 terminal path<input name="terminalPath" defaultValue={editingAccount.terminalPath} placeholder="Optional terminal64.exe path" /></label>
            <div className="wizard-fields"><label>Risk/trade (%)<input name="riskPerTrade" type="number" defaultValue={editingAccount.riskPerTrade} min="0" step="0.05" /></label><label>Maximum positions<input name="maxConcurrentPositions" type="number" defaultValue={editingAccount.maxConcurrentPositions} min="1" /></label><label>Daily loss limit (%)<input name="maxDailyDrawdown" type="number" defaultValue={editingAccount.maxDailyDrawdown} min="0" step="0.1" /></label><label>ATHENA safety limit (%)<input name="athenaSafetyDrawdown" type="number" defaultValue={editingAccount.athenaSafetyDrawdown} min="0" step="0.1" /></label><label>Overall loss limit (%)<input name="maxOverallDrawdown" type="number" defaultValue={editingAccount.maxOverallDrawdown} min="0" step="0.1" /></label></div>
            <label className="account-enabled-toggle"><input name="enabled" type="checkbox" defaultChecked={editingAccount.enabled} /> Enable account for ATHENA</label>
            <div><button type="submit" className="add-account-button" disabled={configSaving}>{configSaving ? 'Saving...' : 'Save settings'}</button><button type="button" className="form-cancel" onClick={() => setEditingAccount(null)}>Cancel</button></div>
          </form>
        </div>}
        {pendingDelete && <ConfirmModal
          title="Delete trading account?"
          message={`You are about to permanently delete ${pendingDelete.displayName}. Its ATHENA policy settings will also be removed.`}
          confirmLabel="Delete account"
          busy={deleteLoading}
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => void deleteAccount()}
        />}
      </section>
      </> : activeTab === 'System Settings' ? <section className="system-settings-panel"><p className="eyebrow">SYSTEM SETTINGS / APPEARANCE</p><h2>Appearance</h2><p>Choose the visual theme for your ATHENA workspace.</p><div className="theme-setting"><div><strong>Workspace theme</strong><span>{theme === 'light' ? 'Light workspace' : 'Dark workspace'}</span></div><div className="theme-switcher" role="group" aria-label="Workspace theme"><button type="button" className={theme === 'light' ? 'theme-option-active' : ''} onClick={() => changeTheme('light')}>Light</button><button type="button" className={theme === 'dark' ? 'theme-option-active' : ''} onClick={() => changeTheme('dark')}>Dark</button></div></div></section> : <section className="settings-placeholder"><p className="eyebrow">SETTINGS / {activeTab.toUpperCase()}</p><h2>{activeTab} controls are next.</h2><p>This policy surface is reserved for the Phase 1 configuration rollout.</p></section>}
    </main>
  );
}
