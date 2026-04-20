const state = {
  openApi: null,
  enums: {
    caseStatus: [],
    documentType: [],
    referralStatus: [],
  },
  consentState: new Map(),
  propertyEndpointsAvailable: false,
  caseListAvailable: false,
  mapInstance: null,
  detailMapInstance: null,
  propertyList: [],
  adminActionHistory: [],
};

const uuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const apiBaseInput = document.getElementById("api-base");
const AUTH_TOKEN_KEY = "auth_token";
const TOUR_COMPLETED_KEY = "guided_tour_completed_v1";
const TOUR_DISMISSED_KEY = "guided_tour_dismissed_v1";
const ONBOARDING_STATE_STORAGE_KEY = "onboarding_state_v1";
const ONBOARDING_SESSION_PROMPTS_KEY = "onboarding_prompt_session_seen_v1";
const ONBOARDING_SCHEMA_VERSION = 1;

// Phase A1: onboarding/adoption config contract (schema + rules only, no UI/runtime wiring yet).
const FEATURE_ADOPTION_STATES = Object.freeze({
  NOT_SEEN: "not_seen",
  SEEN: "seen",
  INTERACTED: "interacted",
  ADOPTED: "adopted",
});

const ONBOARDING_MILESTONES = Object.freeze({
  ONBOARDING_STARTED: "onboarding_started",
  ONBOARDING_COMPLETED: "onboarding_completed",
  CASES_SEEN: "cases_seen",
  FIRST_MEANINGFUL_CASE_ACTION: "first_meaningful_case_action",
  MAP_SEEN: "map_seen",
  ANALYTICS_SEEN: "analytics_seen",
  GUIDED_TOUR_REPLAYED_MANUALLY: "guided_tour_replayed_manually",
});

const ONBOARDING_DEFAULT_STATE = Object.freeze({
  version: ONBOARDING_SCHEMA_VERSION,
  milestones: {
    [ONBOARDING_MILESTONES.ONBOARDING_STARTED]: null,
    [ONBOARDING_MILESTONES.ONBOARDING_COMPLETED]: null,
    [ONBOARDING_MILESTONES.CASES_SEEN]: null,
    [ONBOARDING_MILESTONES.FIRST_MEANINGFUL_CASE_ACTION]: null,
    [ONBOARDING_MILESTONES.MAP_SEEN]: null,
    [ONBOARDING_MILESTONES.ANALYTICS_SEEN]: null,
    [ONBOARDING_MILESTONES.GUIDED_TOUR_REPLAYED_MANUALLY]: null,
  },
  features: {
    cases: FEATURE_ADOPTION_STATES.NOT_SEEN,
    map: FEATURE_ADOPTION_STATES.NOT_SEEN,
    data: FEATURE_ADOPTION_STATES.NOT_SEEN,
  },
  promptHistory: {
    byPromptId: {},
    lastPromptAt: null,
  },
  meta: {
    lastUpdatedAt: null,
    resetCount: 0,
  },
});

const ONBOARDING_SUPPRESSION_RULES = Object.freeze({
  suppressWhileGuidedTourRunning: true,
  suppressMiniTourOffersWhileGlobalTourRunning: true,
  onePromptAtATime: true,
  oncePerPromptPerSession: true,
  maxShowsPerPromptLifetime: 3,
  minSessionsBetweenSamePrompt: 2,
});

const ONBOARDING_MINI_TOUR_CONFIG = Object.freeze({
  cases: {
    id: "cases-mini-tour-v1",
    feature: "cases",
    route: "cases",
    stepIds: ["cases-workspace"],
    trigger: {
      milestoneAnyOfMissing: [
        ONBOARDING_MILESTONES.CASES_SEEN,
        ONBOARDING_MILESTONES.FIRST_MEANINGFUL_CASE_ACTION,
      ],
      featureStateAtMost: FEATURE_ADOPTION_STATES.SEEN,
    },
    replayEligible: true,
    suppression: {
      blockIfGuidedTourRunning: true,
      blockIfPromptAlreadyShownThisSession: true,
      blockIfPromptCapped: true,
    },
  },
  data: {
    id: "data-mini-tour-v1",
    feature: "data",
    route: "data",
    stepIds: ["analytics-panel"],
    trigger: {
      milestoneMissing: ONBOARDING_MILESTONES.ANALYTICS_SEEN,
      featureStateAtMost: FEATURE_ADOPTION_STATES.SEEN,
    },
    replayEligible: true,
    suppression: {
      blockIfGuidedTourRunning: true,
      blockIfPromptAlreadyShownThisSession: true,
      blockIfPromptCapped: true,
    },
  },
});

const ONBOARDING_PROMPT_RULE_MATRIX = Object.freeze([
  {
    id: "suggest-analytics-after-cases-usage",
    priority: 100,
    promptType: "feature_nudge",
    targetFeature: "data",
    eligibility: {
      minSessionCount: 3,
      requiresFeatureState: { cases: FEATURE_ADOPTION_STATES.SEEN },
      requiresMilestoneMissing: ONBOARDING_MILESTONES.ANALYTICS_SEEN,
    },
    suppressIf: {
      guidedTourRunning: true,
      promptShownThisSession: true,
      promptCappedAcrossSessions: true,
    },
  },
  {
    id: "suggest-first-case-action",
    priority: 90,
    promptType: "action_nudge",
    targetFeature: "cases",
    eligibility: {
      minSessionCount: 2,
      requiresMilestonePresent: ONBOARDING_MILESTONES.CASES_SEEN,
      requiresMilestoneMissing: ONBOARDING_MILESTONES.FIRST_MEANINGFUL_CASE_ACTION,
    },
    suppressIf: {
      guidedTourRunning: true,
      promptShownThisSession: true,
      promptCappedAcrossSessions: true,
    },
  },
  {
    id: "suggest-map-after-dashboard-only-pattern",
    priority: 80,
    promptType: "feature_nudge",
    targetFeature: "map",
    eligibility: {
      minSessionCount: 3,
      requiresRoutePattern: "dashboard_only",
      requiresMilestoneMissing: ONBOARDING_MILESTONES.MAP_SEEN,
    },
    suppressIf: {
      guidedTourRunning: true,
      promptShownThisSession: true,
      promptCappedAcrossSessions: true,
    },
  },
]);

const cloneDefaultOnboardingState = () =>
  JSON.parse(JSON.stringify(ONBOARDING_DEFAULT_STATE));

const getSessionPromptIds = () => {
  try {
    const value = JSON.parse(
      sessionStorage.getItem(ONBOARDING_SESSION_PROMPTS_KEY) || "[]",
    );
    return Array.isArray(value) ? value : [];
  } catch (error) {
    return [];
  }
};

const getOnboardingState = () => {
  try {
    const parsed = JSON.parse(localStorage.getItem(ONBOARDING_STATE_STORAGE_KEY) || "null");
    if (!parsed || typeof parsed !== "object") {
      return cloneDefaultOnboardingState();
    }
    if (parsed.version !== ONBOARDING_SCHEMA_VERSION) {
      return cloneDefaultOnboardingState();
    }
    return {
      ...cloneDefaultOnboardingState(),
      ...parsed,
      milestones: {
        ...ONBOARDING_DEFAULT_STATE.milestones,
        ...(parsed.milestones || {}),
      },
      features: {
        ...ONBOARDING_DEFAULT_STATE.features,
        ...(parsed.features || {}),
      },
      promptHistory: {
        ...ONBOARDING_DEFAULT_STATE.promptHistory,
        ...(parsed.promptHistory || {}),
      },
      meta: {
        ...ONBOARDING_DEFAULT_STATE.meta,
        ...(parsed.meta || {}),
      },
    };
  } catch (error) {
    return cloneDefaultOnboardingState();
  }
};

