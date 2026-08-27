import { useEffect, useState } from 'react';
import { authService } from '../services/authService';
import type { AuthSession, AuthStatus } from '../types';

export function useAuth() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');

  useEffect(() => {
    authService
      .getSession()
      .then((currentSession) => {
        setSession(currentSession);
        setStatus(currentSession.user ? 'authenticated' : 'unauthenticated');
      })
      .catch(() => {
        setSession(null);
        setStatus('unauthenticated');
      });
  }, []);

  return { session, status };
}
