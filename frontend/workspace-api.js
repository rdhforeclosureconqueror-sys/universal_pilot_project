(() => {
  const AUTH_TOKEN_KEY = "auth_token";

  function getAuthToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY) || "";
  }

  function tokenExists() {
    return Boolean(getAuthToken());
  }

  function isAuthFailure(response, payload) {
    const detail = String(payload?.detail || "").toLowerCase();
    return response.status === 401 || response.status === 403 || detail.includes("invalid token");
  }

  async function apiFetch(url, options = {}) {
    const token = getAuthToken();
    const headers = new Headers(options.headers || {});
    const hasAuthHeader = Boolean(token);
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    if (options.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    console.info("[workspace auth] token exists:", Boolean(token));
    console.info("[workspace auth] request sent with auth header:", hasAuthHeader ? "yes" : "no");

    return fetch(url, { ...options, headers });
  }

  window.WorkspaceApi = {
    apiFetch,
    tokenExists,
    isAuthFailure,
  };
})();