const setOnboardingState = (nextState) => {
  const current = getOnboardingState();
  const normalized = {
    ...current,
    ...(nextState || {}),
    version: ONBOARDING_SCHEMA_VERSION,
    meta: {
      ...current.meta,
      ...((nextState && nextState.meta) || {}),
      lastUpdatedAt: new Date().toISOString(),
    },
  };
  localStorage.setItem(ONBOARDING_STATE_STORAGE_KEY, JSON.stringify(normalized));
};

const getAuthToken = () => localStorage.getItem(AUTH_TOKEN_KEY) || "";

const clearAuthToken = () => {
  localStorage.removeItem(AUTH_TOKEN_KEY);
};


const pages = {
  login: {
    title: "Admin Sign In",
    subtitle: "Authenticate to access admin tools.",
  },
  dashboard: {
    title: "Operator Dashboard",
    subtitle: "Status-aware overview of your operations.",
  },
  cases: {
    title: "Case Management",
    subtitle: "Track lifecycle progress and compliance checkpoints.",
  },
  properties: {
    title: "Property Management",
    subtitle: "Real estate assets linked to cases.",
  },
  map: {
    title: "Property Map View",
    subtitle: "Geographic intelligence from backend property data.",
  },
  "property-detail": {
    title: "Property Detail",
    subtitle: "Linked cases, documents, and audit history.",
  },
  documents: {
    title: "Document Management",
    subtitle: "Evidence handling and validation enforcement.",
  },
  referrals: {
    title: "Referrals & Partners",
    subtitle: "Consent-gated referral workflows.",
  },
  training: {
    title: "Training & Certification",
    subtitle: "Operator onboarding and certification outcomes.",
  },
  audit: {
    title: "Audit & AI Activity Logs",
    subtitle: "Compliance transparency and AI governance.",
  },
  data: {
    title: "Data Tables",
    subtitle: "Live tables from BotOps and lead intelligence.",
  },
  "admin-command-center": {
    title: "Admin Command Center",
    subtitle: "One-click access to platform capabilities and AI automation.",
  },
};

const TOUR_STEPS = [
  {
    id: "navigation",
    target: '[data-tour="main-navigation"]',
    title: "Main Navigation",
    body: "Use this sidebar to move between your CRM workspaces, including cases, properties, maps, and compliance logs.",
    page: "dashboard",
    optional: false,
    skipIfMissing: true,
  },
  {
    id: "dashboard-overview",
    target: '[data-tour="dashboard-overview"]',
    title: "Dashboard Overview",
    body: "This dashboard gives you a quick operational snapshot so you can spot priorities before diving into case work.",
    page: "dashboard",
    optional: false,
    skipIfMissing: true,
  },
  {
    id: "cases-workspace",
    target: '[data-tour="cases-workspace"]',
    title: "Case Workspace",
    body: "Case Management is where records are filtered, reviewed, and updated as each homeowner or property moves through the lifecycle.",
    page: "cases",
    optional: false,
    skipIfMissing: true,
  },
  {
    id: "map-panel",
    target: '[data-tour="map-panel"]',
    title: "Map Panel",
    body: "The map helps you understand geographic coverage, cluster opportunities, and location-based priorities.",
    page: "map",
    optional: true,
    skipIfMissing: true,
  },
  {
    id: "analytics-panel",
    target: '[data-tour="analytics-panel"]',
    title: "Analytics Tables",
    body: "This area surfaces data tables and trend context to help guide performance and operational decisions.",
    page: "data",
    optional: true,
    skipIfMissing: true,
  },
  {
    id: "admin-command-center",
    target: '[data-tour="admin-command-center"]',
    title: "Admin Command Center",
    body: "Admin actions and automation tools are centralized here for privileged users managing system operations.",
    page: "admin-command-center",
    optional: true,
    skipIfMissing: true,
  },
  {
    id: "tour-replay",
    target: '[data-tour="tour-replay-button"]',
    title: "Replay the Tour",
    body: "You're ready to use the system. Use this button any time you want a quick refresher of the platform layout.",
    page: "dashboard",
    optional: false,
    skipIfMissing: true,
  },
];

