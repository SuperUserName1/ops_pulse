import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuthStore } from "@/features/auth/model/auth-store";

type LoginFormState = {
  username: string;
  password: string;
};

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const authStatus = useAuthStore((state) => state.authStatus);
  const isBootstrapping = useAuthStore((state) => state.isBootstrapping);
  const isSubmitting = useAuthStore((state) => state.isSubmitting);
  const errorMessage = useAuthStore((state) => state.errorMessage);
  const login = useAuthStore((state) => state.login);

  const [form, setForm] = useState<LoginFormState>({
    username: "admin",
    password: "admin123",
  });

  const redirectTo = useMemo(() => {
    const from = location.state as { from?: string } | null;
    return from?.from || "/app/profile";
  }, [location.state]);

  useEffect(() => {
    if (!isBootstrapping && authStatus === "authenticated") {
      navigate(redirectTo, { replace: true });
    }
  }, [authStatus, isBootstrapping, navigate, redirectTo]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      await login(form.username, form.password);
      navigate(redirectTo, { replace: true });
    } catch {
      // Store already contains user-friendly error state.
    }
  };

  return (
    <div className="screen-shell">
      <div className="login-grid">
        <section className="hero-card" aria-label="About Ops Pulse">
          <span className="brand-kicker">Auth Demo</span>
          <h1>Ops Pulse frontend for the current FastAPI backend</h1>
          <p className="muted">
            Public login page, protected app routes, token refresh retry and role-aware profile.
          </p>
          <ul className="hero-list">
            <li>
              <strong>Backend URL:</strong> uses <code>VITE_API_BASE_URL</code> (default <code>/v1</code>)
            </li>
            <li>
              <strong>Refresh flow:</strong> automatic retry on <code>401</code> via <code>/auth/refresh</code>
            </li>
            <li>
              <strong>Roles:</strong> admin / agent / viewer
            </li>
          </ul>
        </section>

        <section className="panel" aria-label="Login form">
          <div className="panel-header">
            <h2>Sign in</h2>
            <p className="muted">Use backend test credentials from the seeded AuthService.</p>
          </div>

          <form className="form-grid" onSubmit={onSubmit}>
            <div className="field">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                autoComplete="username"
                value={form.username}
                onChange={(event) =>
                  setForm((current) => ({ ...current, username: event.target.value }))
                }
                disabled={isSubmitting}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={form.password}
                onChange={(event) =>
                  setForm((current) => ({ ...current, password: event.target.value }))
                }
                disabled={isSubmitting}
                required
              />
            </div>

            {errorMessage ? <div className="error-box">{errorMessage}</div> : null}

            <button type="submit" className="button button-primary" disabled={isSubmitting}>
              {isSubmitting ? "Signing in..." : "Login"}
            </button>
          </form>

          <div className="hint-box">
            Demo users:
            <br />
            <code>admin / admin123</code>, <code>agent / agent123</code>,{" "}
            <code>auditor / viewer123</code>
          </div>
        </section>
      </div>
    </div>
  );
}
