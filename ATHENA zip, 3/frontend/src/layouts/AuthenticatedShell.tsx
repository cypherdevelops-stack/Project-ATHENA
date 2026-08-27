import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { BarChart3, BookOpen, ChevronLeft, ChevronRight, History, LayoutDashboard, LogOut, Network, Settings as SettingsIcon, ShieldCheck } from 'lucide-react';
import { authService } from '../authentication/services/authService';
import type { AuthUser } from '../authentication/types';
import { ConfirmModal } from '../modals/ConfirmModal';
import { getTheme, initializeTheme, type Theme } from '../theme';
import { HelpWidget } from '../help/HelpWidget';

type AuthenticatedShellProps = {
  user: AuthUser;
  children: ReactNode;
};

const navigation = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Executioner', href: '/executioner', icon: BarChart3 },
  { label: 'Orchestration', href: '/orchestration', icon: Network },
  { label: 'Backtesting', href: '/backtesting', icon: History },
  { label: 'Journal', href: '/journal', icon: BookOpen },
  { label: 'Settings', href: '/settings', icon: SettingsIcon },
];

export function AuthenticatedShell({ user, children }: AuthenticatedShellProps) {
  const currentPath = window.location.pathname;
  const [collapsed, setCollapsed] = useShellState();
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [logoutLoading, setLogoutLoading] = useState(false);
  const [, setThemeState] = useState<Theme>(() => getTheme());

  useEffect(() => {
    initializeTheme();
    const handleThemeChange = (event: Event) => setThemeState((event as CustomEvent<Theme>).detail);
    window.addEventListener('athena-theme-change', handleThemeChange);
    return () => window.removeEventListener('athena-theme-change', handleThemeChange);
  }, []);

  async function handleLogout() {
    setLogoutLoading(true);
    try {
      await authService.logout();
      window.location.assign('/');
    } finally {
      setLogoutLoading(false);
    }
  }

  return (
    <div className={`app-shell ${collapsed ? 'app-shell-collapsed' : ''}`}>
      <aside className="sidebar" aria-label="ATHENA navigation">
        <div className="sidebar-brand">
          <img className="sidebar-logo-full" src="/Logo_no_background.png" alt="ATHENA" />
          <img className="sidebar-logo-icon" src="/ATHENA_favicon.png" alt="ATHENA" />
        </div>
        <button
          type="button"
          className="sidebar-toggle"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
          title={collapsed ? 'Expand navigation' : 'Collapse navigation'}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
        <nav className="sidebar-nav">
          <p className="sidebar-label">Workspace</p>
          {navigation.map(({ label, href, icon: Icon }) => {
            const active = currentPath === href || (href === '/dashboard' && currentPath === '/');
            return (
              <a className={`sidebar-link ${active ? 'sidebar-link-active' : ''}`} href={href} key={href}>
                <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
                <span>{label}</span>
              </a>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-user">
            <ShieldCheck size={17} aria-hidden="true" />
            <span>{user.email}</span>
          </div>
          <button type="button" className="sidebar-logout" onClick={() => setShowLogoutModal(true)} title="Sign out">
            <LogOut size={17} aria-hidden="true" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>
      <div className="app-content">{children}</div>
      <HelpWidget />
      {showLogoutModal && <ConfirmModal
        title="Sign out of ATHENA?"
        message="Are you sure you want to log out of your ATHENA workspace?"
        confirmLabel="Sign out"
        busy={logoutLoading}
        onCancel={() => setShowLogoutModal(false)}
        onConfirm={() => void handleLogout()}
      />}
    </div>
  );
}

function useShellState(): [boolean, (collapsed: boolean) => void] {
  const [collapsed, setCollapsedState] = useState(() => localStorage.getItem('athena.sidebar.collapsed') === 'true');

  function setCollapsed(nextCollapsed: boolean) {
    setCollapsedState(nextCollapsed);
    localStorage.setItem('athena.sidebar.collapsed', String(nextCollapsed));
  }

  return [collapsed, setCollapsed];
}
