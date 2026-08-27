import { useEffect, useState } from 'react';
import { authService, type JournalSession } from '../authentication/services/authService';

export function Journal() {
  const [activeTab, setActiveTab] = useState('Market Journal');
  const [sessions, setSessions] = useState<JournalSession[]>([]);

  useEffect(() => {
    authService.getJournalSessions().then(({ sessions: journalSessions }) => setSessions(journalSessions)).catch(() => setSessions([]));
  }, []);
  const allEvents = sessions.flatMap((session) => session.events.map((event) => ({ ...event, session })));

  return (
    <main className="dashboard-shell operational-page">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">GOVERNANCE PLANE / LIVING RECORD</p>
          <h1>Journal</h1>
        </div>
        <span className="status-badge">PERSISTENT</span>
      </header>
      <section className="journal-table-widget">
        <div className="journal-panel journal-table-panel">
          <nav className="journal-tabs" aria-label="Journal views">{['Market Journal', 'Trade Journal', 'Decision Audit', 'Research / AMEF'].map((tab) => <button type="button" className={activeTab === tab ? 'journal-tab-active' : ''} onClick={() => setActiveTab(tab)} key={tab}>{tab}</button>)}</nav>
          {activeTab === 'Market Journal' && <table className="journal-table"><thead><tr><th>Date + time</th><th>Market session</th><th>Instrument scanned</th><th>Regime</th><th>State</th><th>Events</th></tr></thead><tbody>{sessions.map((session) => <tr key={session.id}><td>{new Date(session.startedAt).toLocaleString()}</td><td>{session.marketSession}</td><td>{session.canonicalAsset}</td><td>{session.regime}</td><td>{session.status}</td><td>{session.events.length}</td></tr>)}</tbody></table>}
          {activeTab === 'Trade Journal' && <table className="journal-table"><thead><tr><th>Timestamp</th><th>Asset</th><th>Event</th><th>Record</th><th>Outcome</th></tr></thead><tbody>{allEvents.filter(({ eventType }) => eventType === 'TRADE' || eventType === 'OUTCOME').map(({ id, createdAt, eventType, body, session }) => <tr key={`${session.id}-${id}`}><td>{new Date(createdAt).toLocaleString()}</td><td>{session.canonicalAsset}</td><td>{eventType}</td><td>{body}</td><td>PENDING</td></tr>)}</tbody></table>}
          {activeTab === 'Decision Audit' && <table className="journal-table"><thead><tr><th>Timestamp</th><th>Session</th><th>Type</th><th>Decision record</th><th>State</th></tr></thead><tbody>{allEvents.filter(({ eventType }) => eventType === 'DECISION' || eventType === 'RISK' || eventType === 'BLOCKED').map(({ id, createdAt, eventType, body, session }) => <tr key={`${session.id}-${id}`}><td>{new Date(createdAt).toLocaleString()}</td><td>{session.title}</td><td>{eventType}</td><td>{body}</td><td>{session.status}</td></tr>)}</tbody></table>}
          {activeTab === 'Research / AMEF' && <table className="journal-table"><thead><tr><th>Episode</th><th>Asset</th><th>Authority</th><th>Evidence</th><th>Status</th></tr></thead><tbody /></table>}
          {((activeTab === 'Market Journal' && !sessions.length) || (activeTab === 'Trade Journal' && !allEvents.some(({ eventType }) => eventType === 'TRADE' || eventType === 'OUTCOME')) || (activeTab === 'Decision Audit' && !allEvents.some(({ eventType }) => eventType === 'DECISION' || eventType === 'RISK' || eventType === 'BLOCKED')) || activeTab === 'Research / AMEF') && <p className="journal-table-empty">No records in this view yet.</p>}
        </div>
      </section>
    </main>
  );
}
