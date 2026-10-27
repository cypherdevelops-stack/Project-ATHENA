import { useState } from 'react';
import type { FormEvent } from 'react';
import { authService } from '../services/authService';

export function SignUp() {
  const [error, setError] = useState<string | null>(null);
  const [showPasswords, setShowPasswords] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);

    try {
      setError(null);
      await authService.signup(
        String(formData.get('email') ?? ''),
        String(formData.get('password') ?? ''),
        String(formData.get('passwordConfirmation') ?? ''),
      );
      window.location.assign('/dashboard');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to create the account.');
    }
  }

  return (
    <section>
      <p>ATHENA / Secure access</p>
      <h1>Create account</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Email
          <input name="email" type="email" autoComplete="email" required />
        </label>
        <label>
          Password
          <input name="password" type={showPasswords ? 'text' : 'password'} autoComplete="new-password" required />
        </label>
        <label>
          Confirm password
          <input name="passwordConfirmation" type={showPasswords ? 'text' : 'password'} autoComplete="new-password" required />
        </label>
        <button
          className="password-visibility"
          type="button"
          aria-pressed={showPasswords}
          onClick={() => setShowPasswords((visible) => !visible)}
        >
          {showPasswords ? 'Hide passwords' : 'Show passwords'}
        </button>
        {error && <p role="alert">{error}</p>}
        <button type="submit">Create account</button>
      </form>
      <p>Already have an account? <a href="/login">Sign in</a></p>
    </section>
  );
}
