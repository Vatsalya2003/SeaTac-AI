import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Eye, EyeOff, Loader2, Plane } from 'lucide-react';

interface LoginPageProps {
  /** Checks the demo account (in App.tsx). Returns true when the login worked. */
  onLogin: (username: string, password: string) => boolean;
  /** light/dark switch, shown in the top-right corner */
  themeToggle?: ReactNode;
}

interface LoginErrors {
  username?: string;
  password?: string;
  form?: string;
}

export function LoginPage({ onLogin, themeToggle }: LoginPageProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [signingIn, setSigningIn] = useState(false);
  const [errors, setErrors] = useState<LoginErrors>({});
  const usernameRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    usernameRef.current?.focus();
    return () => window.clearTimeout(timer.current);
  }, []);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (signingIn) return;
    const missing: LoginErrors = {};
    if (!username.trim()) missing.username = 'Enter your username.';
    if (!password) missing.password = 'Enter your password.';
    setErrors(missing);
    if (missing.username) return usernameRef.current?.focus();
    if (missing.password) return passwordRef.current?.focus();

    setSigningIn(true);
    // short pause so the loading state is visible; the check itself is instant (demo login, no server)
    timer.current = window.setTimeout(() => {
      if (!onLogin(username, password)) {
        setSigningIn(false);
        setErrors({ form: 'That username and password don’t match an account. Check them and try again.' });
        window.setTimeout(() => passwordRef.current?.select(), 0);  // after the field is enabled again
      }
    }, 350);
  };

  return (
    <main className="sea-login">
      {themeToggle && <div className="sea-login-theme">{themeToggle}</div>}
      <div className="sea-login-card">
        <div className="sea-login-brand">
          <span className="sea-logo" aria-hidden="true"><Plane /></span>
          <h1>SeaTac AI</h1>
          <p>Answers about SeaTac airfield operations, from the Port’s data.</p>
        </div>

        <form className="sea-login-form" onSubmit={handleSubmit} noValidate>
          {errors.form && (
            <div className="sea-form-alert" role="alert">{errors.form}</div>
          )}

          <div className="sea-field">
            <label htmlFor="username" className="sea-label">Username</label>
            <input
              ref={usernameRef}
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              className="sea-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              aria-invalid={errors.username ? true : undefined}
              aria-describedby={errors.username ? 'username-error' : undefined}
              disabled={signingIn}
            />
            {errors.username && <span id="username-error" className="sea-field-error">{errors.username}</span>}
          </div>

          <div className="sea-field">
            <label htmlFor="password" className="sea-label">Password</label>
            <div className="sea-password">
              <input
                ref={passwordRef}
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                className="sea-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-invalid={errors.password ? true : undefined}
                aria-describedby={errors.password ? 'password-error' : undefined}
                disabled={signingIn}
              />
              <button
                type="button"
                className="sea-icon-btn sea-password-toggle"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                aria-pressed={showPassword}
                aria-controls="password"
              >
                {showPassword ? <EyeOff /> : <Eye />}
              </button>
            </div>
            {errors.password && <span id="password-error" className="sea-field-error">{errors.password}</span>}
          </div>

          <button type="submit" className="sea-btn sea-btn-primary sea-btn-block" disabled={signingIn}>
            {signingIn ? <><Loader2 className="sea-spin" aria-hidden="true" /> Signing in…</> : 'Sign in'}
          </button>
        </form>
      </div>

      <footer className="sea-login-footer">Port of Seattle × Northeastern Experience Expo</footer>
    </main>
  );
}
