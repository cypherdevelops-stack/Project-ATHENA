import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Eye, EyeOff, KeyRound } from 'lucide-react';
import { authService } from '../services/authService';

export function ResetPassword() {
  const params = new URLSearchParams(window.location.search);
  const uid = params.get('uid') ?? '';
  const token = params.get('token') ?? '';
  const [status, setStatus] = useState<'checking' | 'ready' | 'success' | 'error'>(uid && token ? 'checking' : 'error');
  const [message, setMessage] = useState(uid && token ? '' : 'This password reset link is invalid or incomplete.');
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirmation, setShowPasswordConfirmation] = useState(false);

  useEffect(() => {
    if (!uid || !token) return;
    authService.verifyPasswordResetLink(uid, token)
      .then(() => setStatus('ready'))
      .catch((error: unknown) => {
        setStatus('error');
        setMessage(error instanceof Error ? error.message : 'This password reset link is invalid or expired.');
      });
  }, [uid, token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setSubmitting(true);
    setMessage('');
    try {
      await authService.completePasswordReset(
        uid,
        token,
        String(formData.get('password') ?? ''),
        String(formData.get('passwordConfirmation') ?? ''),
      );
      setStatus('success');
      setMessage('Your password has been reset. You can now sign in.');
    } catch (error) {
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Unable to reset your password.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-card">
      <div className="auth-card-brand"><img className="auth-brand-logo" src="/Logo_no_background.png" alt="Project ATHENA" /></div>
      <div className="auth-card-heading"><div><p className="auth-eyebrow">ACCOUNT RECOVERY</p><h1>Choose a new password</h1></div><KeyRound size={25} className="auth-heading-icon" aria-hidden="true" /></div>
      {status === 'checking' ? (
        <p className="auth-card-description" role="status">Verifying your reset link...</p>
      ) : status === 'error' ? (
        <>
          <p className="auth-error" role="alert">{message}</p>
          <p className="auth-footer"><a href="/forgot-password">Request a new reset link</a></p>
        </>
      ) : status === 'success' ? (
        <>
          <p className="auth-success" role="status">{message}</p>
          <p className="auth-footer"><a href="/login">Return to sign in</a></p>
        </>
      ) : (
        <>
          <p className="auth-card-description">Create a new password for your ATHENA account.</p>
          <form onSubmit={handleSubmit}>
            <label>
              Password
              <div className="auth-password-field">
                <input name="password" type={showPassword ? 'text' : 'password'} autoComplete="new-password" required />
                <button
                  type="button"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  title={showPassword ? 'Hide password' : 'Show password'}
                  aria-pressed={showPassword}
                  onClick={() => setShowPassword((value) => !value)}
                >
                  {showPassword ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
                </button>
              </div>
            </label>
            <label>
              Confirm password
              <div className="auth-password-field">
                <input name="passwordConfirmation" type={showPasswordConfirmation ? 'text' : 'password'} autoComplete="new-password" required />
                <button
                  type="button"
                  aria-label={showPasswordConfirmation ? 'Hide confirm password' : 'Show confirm password'}
                  title={showPasswordConfirmation ? 'Hide confirm password' : 'Show confirm password'}
                  aria-pressed={showPasswordConfirmation}
                  onClick={() => setShowPasswordConfirmation((value) => !value)}
                >
                  {showPasswordConfirmation ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
                </button>
              </div>
            </label>
            <button className="auth-submit" type="submit" disabled={submitting}>Reset password <span aria-hidden="true">→</span></button>
          </form>
          {message && <p className="auth-error" role="alert">{message}</p>}
          <p className="auth-footer"><a href="/login">Return to sign in</a></p>
        </>
      )}
    </section>
  );
}
