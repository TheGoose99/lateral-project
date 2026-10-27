import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../AuthContext";

export function LoginPage() {
  const { login, register, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const from =
    (location.state as { from?: string } | null)?.from ??
    (user?.role === "staff" || user?.role === "admin" ? "/staff" : "/");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const signedIn =
        authMode === "register"
          ? await register(fullName, email, password)
          : await login(email, password);
      const destination =
        signedIn.role === "staff" || signedIn.role === "admin" ? "/staff" : from;
      navigate(destination, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="content-section auth-page">
      <p className="eyebrow">ACCOUNT</p>
      <h2>{authMode === "login" ? "Welcome back" : "Create your account"}</h2>
      <div className="auth-tabs">
        <button
          type="button"
          className={authMode === "login" ? "active" : ""}
          onClick={() => setAuthMode("login")}
        >
          Log in
        </button>
        <button
          type="button"
          className={authMode === "register" ? "active" : ""}
          onClick={() => setAuthMode("register")}
        >
          Create account
        </button>
      </div>
      <form className="checkout-form" onSubmit={onSubmit}>
        {authMode === "register" && (
          <label>
            Full name
            <input
              required
              minLength={2}
              maxLength={150}
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
            />
          </label>
        )}
        <label>
          Email address
          <input
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            minLength={authMode === "register" ? 12 : 1}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error && (
          <p className="checkout-error" role="alert">
            {error}
          </p>
        )}
        <button className="checkout-button" type="submit" disabled={submitting}>
          {submitting ? "Please wait…" : authMode === "login" ? "Sign in" : "Create account"}
        </button>
      </form>
    </section>
  );
}
