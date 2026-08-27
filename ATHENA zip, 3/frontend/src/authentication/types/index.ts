export type AuthUser = {
  id: string;
  email: string;
  displayName?: string;
};

export type AuthSession = {
  user: AuthUser | null;
  accessToken?: string;
  expiresAt?: string;
};

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';