const createGuidedTourController = ({ setPageFn, getCurrentPageFn }) => {
  const state = {
    running: false,
    steps: TOUR_STEPS,
    currentStepIndex: -1,
    completionState: "idle",
  };

  const markCompleted = () => {
    localStorage.setItem(TOUR_COMPLETED_KEY, "true");
    localStorage.removeItem(TOUR_DISMISSED_KEY);
  };

  const markDismissed = () => {
    if (localStorage.getItem(TOUR_COMPLETED_KEY) === "true") {
      return;
    }
    localStorage.setItem(TOUR_DISMISSED_KEY, "true");
  };

  const overlay = document.createElement("div");
  overlay.className = "tour-overlay hidden";
  overlay.setAttribute("aria-hidden", "true");
  document.body.appendChild(overlay);

  const popover = document.createElement("div");
  popover.className = "tour-popover hidden";
  popover.setAttribute("role", "dialog");
  popover.setAttribute("aria-modal", "true");
  popover.setAttribute("aria-live", "polite");
  popover.innerHTML = `
    <div class="tour-step-count"></div>
    <h3 class="tour-title"></h3>
    <p class="tour-body"></p>
    <div class="tour-controls">
      <button type="button" class="ghost tour-prev">Back</button>
      <button type="button" class="ghost tour-close">Skip Tour</button>
      <button type="button" class="primary tour-next">Next</button>
    </div>
  `;
  document.body.appendChild(popover);

  const stepCount = popover.querySelector(".tour-step-count");
  const title = popover.querySelector(".tour-title");
  const body = popover.querySelector(".tour-body");
  const prevButton = popover.querySelector(".tour-prev");
  const nextButton = popover.querySelector(".tour-next");
  const closeButton = popover.querySelector(".tour-close");

  let highlightedElement = null;

  const clearHighlight = () => {
    if (!highlightedElement) {
      return;
    }
    highlightedElement.classList.remove("tour-target-active");
    highlightedElement = null;
  };

  const isElementVisible = (element) => {
    if (!element) {
      return false;
    }
    const pageContainer = element.closest(".page");
    if (pageContainer && !pageContainer.classList.contains("active")) {
      return false;
    }
    const style = window.getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden") {
      return false;
    }
    return true;
  };

  const resolveTarget = (step) => {
    if (!step?.target) {
      return null;
    }
    const element = document.querySelector(step.target);
    if (!element || !isElementVisible(element)) {
      return null;
    }
    return element;
  };

  const waitForStepTarget = async (step, attempts = 12) => {
    for (let attempt = 0; attempt < attempts; attempt += 1) {
      const element = resolveTarget(step);
      if (element) {
        return element;
      }
      await new Promise((resolve) => window.setTimeout(resolve, 60));
    }
    return null;
  };

  const setRouteForStep = (step) => {
    if (!step?.page) {
      return;
    }
    const currentPage = getCurrentPageFn();
    if (currentPage === step.page) {
      return;
    }
    window.location.hash = `#/${step.page}`;
    setPageFn(step.page);
  };

  const updatePopoverForStep = (step, stepIndex) => {
    stepCount.textContent = `Step ${stepIndex + 1} of ${state.steps.length}`;
    title.textContent = step.title;
    body.textContent = step.body;
    prevButton.disabled = stepIndex <= 0;
    nextButton.textContent = stepIndex >= state.steps.length - 1 ? "Finish" : "Next";
  };

  const positionPopover = (target) => {
    if (!target) {
      return;
    }
    const popoverRect = popover.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const margin = 16;

    let left = targetRect.left + targetRect.width / 2 - popoverRect.width / 2;
    left = Math.min(
      Math.max(margin, left),
      Math.max(margin, viewportWidth - popoverRect.width - margin),
    );

    const spaceAbove = targetRect.top - margin;
    const spaceBelow = viewportHeight - targetRect.bottom - margin;
    const prefersAbove = spaceAbove >= popoverRect.height + margin || spaceAbove > spaceBelow;

    const top = prefersAbove
      ? Math.max(margin, targetRect.top - popoverRect.height - margin)
      : Math.min(
          viewportHeight - popoverRect.height - margin,
          targetRect.bottom + margin,
        );

    popover.style.top = `${top}px`;
    popover.style.left = `${left}px`;
  };

  const activateStep = async (requestedIndex) => {
    if (!state.running) {
      return;
    }
    if (requestedIndex < 0) {
      requestedIndex = 0;
    }
    if (requestedIndex >= state.steps.length) {
      state.completionState = "completed";
      stop({ markComplete: true });
      return;
    }

    const step = state.steps[requestedIndex];
    setRouteForStep(step);
    const target = await waitForStepTarget(step);

    if (!target) {
      if (step.skipIfMissing || step.optional) {
        activateStep(requestedIndex + 1);
        return;
      }
      stop({ markComplete: false });
      return;
    }

    clearHighlight();
    highlightedElement = target;
    target.classList.add("tour-target-active");
    target.scrollIntoView({ behavior: "smooth", block: "center" });

    state.currentStepIndex = requestedIndex;
    updatePopoverForStep(step, requestedIndex);
    positionPopover(target);
  };

  const start = async ({ restart = false } = {}) => {
    state.running = true;
    if (restart) {
      state.completionState = "restarted";
    } else {
      state.completionState = "in_progress";
    }
    overlay.classList.remove("hidden");
    overlay.setAttribute("aria-hidden", "false");
    popover.classList.remove("hidden");
    await activateStep(0);
  };

  const next = async () => {
    await activateStep(state.currentStepIndex + 1);
  };

  const previous = async () => {
    await activateStep(state.currentStepIndex - 1);
  };

  const stop = ({ markComplete = false } = {}) => {
    const wasRunning = state.running;
    state.running = false;
    overlay.classList.add("hidden");
    overlay.setAttribute("aria-hidden", "true");
    popover.classList.add("hidden");
    clearHighlight();
    if (markComplete) {
      state.completionState = "completed";
      markCompleted();
      return;
    }
    if (!wasRunning || state.completionState === "completed") {
      return;
    }
    state.completionState = "dismissed";
    markDismissed();
  };

  const restart = async () => {
    stop({ markComplete: false });
    await start({ restart: true });
  };

  nextButton.addEventListener("click", () => {
    next();
  });
  prevButton.addEventListener("click", () => {
    previous();
  });
  closeButton.addEventListener("click", () => {
    stop({ markComplete: false });
  });
  window.addEventListener("resize", () => {
    if (!state.running || !highlightedElement) {
      return;
    }
    positionPopover(highlightedElement);
  });
  window.addEventListener(
    "scroll",
    () => {
      if (!state.running || !highlightedElement) {
        return;
      }
      positionPopover(highlightedElement);
    },
    true,
  );

  return {
    start,
    restart,
    next,
    previous,
    stop,
    complete: () => stop({ markComplete: true }),
    resolveTarget,
    getState: () => ({ ...state }),
    canAutoStart: () => {
      const completed = localStorage.getItem(TOUR_COMPLETED_KEY) === "true";
      const dismissed = localStorage.getItem(TOUR_DISMISSED_KEY) === "true";
      return !completed && !dismissed;
    },
  };
};

const getApiBase = () => {
  const override = apiBaseInput.value.trim();
  if (override) {
    return override.endsWith("/") ? override.slice(0, -1) : override;
  }
  const configured = window.__API_BASE_URL__ || "";
  return configured.endsWith("/") ? configured.slice(0, -1) : configured;
};

const getCurrentPageFromHash = () => window.location.hash.replace("#/", "") || "dashboard";

let guidedTourController = null;
let autoTourAttempted = false;

const isNonLoginDashboardRoute = (page) =>
  Boolean(page && page !== "login" && pages[page]);

const waitForTourLaunchReadiness = async ({ page, attempts = 15 } = {}) => {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const activePage = document.querySelector(`.page.active[data-page="${page}"]`);
    if (activePage) {
      return true;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 80));
  }
  return false;
};

const maybeAutoStartGuidedTour = async () => {
  if (autoTourAttempted || !guidedTourController) {
    return;
  }

  const token = getAuthToken();
  const currentPage = getCurrentPageFromHash();
  if (!token || !isNonLoginDashboardRoute(currentPage)) {
    return;
  }

  if (!guidedTourController.canAutoStart()) {
    autoTourAttempted = true;
    return;
  }

  const isReady = await waitForTourLaunchReadiness({ page: currentPage });
  if (!isReady) {
    return;
  }

  autoTourAttempted = true;
  await guidedTourController.start();
};

const fetchOpenApi = async () => {
  const response = await fetch(`${getApiBase()}/openapi.json`);
  if (!response.ok) {
    throw new Error("Unable to load OpenAPI schema.");
  }
  return response.json();
};

const extractEnum = (schemas, enumName) => {
  if (schemas?.[enumName]?.enum) {
    return schemas[enumName].enum;
  }
  const match = Object.entries(schemas || {}).find(
    ([key, schema]) =>
      schema?.enum && key.toLowerCase().includes(enumName.toLowerCase())
  );
  return match ? match[1].enum : [];
};

const detectEndpoint = (openApi, path, method = "get") => {
  const entry = openApi?.paths?.[path];
  return Boolean(entry && entry[method]);
};

const detectPropertyEndpoints = (openApi) => {
  const paths = Object.keys(openApi?.paths || {});
  return paths.some((path) => path.includes("property"));
};

const fetchJson = async (url) => {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
};

const clearElement = (element) => {
  element.replaceChildren();
};

const createCell = (value) => {
  const cell = document.createElement("td");
  cell.textContent = value ?? "—";
  return cell;
};

const createPanel = (label, value) => {
  const panel = document.createElement("div");
  panel.className = "panel";
  const strong = document.createElement("strong");
  strong.textContent = `${label}:`;
  panel.appendChild(strong);
  panel.append(` ${value ?? "—"}`);
  return panel;
};

const chartSets = {
  dashboard: [
    { title: "Market Pulse", subtitle: "Listings, demand, and equity signals." },
    { title: "Opportunity Score", subtitle: "AI-ready scoring baseline." },
    { title: "Pipeline Trend", subtitle: "Cases moving through stages." },
  ],
  cases: [
    { title: "Case Volume", subtitle: "New cases by week." },
    { title: "Status Mix", subtitle: "Distribution across lifecycle states." },
  ],
  properties: [
    { title: "Intake Velocity", subtitle: "New properties over time." },
    { title: "Auction Calendar", subtitle: "Upcoming auction windows." },
  ],
  map: [
    { title: "Geo Coverage", subtitle: "ZIP-level distribution." },
    { title: "Hot Zones", subtitle: "Highest equity clusters." },
  ],
  "property-detail": [
    { title: "Equity Snapshot", subtitle: "Estimated equity vs balance." },
    { title: "Timeline", subtitle: "Key property milestones." },
  ],
  documents: [
    { title: "Document Status", subtitle: "Pending vs verified evidence." },
    { title: "Upload Volume", subtitle: "Evidence throughput." },
  ],
  referrals: [
    { title: "Referral Pipeline", subtitle: "Queued vs completed." },
    { title: "Partner Activity", subtitle: "Top partner outcomes." },
  ],
  training: [
    { title: "Training Progress", subtitle: "Quiz completions." },
    { title: "Certification Status", subtitle: "Active vs expired." },
  ],
  audit: [
    { title: "Audit Events", subtitle: "Recent compliance activity." },
    { title: "AI Activity", subtitle: "Model calls and overrides." },
  ],
  data: [
    { title: "BotOps Throughput", subtitle: "Commands processed." },
    { title: "Command Backlog", subtitle: "Pending automation jobs." },
  ],
  "admin-command-center": [
    { title: "Capability Coverage", subtitle: "System, lead, foreclosure, and AI actions." },
    { title: "Automation Queue", subtitle: "Recent admin-run jobs and outcomes." },
  ],
};

