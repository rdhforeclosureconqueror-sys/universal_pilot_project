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
};

const getApiBase = () => {
  const base = apiBaseInput.value.trim();
  if (!base) {
    return "";
  }
  return base.endsWith("/") ? base.slice(0, -1) : base;
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
  metrics.innerHTML = "";

  const items = [
    { label: "Active Cases", value: "—" },
    { label: "Properties", value: "—" },
    { label: "Referrals", value: "—" },
    { label: "Documents", value: "—" },
  ];

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "metric";
    card.innerHTML = `<span>${item.label}</span><strong>${item.value}</strong>`;
    metrics.appendChild(card);
  });
};

const updateStatusSummary = () => {
  const summary = document.getElementById("case-status-summary");
  summary.innerHTML = "";

  if (!state.enums.caseStatus.length) {
    summary.innerHTML = "<li>No CaseStatus enum available from OpenAPI.</li>";
    return;
  }

  state.enums.caseStatus.forEach((status) => {
    const li = document.createElement("li");
    li.className = "status-pill";
    li.innerHTML = `<span>${status}</span><strong>—</strong>`;
    summary.appendChild(li);
  });
};

const updateBlockedActions = () => {
  const blocked = document.getElementById("blocked-actions");
  blocked.innerHTML = "";

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
  container.innerHTML = "";
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
  select.innerHTML = "";
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

  const consentRecord = state.consentState.get(caseDetailId);
  document.getElementById("case-consent-revoke-submit").disabled =
    !validateUuid(caseDetailId) || !consentRecord || consentRecord.revoked;
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
    document.getElementById("property-import-hint").textContent =
      "CSV import requires backend support and admin authorization.";
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

  window.addEventListener("hashchange", () => {
    const page = window.location.hash.replace("#/", "");
    setPage(page || "dashboard");
  });
};

const init = async () => {
  const openApi = await fetchOpenApi();
  state.openApi = openApi;
  const schemas = openApi.components?.schemas;
  state.enums.caseStatus = extractEnum(schemas, "CaseStatus");
  state.enums.documentType = extractEnum(schemas, "DocumentType");
  state.enums.referralStatus = extractEnum(schemas, "ReferralStatus");

  state.caseListAvailable = detectEndpoint(openApi, "/cases", "get");
  state.propertyEndpointsAvailable = detectPropertyEndpoints(openApi);

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
  referralList.innerHTML = "";
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
  if (!map) {
    document.getElementById("map-status").textContent =
      "Map library unavailable. Ensure Leaflet loads in production.";
  }
  const detailMap = initDetailMap();
  if (!detailMap) {
    document.getElementById("property-map-status").textContent =
      "Map library unavailable. Ensure Leaflet loads in production.";
  }

  wireEvents();
  updateDocumentFields();
  updateValidation();

  const page = window.location.hash.replace("#/", "");
  setPage(page || "dashboard");
};

init().catch((error) => {
  document.getElementById("metric-cards").textContent =
    "Unable to load OpenAPI schema. Check API base URL.";
  console.error(error);
});
