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
};

const uuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const apiBaseInput = document.getElementById("api-base");

const pages = {
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
};

const getApiBase = () => {
  const override = apiBaseInput.value.trim();
  if (override) {
    return override.endsWith("/") ? override.slice(0, -1) : override;
  }
  const configured = window.__API_BASE_URL__ || "";
  return configured.endsWith("/") ? configured.slice(0, -1) : configured;
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

const setPage = (pageId) => {
  const pageKey = pageId in pages ? pageId : "dashboard";
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
  if (!state.propertyEndpointsAvailable) {
    return;
  }
  const properties = await fetchJson(`${getApiBase()}/properties/`);
  renderPropertiesTable(properties);
  renderMapPins(mapInstance, properties);
};

const loadPropertyDetail = async (propertyId, mapInstance) => {
  if (!state.propertyEndpointsAvailable || !propertyId) {
    return;
  }
  const detail = await fetchJson(`${getApiBase()}/properties/${propertyId}`);
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
    fetch(`${getApiBase()}/imports/auction`, {
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

  window.addEventListener("hashchange", () => {
    const page = window.location.hash.replace("#/", "");
    setPage(page || "dashboard");
  });
};

const initapp = async () => {
  const page = window.location.hash.replace("#/", "");
  setPage(page || "dashboard");
  renderCharts();
  if (!apiBaseInput.value && window.__API_BASE_URL__) {
    apiBaseInput.value = window.__API_BASE_URL__;
  }

  let openApi = null;
  try {
    openApi = await fetchOpenApi();
    state.openApi = openApi;
    const schemas = openApi.components?.schemas;
    state.enums.caseStatus = extractEnum(schemas, "CaseStatus");
    state.enums.documentType = extractEnum(schemas, "DocumentType");
    state.enums.referralStatus = extractEnum(schemas, "ReferralStatus");

    state.caseListAvailable = detectEndpoint(openApi, "/cases", "get");
    state.propertyEndpointsAvailable = detectPropertyEndpoints(openApi);
  } catch (error) {
    document.getElementById("metric-cards").textContent =
      "Unable to load OpenAPI schema. Check API base URL.";
  }

  populateSelect("doc-type-select", state.enums.documentType);
  populateSelect("case-status-filter", state.enums.caseStatus);
  populateSelect("ai-role-select", ["assistive", "advisory", "automated"]);

  updateMetrics();
  updateStatusSummary();
  updateBlockedActions();
  updateQuickLinks();
  updateCaseListState();
  updatePropertyState();
  updateMapStatus();
  updatePropertyDetailState();

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
};

initapp().catch((error) => {
  document.getElementById("metric-cards").textContent =
    "Unable to initialize dashboard. Check API base URL.";
  renderCharts();
  setPage(window.location.hash.replace("#/", "") || "dashboard");
  console.error(error);
});