const devPropertyFallback = {
  id: "dev-property-101-elm",
  address: "101 Elm St",
  city: "Dallas",
  state: "TX",
  zip: "75201",
  case_status: "new",
  latitude: 32.7767,
  longitude: -96.797,
  loan_type: "Conventional",
};

const adminCapabilitySections = [
  {
    title: "System Operations",
    actions: [
      { label: "Verify System Health", endpoint: "/admin/system/verify/phase10", method: "POST", payload: {} },
      { label: "Run Policy Engine Diagnostics", endpoint: "/verify/policy-engine", method: "GET" },
      { label: "View Impact Summary", endpoint: "/impact/summary", method: "GET" },
    ],
  },
  {
    title: "Lead Intelligence",
    actions: [
      { label: "Ingest Leads", endpoint: "/leads/intelligence/ingest", method: "POST", payload: { source_name: "mufasa", source_type: "ai", leads: [{ property_address: "101 Elm St", city: "Dallas", state: "TX", foreclosure_stage: "pre_foreclosure" }] } },
      { label: "Score Leads", endpoint: "/admin/ai/mufasa/chat", method: "POST", payload: { prompt: "score leads" } },
    ],
  },
  {
    title: "Foreclosure Intelligence",
    actions: [
      { label: "Create Foreclosure Profile", endpoint: "/foreclosure/create-profile", method: "POST", payload: { property_id: "demo-property", owner_name: "Demo Owner" } },
      { label: "Analyze Property", endpoint: "/foreclosure/analyze-property", method: "POST", payload: { estimated_value: 350000, estimated_mortgage_balance: 280000, months_delinquent: 5, auction_days_out: 18 } },
    ],
  },
  {
    title: "Skiptrace",
    actions: [{ label: "Run Skiptrace Integration Check", endpoint: "/verify/skiptrace-integration", method: "GET" }],
  },
  {
    title: "Essential Worker Housing",
    actions: [
      { label: "Create Worker Profile", endpoint: "/essential-worker/profile", method: "POST", payload: { worker_id: "worker-demo", occupation: "Teacher", annual_income: 68000, city: "Dallas", state: "TX" } },
      { label: "Discover Programs", endpoint: "/essential-worker/discover-benefits", method: "POST", payload: { worker_id: "worker-demo" } },
    ],
  },
  {
    title: "Veteran Intelligence",
    actions: [{ label: "Discover Veteran Benefits", endpoint: "/admin/ai/mufasa/chat", method: "POST", payload: { prompt: "discover veteran benefits" } }],
  },
  {
    title: "Partner Routing",
    actions: [{ label: "Route Case To Partner", endpoint: "/partners/route-case", method: "POST", payload: { case_id: "00000000-0000-0000-0000-000000000000", partner_id: "partner-demo", routing_reason: "demo" } }],
  },
  {
    title: "Portfolio",
    actions: [{ label: "View Portfolio Summary", endpoint: "/portfolio/summary", method: "GET" }],
  },
  {
    title: "Training",
    actions: [{ label: "System Training Overview", endpoint: "/training/system-overview", method: "GET" }],
  },
  {
    title: "AI Command Center",
    actions: [
      { label: "Show Platform Capabilities", endpoint: "/admin/ai/mufasa/chat", method: "POST", payload: { prompt: "show platform capabilities" } },
      { label: "Run Investor Demo", endpoint: "/admin/ai/mufasa/chat", method: "POST", payload: { prompt: "run investor demo", investor_mode: true } },
    ],
  },
];

const renderAdminResponseConsole = () => {
  const output = document.getElementById("admin-response-output");
  if (!output) {
    return;
  }
  if (!state.adminActionHistory.length) {
    output.textContent = "Run an admin action to view API responses in the console.";
    return;
  }
  output.textContent = JSON.stringify(state.adminActionHistory, null, 2);
};

