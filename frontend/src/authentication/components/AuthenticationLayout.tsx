import type { ReactNode } from 'react';

type AuthenticationLayoutProps = {
  children: ReactNode;
};

export function AuthenticationLayout({ children }: AuthenticationLayoutProps) {
  return (
    <main aria-label="ATHENA authentication" className="authentication-layout">
      {children}
    </main>
  );
}
