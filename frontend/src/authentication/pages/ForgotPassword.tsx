import { useState } from 'react';
import type { FormEvent } from 'react';
import { authService } from '../services/authService';

export function ForgotPassword() {
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    await authService.requestPasswordReset(String(formData.get('email') ?? ''));
    setSubmitted(true);
  }

  return (
    <section>
      <p>ATHENA / Secure access</p>
      <h1>Reset password</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Account email
          <input name="email" type="email" autoComplete="email" required />
        </label>
        <button type="submit">Send reset link</button>
      </form>
      {submitted && <p role="status">If an account exists, reset instructions will be sent.</p>}
    </section>
  );
}