const executeAdminAction = async (action) => {
  const headers = { "Content-Type": "application/json" };
  const token = getAuthToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${getApiBase()}${action.endpoint}`, {
    method: action.method,
    headers,
    body: action.method === "POST" ? JSON.stringify(action.payload || {}) : undefined,
  });

  let payload;
  try {
    payload = await response.json();
  } catch (error) {
    payload = await response.text();
  }

  const entry = {
    timestamp: new Date().toISOString(),
    action: action.label,
    endpoint: action.endpoint,
    method: action.method,
    ok: response.ok,
    status: response.status,
    payload,
  };

  state.adminActionHistory = [entry, ...state.adminActionHistory].slice(0, 50);
  renderAdminResponseConsole();

  if (response.status === 401) {
    clearAuthToken();
    window.location.hash = "#/login";
  }
};

const renderAdminCommandCenter = () => {
  const container = document.getElementById("admin-capability-panels");
  if (!container) {
    return;
  }
  clearElement(container);

  adminCapabilitySections.forEach((section) => {
    const card = document.createElement("article");
    card.className = "card";

    const title = document.createElement("h3");
    title.textContent = section.title;

    const actionsContainer = document.createElement("div");
    actionsContainer.className = "admin-capability-actions";

    section.actions.forEach((action) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "ghost admin-action-button";
      button.textContent = action.label;
      button.addEventListener("click", async () => {
        button.disabled = true;
        try {
          await executeAdminAction(action);
        } catch (error) {
          state.adminActionHistory = [
            {
              timestamp: new Date().toISOString(),
              action: action.label,
              endpoint: action.endpoint,
              method: action.method,
              ok: false,
              status: "network_error",
              payload: String(error),
            },
            ...state.adminActionHistory,
          ].slice(0, 50);
          renderAdminResponseConsole();
        } finally {
          button.disabled = false;
        }
      });
      actionsContainer.appendChild(button);
    });

    card.append(title, actionsContainer);
    container.appendChild(card);
  });

  renderAdminResponseConsole();
};

const getRenderableProperties = (properties) => {
  if (Array.isArray(properties) && properties.length > 0) {
    return properties;
  }
  return [devPropertyFallback];
};

const applyPropertyPlaceholders = () => {
  document.getElementById("property-list-state").textContent =
    "No properties available yet. Import auction CSV data to begin.";
  document.getElementById("map-empty-state").textContent =
    "No properties available yet. Import auction CSV data to begin.";
  document.getElementById("property-detail-empty").textContent =
    "No properties available yet. Import auction CSV data to begin.";
};

const renderCharts = () => {
  document.querySelectorAll(".chart-grid").forEach((grid) => {
    const key = grid.dataset.charts;
    const items = chartSets[key] || [];
    clearElement(grid);
    items.forEach((item) => {
      const card = document.createElement("div");
      card.className = "card chart-card";
      const title = document.createElement("h3");
      title.textContent = item.title;
      const hint = document.createElement("p");
      hint.className = "hint";
      hint.textContent = item.subtitle;
      const placeholder = document.createElement("div");
      placeholder.className = "chart-placeholder";
      placeholder.textContent = "Chart will render when data is available.";
      card.append(title, hint, placeholder);
      grid.appendChild(card);
    });
  });
};

const formatTimestamp = (value) => {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
};

const ensureAdminAuth = (pageKey) => {
  if (pageKey !== "admin-command-center") {
    return pageKey;
  }
  if (getAuthToken()) {
    return pageKey;
  }
  return "login";
};

const setPage = (pageId) => {
  const requestedPage = pageId in pages ? pageId : "dashboard";
  const pageKey = ensureAdminAuth(requestedPage);
  document.querySelectorAll(".page").forEach((page) => {
    page.classList.toggle("active", page.dataset.page === pageKey);
  });

  document.querySelectorAll(".nav-link[data-page]").forEach((link) => {
    link.classList.toggle("active", link.dataset.page === pageKey);
  });

  document.getElementById("page-title").textContent = pages[pageKey].title;
  document.getElementById("page-subtitle").textContent =
    pages[pageKey].subtitle;
};

const validateUuid = (value) => uuidPattern.test(value.trim());

const validateJson = (value) => {
  if (!value.trim()) {
    return true;
  }
  try {
    JSON.parse(value);
    return true;
  } catch (error) {
    return false;
  }
};

const updateMetrics = () => {
  const metrics = document.getElementById("metric-cards");
  clearElement(metrics);

  const items = [
    { label: "Active Cases", value: "—" },
    { label: "Properties", value: "—" },
    { label: "Referrals", value: "—" },
    { label: "Documents", value: "—" },
  ];

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "metric";
    const label = document.createElement("span");
    label.textContent = item.label;
    const value = document.createElement("strong");
    value.textContent = item.value;
    card.append(label, value);
    metrics.appendChild(card);
  });
};

const updateStatusSummary = () => {
  const summary = document.getElementById("case-status-summary");
  clearElement(summary);

  if (!state.enums.caseStatus.length) {
    const li = document.createElement("li");
    li.textContent = "No CaseStatus enum available from OpenAPI.";
    summary.appendChild(li);
    return;
  }

  state.enums.caseStatus.forEach((status) => {
    const li = document.createElement("li");
    li.className = "status-pill";
    const label = document.createElement("span");
    label.textContent = status;
    const value = document.createElement("strong");
    value.textContent = "—";
    li.append(label, value);
    summary.appendChild(li);
  });
};

const updateBlockedActions = () => {
  const blocked = document.getElementById("blocked-actions");
  clearElement(blocked);

  const items = [
    "Referral queueing requires active consent scope 'referral'.",
    "Document uploads with doc_type=other require meta.evidence_type.",
  ];

  items.forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    blocked.appendChild(li);
  });
};

const updateQuickLinks = () => {
  const container = document.getElementById("quick-links");
  clearElement(container);
  [
    { label: "Go to Case Management", href: "#/cases" },
    { label: "Open Document Management", href: "#/documents" },
    { label: "View Audit Logs", href: "#/audit" },
  ].forEach((link) => {
    const anchor = document.createElement("a");
    anchor.href = link.href;
    anchor.textContent = link.label;
    container.appendChild(anchor);
  });
};

const populateSelect = (selectId, values) => {
  const select = document.getElementById(selectId);
  clearElement(select);
  if (!values.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Unavailable";
    select.appendChild(option);
    select.disabled = true;
    return;
  }
  select.disabled = false;
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
};

const updateCaseListState = () => {
  const stateEl = document.getElementById("case-list-state");
  const hint = document.getElementById("case-filter-hint");
  if (!state.caseListAvailable) {
    stateEl.textContent =
      "No case listing endpoint found in OpenAPI. Case list is read-only until available.";
    hint.textContent = "Filtering requires a GET /cases endpoint.";
    document.getElementById("case-list-table").classList.add("hidden");
  } else {
    stateEl.textContent = "";
    hint.textContent = "";
    document.getElementById("case-list-table").classList.remove("hidden");
  }
  const empty = document.getElementById("case-detail-empty");
  empty.textContent = "Load a case to view lifecycle, documents, and consents.";
  document.getElementById("case-timeline-empty").textContent =
    "Timeline will appear after a case is loaded.";
};

const updatePropertyState = () => {
  const listState = document.getElementById("property-list-state");
  const exportButton = document.getElementById("property-export");
  const exportHint = document.getElementById("property-export-hint");
  const endpointPanel = document.getElementById("property-endpoint-status");
  const importButton = document.getElementById("property-import-submit");
  const importHint = document.getElementById("property-import-hint");

  if (!state.propertyEndpointsAvailable) {
    listState.textContent =
      "No property endpoints detected in OpenAPI. This page is awaiting backend support.";
    exportButton.disabled = true;
    exportHint.textContent = "Export requires a backend property export endpoint.";
    endpointPanel.textContent =
      "Property endpoints not available. Map and detail views remain read-only.";
    importButton.disabled = true;
    importHint.textContent =
      "CSV import requires admin permissions and backend support.";
  } else {
    listState.textContent = "";
    exportButton.disabled = false;
    exportHint.textContent = "";
    endpointPanel.textContent = "Property endpoints detected.";
    importButton.disabled = false;
    importHint.textContent = "Admin-only action.";
  }
  document.getElementById("property-detail-empty").textContent =
    "Select a property to view metadata and linked cases.";
};

const updateMapStatus = () => {
  const status = document.getElementById("map-status");
  if (!state.propertyEndpointsAvailable) {
    status.textContent =
      "Map initialized. Awaiting property endpoints to plot pins.";
    document.getElementById("map-empty-state").textContent =
      "No property data available to render map pins.";
  } else {
    status.textContent = "Ready to plot property pins.";
    document.getElementById("map-empty-state").textContent =
      "Pins will appear once properties are loaded.";
  }
};

const updatePropertyDetailState = () => {
  const hint = document.getElementById("property-detail-hint");
  const button = document.querySelector("#property-detail-form button");
  if (!state.propertyEndpointsAvailable) {
    hint.textContent =
      "Property detail requires backend property endpoints. Disabled until available.";
    button.disabled = true;
    document.getElementById("property-map-empty").textContent =
      "Map will update once property data is available.";
  } else {
    hint.textContent = "";
    button.disabled = false;
    document.getElementById("property-map-empty").textContent = "";
  }
};

const initMap = () => {
  const mapContainer = document.getElementById("property-map");
  if (!mapContainer || !window.L) {
    return null;
  }
  const map = L.map(mapContainer).setView([39.5, -98.35], 4);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
  return map;
};

const initDetailMap = () => {
  const mapContainer = document.getElementById("property-detail-map");
  if (!mapContainer || !window.L) {
    return null;
  }
  const map = L.map(mapContainer).setView([39.5, -98.35], 4);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
  return map;
};

const renderPropertiesTable = (properties) => {
  const tbody = document.querySelector("#property-list-table tbody");
  clearElement(tbody);
  if (!properties.length) {
    document.getElementById("property-list-state").textContent =
      "No properties found yet. Import auction CSV data to get started.";
    return;
  }
  document.getElementById("property-list-state").textContent = "";
  properties.forEach((prop) => {
    const row = document.createElement("tr");
    row.append(
      createCell(prop.address || "—"),
      createCell(prop.city || "—"),
      createCell(prop.state || "—"),
      createCell(prop.zip || "—"),
      createCell(prop.case_status || "—"),
      createCell(prop.case_id || "—")
    );
    tbody.appendChild(row);
  });
};

const renderTopDeals = (deals) => {
  const tbody = document.querySelector("#top-deals-table tbody");
  clearElement(tbody);
  if (!deals.length) {
    document.getElementById("top-deals-empty").textContent =
      "No ranked deals available yet. Import auction data to generate scores.";
    return;
  }
  document.getElementById("top-deals-empty").textContent = "";
  deals.forEach((deal) => {
    const row = document.createElement("tr");
    const auctionDate = deal.auction_date
      ? new Date(deal.auction_date).toLocaleDateString()
      : "—";
    row.append(
      createCell(deal.score ?? "—"),
      createCell(deal.tier || "—"),
      createCell(deal.address || "—"),
      createCell(auctionDate),
      createCell(deal.urgency_days ?? "—"),
      createCell(deal.exit_strategy || "—"),
      createCell(deal.case_status || "—")
    );
    tbody.appendChild(row);
  });
};

const renderLeadsTable = (leads) => {
  const tbody = document.querySelector("#leads-table tbody");
  clearElement(tbody);
  document.getElementById("leads-count").textContent = leads.length;
  if (!leads.length) {
    document.getElementById("leads-empty").textContent =
      "No leads have been ingested yet.";
    return;
  }
  document.getElementById("leads-empty").textContent = "";
  leads.forEach((lead) => {
    const row = document.createElement("tr");
    row.append(
      createCell(lead.lead_id || lead.id || "—"),
      createCell(lead.address || "—"),
      createCell(lead.city || "—"),
      createCell(lead.status || "—"),
      createCell(lead.score ?? "—")
    );
    tbody.appendChild(row);
  });
};

const renderReportsTable = (reports) => {
  const tbody = document.querySelector("#reports-table tbody");
  clearElement(tbody);
  document.getElementById("reports-count").textContent = reports.length;
  if (!reports.length) {
    document.getElementById("reports-empty").textContent =
      "No bot reports logged yet.";
    return;
  }
  document.getElementById("reports-empty").textContent = "";
  reports.forEach((report) => {
    const row = document.createElement("tr");
    row.append(
      createCell(report.bot || "—"),
      createCell(report.level || "—"),
      createCell(report.code || "—"),
      createCell(report.message || "—"),
      createCell(formatTimestamp(report.created_at))
    );
    tbody.appendChild(row);
  });
};

const renderCommandsTable = (commands) => {
  const tbody = document.querySelector("#commands-table tbody");
  clearElement(tbody);
  document.getElementById("commands-count").textContent = commands.length;
  if (!commands.length) {
    document.getElementById("commands-empty").textContent =
      "No bot commands queued yet.";
    return;
  }
  document.getElementById("commands-empty").textContent = "";
  commands.forEach((command) => {
    const row = document.createElement("tr");
    row.append(
      createCell(command.target_bot || "—"),
      createCell(command.command || "—"),
      createCell(command.status || "pending"),
      createCell(command.priority ?? "—"),
      createCell(formatTimestamp(command.created_at))
    );
    tbody.appendChild(row);
  });
};

const renderSettingsTable = (settings) => {
  const tbody = document.querySelector("#settings-table tbody");
  clearElement(tbody);
  document.getElementById("settings-count").textContent = settings.length;
  if (!settings.length) {
    document.getElementById("settings-empty").textContent =
      "No bot settings configured yet.";
    return;
  }
  document.getElementById("settings-empty").textContent = "";
  settings.forEach((setting) => {
    const row = document.createElement("tr");
    row.append(
      createCell(setting.key || "—"),
      createCell(setting.value || "—"),
      createCell(formatTimestamp(setting.updated_at))
    );
    tbody.appendChild(row);
  });
};

const renderMapPins = (map, properties) => {
  if (!map) {
    return;
  }
  const hasCoordinates = properties.some(
    (prop) => prop.latitude && prop.longitude
  );
  if (!hasCoordinates) {
    document.getElementById("map-empty-state").textContent =
      "Properties are missing coordinates. Ensure geocoding completes during import.";
    return;
  }
  properties.forEach((prop) => {
    if (prop.latitude && prop.longitude) {
      const popup = document.createElement("div");
      const address = document.createElement("div");
      address.textContent = prop.address || "—";
      const status = document.createElement("div");
      status.textContent = `Status: ${prop.case_status || "—"}`;
      popup.append(address, status);
      L.marker([prop.latitude, prop.longitude])
        .addTo(map)
        .bindPopup(popup);
    }
  });
};

const loadProperties = async (mapInstance) => {
  let properties = [];
  if (state.propertyEndpointsAvailable) {
    properties = await fetchJson(`${getApiBase()}/properties/`);
  }

  const renderableProperties = getRenderableProperties(properties);
  state.propertyList = renderableProperties;
  renderPropertiesTable(renderableProperties);
  renderMapPins(mapInstance, renderableProperties);

  if (!properties.length) {
    applyPropertyPlaceholders();
  }

  const detailFormInput = document.querySelector("#property-detail-form input[name='property_id']");
  if (detailFormInput && renderableProperties[0]?.id) {
    detailFormInput.value = renderableProperties[0].id;
  }
  await loadPropertyDetail(renderableProperties[0]?.id, state.detailMapInstance);
};

const loadPropertyDetail = async (propertyId, mapInstance) => {
  if (!propertyId) {
    return;
  }

  let detail = null;
  if (state.propertyEndpointsAvailable) {
    detail = await fetchJson(`${getApiBase()}/properties/${propertyId}`);
  } else {
    detail = state.propertyList.find((property) => property.id === propertyId) || devPropertyFallback;
  }

  const container = document.getElementById("property-detail");
  clearElement(container);
  container.append(
    createPanel("Address", detail.address || "—"),
    createPanel("Status", detail.case_status || "—"),
    createPanel("Case", detail.case_id || "—"),
    createPanel("Loan Type", detail.loan_type || "—")
  );
  if (mapInstance && detail.latitude && detail.longitude) {
    mapInstance.setView([detail.latitude, detail.longitude], 14);
    L.marker([detail.latitude, detail.longitude]).addTo(mapInstance);
    document.getElementById("property-map-empty").textContent = "";
  }
};

const loadBotOpsTables = async () => {
  try {
    const dashboard = await fetchJson(`${getApiBase()}/botops/dashboard`);
    renderLeadsTable(dashboard.leads || []);
    renderReportsTable(dashboard.reports || []);
    renderCommandsTable(dashboard.commands || []);
  } catch (error) {
    document.getElementById("leads-empty").textContent =
      "Unable to load BotOps dashboard data.";
    document.getElementById("reports-empty").textContent =
      "Unable to load BotOps dashboard data.";
    document.getElementById("commands-empty").textContent =
      "Unable to load BotOps dashboard data.";
  }

  try {
    const settings = await fetchJson(`${getApiBase()}/botops/settings`);
    renderSettingsTable(settings || []);
  } catch (error) {
    document.getElementById("settings-empty").textContent =
      "Unable to load BotOps settings.";
  }
};

const loadTopDeals = async () => {
  try {
    const deals = await fetchJson(`${getApiBase()}/deals/top`);
    renderTopDeals(deals || []);
  } catch (error) {
    document.getElementById("top-deals-empty").textContent =
      "Unable to load top deals. Check API connectivity.";
  }
};

const handleDocumentUpload = async (event) => {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData();
  const docType = form.doc_type.value;
  const evidenceType = form.evidence_type.value.trim();
  const metaRaw = form.meta.value.trim();

  formData.append("case_id", form.case_id.value.trim());
  formData.append("doc_type", docType);

  if (docType === "other") {
    let metaPayload = {};
    if (metaRaw) {
      metaPayload = JSON.parse(metaRaw) || {};
    }
    if (evidenceType && !metaPayload.evidence_type) {
      metaPayload.evidence_type = evidenceType;
    }
    formData.append("meta", JSON.stringify(metaPayload));
  } else {
    formData.append("meta", "{}");
  }

  const file = form.file.files[0];
  formData.append("file", file);

  const response = await fetch(`${getApiBase()}/documents/`, {
    method: "POST",
    body: formData,
  });

  const text = await response.text();
  document.getElementById("document-upload-response").textContent = text;
};

const handleDocumentGet = async (event) => {
  event.preventDefault();
  const docId = event.target.doc_id.value.trim();
  const response = await fetch(`${getApiBase()}/documents/${docId}`);
  const text = await response.text();
  document.getElementById("document-get-response").textContent = text;
};

const handleDocumentList = async (event) => {
  event.preventDefault();
  const caseId = event.target.case_id.value.trim();
  const response = await fetch(`${getApiBase()}/documents/case/${caseId}`);
  const text = await response.text();
  document.getElementById("document-list-response").textContent = text;
};

const handleReferralQueue = async (event) => {
  event.preventDefault();
  const form = event.target;
  const caseId = form.case_id.value.trim();
  const partnerId = form.partner_id.value.trim();
  const response = await fetch(`${getApiBase()}/cases/${caseId}/referral/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ partner_id: partnerId }),
  });
  const text = await response.text();
  document.getElementById("referral-queue-response").textContent = text;
};

