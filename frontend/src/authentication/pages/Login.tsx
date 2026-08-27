import { useState } from 'react';
import type { FormEvent } from 'react';
import { authService } from '../services/authService';

export function Login() {
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);

    try {
      setError(null);
      await authService.login(
        String(formData.get('email') ?? ''),
        String(formData.get('password') ?? ''),
      );
      window.location.assign('/dashboard');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to sign in.');
    }
  }

  return (
    <section>
      <p>ATHENA / Secure access</p>
      <h1>Sign in</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Email
          <input name="email" type="email" autoComplete="email" required />
        </label>
        <label>
          Password
          <input name="password" type="password" autoComplete="current-password" required />
        </label>
        {error && <p role="alert">{error}</p>}
        <button type="submit">Sign in</button>
      </form>
      <a href="/forgot-password">Forgot password?</a>
      <p>New to ATHENA? <a href="/sign-up">Create an account</a></p>
    </section>
  );
}
