import { useState, useEffect, useRef, type ClipboardEvent, type KeyboardEvent } from 'react';
import { authService } from '../services/authService';

export function VerifyEmail() {
  const [email, setEmail] = useState(() => new URLSearchParams(window.location.search).get('email') ?? '');
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const inputsRef = useRef<Array<HTMLInputElement | null>>([]);
  const [values, setValues] = useState(['', '', '', '']);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const nextEmail = params.get('email');
    if (nextEmail) setEmail(nextEmail);
    setTimeout(() => inputsRef.current[0]?.focus(), 100);
  }, []);

  useEffect(() => {
    const code = values.join('');
    if (code.length === 4) {
      void verify(code);
    }
  }, [values]);

  async function verify(code: string) {
    setError(null);
    try {
      await authService.verifyEmail(email, code);
      window.location.assign('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed.');
    }
  }

  function onChangeChar(index: number, value: string) {
    if (!/^[0-9]?$/.test(value)) return;
    const next = [...values];
    next[index] = value;
    setValues(next);
    if (value && index < 3) {
      inputsRef.current[index + 1]?.focus();
    }
  }

  function onKeyDown(index: number, event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Backspace' && !values[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  }

  async function resend() {
    setError(null);
    try {
      await authService.sendVerificationCode(email);
      setSent(true);
      setValues(['', '', '', '']);
      setTimeout(() => inputsRef.current[0]?.focus(), 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to send verification code.');
    }
  }

  function handlePaste(event: ClipboardEvent<HTMLInputElement>) {
    const text = event.clipboardData.getData('text').trim().slice(0, 4);
    if (/^[0-9]{4}$/.test(text)) {
      setValues(text.split(''));
    }
  }

  return (
    <section className="auth-card">
      <div className="auth-card-brand"><img className="auth-brand-logo" src="/Logo_no_background.png" alt="Project ATHENA" /></div>
      <div className="auth-card-heading"><div><p className="auth-eyebrow">EMAIL VERIFICATION</p><h1>Verify your email</h1></div></div>
      <p className="auth-card-description">Enter the 4-digit code sent to <strong>{email}</strong>.</p>
      <div className="verification-inputs" onPaste={handlePaste}>
        {values.map((value, index) => (
          <input
            key={index}
            ref={(element) => {
              inputsRef.current[index] = element;
            }}
            className="verification-box"
            inputMode="numeric"
            pattern="[0-9]"
            maxLength={1}
            value={value}
            onChange={(event) => onChangeChar(index, event.target.value.slice(-1))}
            onKeyDown={(event) => onKeyDown(index, event)}
            aria-label={`Digit ${index + 1}`}
          />
        ))}
      </div>

      {error && <p className="auth-error" role="alert">{error}</p>}
      {sent && <p className="auth-success">A fresh code was sent to your email.</p>}

      <p className="auth-footer">Didn't receive the code? <button type="button" onClick={() => void resend()} className="link-like">Resend</button></p>
    </section>
  );
}

export default VerifyEmail;
