(() => {
  const AUTH_TOKEN_KEY = "auth_token";
  const WORKSPACE_TOUR_PROMPT_KEY_PREFIX = "workspace_tour_prompted_v1_";

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

  function createWorkspaceTour({
    workspaceKey,
    title = "Workspace Tour",
    steps = [],
    onBeforeStep = async () => {},
  } = {}) {
    if (!workspaceKey || !Array.isArray(steps) || !steps.length) {
      return null;
    }

    const overlay = document.createElement("div");
    overlay.style.cssText = "position:fixed;inset:0;background:rgba(15,23,42,.56);z-index:9998;display:none;";
    const popover = document.createElement("div");
    popover.style.cssText = "position:fixed;max-width:420px;background:#fff;border-radius:12px;padding:14px;border:1px solid #d9e2ec;z-index:9999;display:none;box-shadow:0 18px 30px rgba(15,23,42,.2);";
    popover.innerHTML = `
      <h3 id="workspace-tour-title" style="margin:0 0 8px 0;"></h3>
      <p id="workspace-tour-body" style="margin:0 0 10px 0;color:#334155;"></p>
      <div style="display:flex;justify-content:space-between;gap:8px;">
        <button type="button" id="workspace-tour-prev">Back</button>
        <div style="display:flex;gap:8px;">
          <button type="button" id="workspace-tour-close">Close</button>
          <button type="button" id="workspace-tour-next">Next</button>
        </div>
      </div>
    `;
    document.body.append(overlay, popover);

    let running = false;
    let stepIndex = 0;
    let highlightedEl = null;
    const titleEl = popover.querySelector("#workspace-tour-title");
    const bodyEl = popover.querySelector("#workspace-tour-body");
    const prevBtn = popover.querySelector("#workspace-tour-prev");
    const nextBtn = popover.querySelector("#workspace-tour-next");
    const closeBtn = popover.querySelector("#workspace-tour-close");

    const clearHighlight = () => {
      if (highlightedEl) {
        highlightedEl.style.outline = "";
        highlightedEl.style.position = "";
        highlightedEl.style.zIndex = "";
      }
      highlightedEl = null;
    };

    const stop = () => {
      running = false;
      clearHighlight();
      overlay.style.display = "none";
      popover.style.display = "none";
    };

    const positionPopover = (target) => {
      const rect = target.getBoundingClientRect();
      const top = Math.min(window.innerHeight - popover.offsetHeight - 16, Math.max(16, rect.bottom + 12));
      const left = Math.min(window.innerWidth - popover.offsetWidth - 16, Math.max(16, rect.left));
      popover.style.top = `${top}px`;
      popover.style.left = `${left}px`;
    };

    const renderStep = async () => {
      const step = steps[stepIndex];
      await onBeforeStep(step);
      const target = document.querySelector(step.target);
      if (!target) {
        if (stepIndex < steps.length - 1) {
          stepIndex += 1;
          await renderStep();
        }
        return;
      }
      clearHighlight();
      highlightedEl = target;
      target.scrollIntoView({ behavior: "smooth", block: "center" });
      target.style.outline = "3px solid #1f7aec";
      target.style.position = "relative";
      target.style.zIndex = "9999";
      titleEl.textContent = `${title} (${stepIndex + 1}/${steps.length}) · ${step.title}`;
      bodyEl.textContent = step.body;
      prevBtn.disabled = stepIndex === 0;
      nextBtn.textContent = stepIndex === steps.length - 1 ? "Finish" : "Next";
      positionPopover(target);
    };

    const start = async () => {
      running = true;
      stepIndex = 0;
      overlay.style.display = "block";
      popover.style.display = "block";
      await renderStep();
    };

    prevBtn.addEventListener("click", async () => {
      if (!running || stepIndex === 0) return;
      stepIndex -= 1;
      await renderStep();
    });
    nextBtn.addEventListener("click", async () => {
      if (!running) return;
      if (stepIndex >= steps.length - 1) {
        stop();
        return;
      }
      stepIndex += 1;
      await renderStep();
    });
    closeBtn.addEventListener("click", stop);
    overlay.addEventListener("click", stop);

    const autoPromptOnce = async () => {
      const storageKey = `${WORKSPACE_TOUR_PROMPT_KEY_PREFIX}${workspaceKey}`;
      if (localStorage.getItem(storageKey) === "true") {
        return;
      }
      localStorage.setItem(storageKey, "true");
      await start();
    };

    return { start, autoPromptOnce, stop, isRunning: () => running };
  }

  window.WorkspaceApi = {
    apiFetch,
    tokenExists,
    isAuthFailure,
    createWorkspaceTour,
  };
})();
