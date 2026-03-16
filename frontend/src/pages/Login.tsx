import { FormEvent, useState } from "react";

import { AUTH_TOKEN_KEY } from "../services/apiClient";

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const payload = await response.json();

      if (!response.ok || !payload?.access_token) {
        setError(payload?.detail || "Login failed.");
        return;
      }

      localStorage.setItem(AUTH_TOKEN_KEY, payload.access_token);
      window.location.hash = "#/admin-command-center";
    } catch (requestError) {
      setError("Unable to sign in. Check connectivity and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 420, margin: "4rem auto", padding: 24, border: "1px solid #d7deeb", borderRadius: 12 }}>
      <h1>Admin Sign In</h1>
      <p>Sign in to access the Admin Command Center.</p>

      <form onSubmit={handleSubmit} style={{ display: "grid", gap: 12 }}>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            style={{ width: "100%" }}
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            style={{ width: "100%" }}
          />
        </label>

        <button type="submit" disabled={loading}>
          {loading ? "Signing In..." : "Sign In"}
        </button>
      </form>

      {error ? <p style={{ color: "#c53030", marginTop: 12 }}>{error}</p> : null}
    </div>
  );
};

export default Login;