const handleTrainingQuiz = async (event) => {
  event.preventDefault();
  const form = event.target;
  const response = await fetch(`${getApiBase()}/training/quiz_attempt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      case_id: form.case_id.value.trim(),
      quiz_key: form.quiz_key.value.trim(),
      answers: JSON.parse(form.answers.value.trim() || "{}"),
    }),
  });
  const text = await response.text();
  document.getElementById("training-quiz-response").textContent = text;
};

const handleAiDryRun = async (event) => {
  event.preventDefault();
  const form = event.target;
  const response = await fetch(`${getApiBase()}/ai/dryrun`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      case_id: form.case_id.value.trim(),
      prompt: form.prompt.value.trim(),
      role: form.role.value,
      policy_rule_id: form.policy_rule_id.value.trim(),
    }),
  });
  const text = await response.text();
  document.getElementById("ai-dryrun-response").textContent = text;
};

const handleConsentGrant = async (caseId, scope) => {
  const response = await fetch(`${getApiBase()}/consent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id: caseId, scope }),
  });
  if (response.ok) {
    state.consentState.set(caseId, { scope, revoked: false });
  }
  return response.text();
};

const handleConsentRevoke = async (caseId) => {
  const response = await fetch(`${getApiBase()}/consent/revoke`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id: caseId }),
  });
  if (response.ok && state.consentState.has(caseId)) {
    const record = state.consentState.get(caseId);
    state.consentState.set(caseId, { ...record, revoked: true });
  }
  return response.text();
};

