import './App.css'
import { useAuth } from './authentication/hooks/useAuth'
import { AuthenticationLayout } from './authentication/components/AuthenticationLayout'
import { ForgotPassword } from './authentication/pages/ForgotPassword'
import { Login } from './authentication/pages/Login'
import { ResetPassword } from './authentication/pages/ResetPassword'
import { SignUp } from './authentication/pages/SignUp'
import { SplashScreen } from './authentication/pages/SplashScreen'
import { VerifyEmail } from './authentication/pages/VerifyEmail'
import { Dashboard } from './dashboard/Dashboard'
import { Backtesting } from './backtesting/Backtesting'
import { Executioner } from './executioner/Executioner'
import { Journal } from './journal/Journal'
import { AuthenticatedShell } from './layouts/AuthenticatedShell'
import OrchestratorDashboard from './orchestration/OrchestratorDashboard'
import { Settings } from './settings/Settings'

function App() {
  const path = window.location.pathname
  const { session, status } = useAuth()

  if (path === '/forgot-password') {
    return <AuthenticationLayout><ForgotPassword /></AuthenticationLayout>
  }

  if (path === '/reset-password') {
    return <AuthenticationLayout><ResetPassword /></AuthenticationLayout>
  }

  if (path === '/login') {
    return <AuthenticationLayout><Login /></AuthenticationLayout>
  }

  if (path === '/sign-up') {
    return <AuthenticationLayout><SignUp /></AuthenticationLayout>
  }

  if (path.startsWith('/verify-email')) {
    return <AuthenticationLayout><VerifyEmail /></AuthenticationLayout>
  }

  if (status === 'authenticated' && session?.user) {
    let content = <Dashboard />
    if (path === '/executioner') content = <Executioner />
    if (path === '/backtesting') content = <Backtesting />
    if (path === '/journal') content = <Journal />
    if (path === '/orchestration') content = <OrchestratorDashboard />
    if (path === '/settings') content = <Settings />
    return <AuthenticatedShell user={session.user}>{content}</AuthenticatedShell>
  }

  if (path === '/dashboard' && status !== 'loading') {
    return <AuthenticationLayout><Login /></AuthenticationLayout>
  }

  return (
    <AuthenticationLayout><SplashScreen /></AuthenticationLayout>
  )
}

export default App

