import { Shield } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi, setAuthToken } from "../api/client";

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await authApi.login(email, password);
      setAuthToken(res.access_token);
      window.localStorage.setItem("agentguard.workspaceId", res.workspace_id);
      window.localStorage.setItem("agentguard.userId", res.user_id);
      window.localStorage.setItem("agentguard.email", res.email);
      navigate("/overview");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <Shield size={28} fill="var(--brand-cyan)" color="var(--brand-cyan)" />
          <span className="auth-logo-name">AgentGuard</span>
        </div>
        <h1 className="auth-title">Sign in</h1>
        <p className="auth-subtitle">Monitor and control your AI agents</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-field">
            <label htmlFor="email" className="auth-label">Email</label>
            <input
              id="email"
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoFocus
            />
          </div>
          <div className="auth-field">
            <label htmlFor="password" className="auth-label">Password</label>
            <input
              id="password"
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          {error && <p className="auth-error">{error}</p>}

          <button
            type="submit"
            className="button button-primary auth-submit"
            disabled={loading}
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="auth-footer">
          Don't have an account?{" "}
          <Link to="/register" className="auth-link">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