const handleCaseConsentGrant = async (event) => {
  event.preventDefault();
  const caseId = document.querySelector("#case-detail-form input[name='case_id']").value.trim();
  const scopeValue = event.target.scope.value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
  const text = await handleConsentGrant(caseId, scopeValue);
  document.getElementById("case-consent-response").textContent = text;
  updateValidation();
};

const handleCaseConsentRevoke = async (event) => {
  event.preventDefault();
  const caseId = document.querySelector("#case-detail-form input[name='case_id']").value.trim();
  const text = await handleConsentRevoke(caseId);
  document.getElementById("case-consent-response").textContent = text;
  updateValidation();
};

const updateDocumentFields = () => {
  const form = document.getElementById("document-upload-form");
  const docType = form.doc_type.value;
  const metaField = document.getElementById("document-meta-field");
  const evidenceField = document.getElementById("evidence-type-field");

  if (docType === "other") {
    metaField.classList.remove("hidden");
    evidenceField.classList.remove("hidden");
  } else {
    metaField.classList.add("hidden");
    evidenceField.classList.add("hidden");
    form.meta.value = "";
    form.evidence_type.value = "";
  }
};

const updateValidation = () => {
  const docForm = document.getElementById("document-upload-form");
  const docButton = document.getElementById("document-upload-submit");
  const docType = docForm.doc_type.value;
  const hasFile = docForm.file.files.length > 0;
  const metaValid = validateJson(docForm.meta.value);
  const evidenceType = docForm.evidence_type.value.trim();
  let evidenceValid = docType !== "other";

  if (docType === "other") {
    if (docForm.meta.value.trim()) {
      try {
        const metaPayload = JSON.parse(docForm.meta.value);
        evidenceValid = Boolean(metaPayload.evidence_type || evidenceType);
      } catch (error) {
        evidenceValid = false;
      }
    } else {
      evidenceValid = evidenceType.length > 0;
    }
  }

  docButton.disabled =
    !validateUuid(docForm.case_id.value) ||
    !hasFile ||
    !metaValid ||
    !evidenceValid;

  const docGetForm = document.getElementById("document-get-form");
  document.getElementById("document-get-submit").disabled =
    !validateUuid(docGetForm.doc_id.value);

  const docListForm = document.getElementById("document-list-form");
  document.getElementById("document-list-submit").disabled =
    !validateUuid(docListForm.case_id.value);

  const referralForm = document.getElementById("referral-queue-form");
  const referralButton = document.getElementById("referral-queue-submit");
  const consentRecord = state.consentState.get(referralForm.case_id.value.trim());
  const hasReferralConsent =
    consentRecord &&
    !consentRecord.revoked &&
    consentRecord.scope.includes("referral");

  referralButton.disabled = !(
    hasReferralConsent &&
    validateUuid(referralForm.case_id.value) &&
    validateUuid(referralForm.partner_id.value)
  );

  const trainingForm = document.getElementById("training-quiz-form");
  document.getElementById("training-quiz-submit").disabled =
    !validateUuid(trainingForm.case_id.value) ||
    !trainingForm.quiz_key.value.trim() ||
    !trainingForm.answers.value.trim() ||
    !validateJson(trainingForm.answers.value);

  const aiForm = document.getElementById("ai-dryrun-form");
  document.getElementById("ai-dryrun-submit").disabled =
    !validateUuid(aiForm.case_id.value) ||
    !aiForm.prompt.value.trim() ||
    !aiForm.policy_rule_id.value.trim();

  const caseDetailId = document.querySelector("#case-detail-form input[name='case_id']").value.trim();
  const consentGrantForm = document.getElementById("case-consent-grant-form");
  const consentScope = consentGrantForm.scope.value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);

  document.getElementById("case-consent-grant-submit").disabled =
    !validateUuid(caseDetailId) || consentScope.length === 0;

  const existingConsentRecord = state.consentState.get(caseDetailId);
  document.getElementById("case-consent-revoke-submit").disabled =
    !validateUuid(caseDetailId) ||
    !existingConsentRecord ||
    existingConsentRecord.revoked;

  document.getElementById("document-upload-empty").textContent =
    "Upload evidence to attach to a case.";
  document.getElementById("document-view-empty").textContent =
    "Search for documents by case or document ID.";
  document.getElementById("referral-queue-empty").textContent =
    "Queue referrals once consent is granted.";
  document.getElementById("training-empty").textContent =
    "Submit training quiz attempts to record outcomes.";
  document.getElementById("certification-empty").textContent =
    "Certification records will appear after training completion.";
  document.getElementById("audit-empty").textContent =
    "Audit logs are system-generated; use backend reports for exports.";
  document.getElementById("ai-dryrun-empty").textContent =
    "AI dry runs require consent and policy allowance.";
  document.getElementById("ai-log-empty").textContent =
    "AI activity logs populate after AI workflows execute.";
};


