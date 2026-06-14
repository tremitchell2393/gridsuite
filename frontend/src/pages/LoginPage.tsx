/**
 * Login / Register page.
 *
 * Single page handling both flows via a toggle — matches the
 * lightweight auth approach in app/api/v1/routes/auth.py (registration
 * creates an org + user in one step, login returns a JWT).
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import "./LoginPage.css";

export function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register({ email, password, full_name: fullName, organization_name: orgName });
      }
      navigate("/");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">GridSuite</div>
        <h1>{mode === "login" ? "Log in" : "Create your account"}</h1>

        <form onSubmit={handleSubmit}>
          {mode === "register" && (
            <>
              <label>
                Full name
                <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </label>
              <label>
                Organization name
                <input
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  required
                />
              </label>
            </>
          )}

          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </label>

          {error && <div className="login-error">{error}</div>}

          <button type="submit" disabled={submitting}>
            {submitting ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
          </button>
        </form>

        <div className="login-toggle">
          {mode === "login" ? (
            <>
              Don't have an account?{" "}
              <button type="button" onClick={() => setMode("register")}>
                Sign up
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button type="button" onClick={() => setMode("login")}>
                Log in
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
