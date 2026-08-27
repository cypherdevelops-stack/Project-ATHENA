export function SplashScreen() {
  return (
    <section className="splash-screen">
      <img className="splash-mark" src="/ATHENA_favicon.png" alt="" aria-hidden="true" />
      <img className="splash-logo" src="/Logo_no_background.png" alt="Project ATHENA" />
      <p className="eyebrow">PROJECT ATHENA / v2.7</p>
      <h1>Risk-first<br />trading intelligence.</h1>
      <p className="splash-copy">A governed operating system for persistent market experience and multi-asset execution.</p>
      <div className="splash-actions">
        <a className="button button-primary" href="/login">Sign in</a>
        <a className="button button-secondary" href="/sign-up">Create account</a>
      </div>
      <p className="splash-status"><span aria-hidden="true" /> Secure access / Backend authority online</p>
    </section>
  );
}