const wireEvents = () => {
  document
    .getElementById("document-upload-form")
    .addEventListener("submit", handleDocumentUpload);
  document
    .getElementById("document-get-form")
    .addEventListener("submit", handleDocumentGet);
  document
    .getElementById("document-list-form")
    .addEventListener("submit", handleDocumentList);
  document
    .getElementById("referral-queue-form")
    .addEventListener("submit", handleReferralQueue);
  document
    .getElementById("training-quiz-form")
    .addEventListener("submit", handleTrainingQuiz);
  document
    .getElementById("ai-dryrun-form")
    .addEventListener("submit", handleAiDryRun);
  document
    .getElementById("case-consent-grant-form")
    .addEventListener("submit", handleCaseConsentGrant);
  document
    .getElementById("case-consent-revoke-form")
    .addEventListener("submit", handleCaseConsentRevoke);

  document.getElementById("property-import-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const fileInput = event.target.csv_file;
    if (!fileInput.files.length) {
      document.getElementById("property-import-hint").textContent =
        "Select a CSV or PDF file to import.";
      return;
    }
    const fileName = fileInput.files[0].name.toLowerCase();
    if (!fileName.endsWith(".csv") && !fileName.endsWith(".pdf")) {
      document.getElementById("property-import-hint").textContent =
        "CSV or PDF file required.";
      return;
    }
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    fetch(`${getApiBase()}/auction-imports/upload`, {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((result) => {
        document.getElementById("property-import-hint").textContent =
          `Imported ${result.records_created} properties.`;
      })
      .catch(() => {
        document.getElementById("property-import-hint").textContent =
          "Import failed. Ensure backend supports /imports/auction-csv.";
      });
  });

  document
    .getElementById("doc-type-select")
    .addEventListener("change", () => {
      updateDocumentFields();
      updateValidation();
    });

  document
    .getElementById("theme-toggle")
    .addEventListener("click", () => {
      document.body.classList.toggle("theme-dark");
    });

  document.getElementById("tour-replay").addEventListener("click", () => {
    if (!guidedTourController) {
      return;
    }
    guidedTourController.restart();
  });

  document.getElementById("api-base").addEventListener("change", () => {
    state.adminActionHistory = [];
    renderAdminResponseConsole();
  });

  document.querySelectorAll("input, textarea, select").forEach((el) => {
    el.addEventListener("input", updateValidation);
  });

  document.getElementById("map-refresh").addEventListener("click", () => {
    updateMapStatus();
  });

  document
    .getElementById("property-detail-form")
    .addEventListener("submit", (event) => {
      event.preventDefault();
      const propertyId = event.target.property_id.value.trim();
      loadPropertyDetail(propertyId, state.detailMapInstance);
    });


  document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const response = await fetch(`${getApiBase()}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: form.email.value.trim(),
        password: form.password.value,
      }),
    });

    let payload = null;
    try {
      payload = await response.json();
    } catch (error) {
      payload = { detail: "Unable to parse login response" };
    }

    if (!response.ok || !payload?.access_token) {
      document.getElementById("login-response").textContent =
        payload?.detail || "Login failed.";
      clearAuthToken();
      return;
    }

    localStorage.setItem(AUTH_TOKEN_KEY, payload.access_token);
    document.getElementById("login-response").textContent = "";
    window.location.hash = "#/admin-command-center";
  });

  document.getElementById("admin-logout").addEventListener("click", () => {
    clearAuthToken();
    window.location.hash = "#/login";
  });

  window.addEventListener("hashchange", () => {
    const page = window.location.hash.replace("#/", "");
    setPage(page || "dashboard");
    window.setTimeout(() => {
      maybeAutoStartGuidedTour();
    }, 120);
  });
};

const initapp = async () => {
  const page = window.location.hash.replace("#/", "") || "dashboard";

  setPage(page);
  renderCharts();

  if (!guidedTourController) {
    guidedTourController = createGuidedTourController({
      setPageFn: setPage,
      getCurrentPageFn: getCurrentPageFromHash,
    });
  }

  if (!apiBaseInput.value && window.__API_BASE_URL__) {
    apiBaseInput.value = window.__API_BASE_URL__;
  }

  let openApi = null;

  try {
    openApi = await fetchOpenApi();
    state.openApi = openApi;

    const schemas = openApi?.components?.schemas || {};

    state.enums.caseStatus = extractEnum(schemas, "CaseStatus") || [];
    state.enums.documentType = extractEnum(schemas, "DocumentType") || [];
    state.enums.referralStatus = extractEnum(schemas, "ReferralStatus") || [];

    state.caseListAvailable = detectEndpoint(openApi, "/cases", "get");
    state.propertyEndpointsAvailable = detectPropertyEndpoints(openApi);

  } catch (error) {
    console.error("OpenAPI load failed:", error);

    const metrics = document.getElementById("metric-cards");
    if (metrics) {
      metrics.textContent =
        "Unable to load OpenAPI schema. Check API base URL.";
    }

    state.enums.caseStatus = [];
    state.enums.documentType = [];
    state.enums.referralStatus = [];
  }

  populateSelect("doc-type-select", state.enums.documentType || []);
  populateSelect("case-status-filter", state.enums.caseStatus || []);
  populateSelect("ai-role-select", ["assistive", "advisory", "automated"]);

  updateMetrics();
  updateStatusSummary();
  updateBlockedActions();
  updateQuickLinks();
  updateCaseListState();
  updatePropertyState();
  updateMapStatus();
  updatePropertyDetailState();
  renderAdminCommandCenter();

  const referralList = document.getElementById("referral-status-list");
  clearElement(referralList);
  if (state.enums.referralStatus.length) {
    state.enums.referralStatus.forEach((status) => {
      const li = document.createElement("li");
      li.textContent = status;
      referralList.appendChild(li);
    });
    document.getElementById("referral-status-empty").textContent =
      "Select a case to view referral history.";
  } else {
    referralList.textContent = "ReferralStatus enum not available.";
    document.getElementById("referral-status-empty").textContent =
      "Unable to render status list without backend enums.";
  }

  const map = initMap();
  state.mapInstance = map;
  if (!map) {
    document.getElementById("map-status").textContent =
      "Map library unavailable. Ensure Leaflet loads in production.";
  }
  const detailMap = initDetailMap();
  state.detailMapInstance = detailMap;
  if (!detailMap) {
    document.getElementById("property-map-status").textContent =
      "Map library unavailable. Ensure Leaflet loads in production.";
  }

  wireEvents();
  updateDocumentFields();
  updateValidation();

  try {
    await loadProperties(map);
  } catch (error) {
    document.getElementById("property-list-state").textContent =
      "Unable to load properties. Check API connectivity.";
  }

  await loadTopDeals();

  try {
    await loadBotOpsTables();
  } catch (error) {
    document.getElementById("leads-empty").textContent =
      "Unable to load BotOps tables. Check API connectivity.";
  }

  const currentPage = window.location.hash.replace("#/", "");
  setPage(currentPage || "dashboard");
  await maybeAutoStartGuidedTour();
};

initapp().catch((error) => {
  console.error("Application failed to initialize:", error);

  const metrics = document.getElementById("metric-cards");
  if (metrics) {
    metrics.textContent =
      "Unable to initialize dashboard. Check API base URL.";
  }

  renderCharts();

  const fallbackPage = window.location.hash.replace("#/", "") || "dashboard";
  setPage(fallbackPage);
});
