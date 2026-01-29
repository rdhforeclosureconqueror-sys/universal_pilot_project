const ENUMS = {
  caseStatus: [],
  documentType: [],
  referralStatus: [],
  caseStatus: [
    "intake_submitted",
    "intake_incomplete",
    "under_review",
    "in_progress",
    "program_completed_positive_outcome",
    "case_closed_other_outcome",
  ],
  documentType: [
    "id_verification",
    "income_verification",
    "lease_or_mortgage",
    "foreclosure_notice",
    "eviction_notice",
    "signed_consent",
    "taskcheck_evidence",
    "training_proof",
    "system_doc",
    "other",
  ],
  referralStatus: ["draft", "queued", "sent", "failed", "cancelled"],
  aiRoles: ["assistive", "advisory", "automated"],
};

const MODEL_FIELDS = {
  case: [
    "id (UUID)",
    "status (CaseStatus)",
    "created_by (UUID)",
    "created_at (DateTime)",
    "program_type",
    "policy_version_id (UUID)",
  ],
  document: [
    "id (UUID)",
    "case_id (UUID)",
    "uploaded_by (UUID)",
    "doc_type (DocumentType)",
    "meta (JSON)",
    "uploaded_at (DateTime)",
  ],
  consent: [
    "id (UUID)",
    "case_id (UUID)",
    "granted_by_user_id (UUID)",
    "scope (JSON)",
    "valid_from (DateTime)",
    "valid_until (DateTime)",
    "revoked (Boolean)",
  ],
  taskcheck: [
    "id (UUID)",
    "case_id (UUID)",
    "skill_key (String)",
    "passed (Boolean)",
    "evidence (JSON)",
    "created_at (DateTime)",
  ],
  referral: [
    "id (UUID)",
    "case_id (UUID)",
    "partner_id (UUID)",
    "status (ReferralStatus)",
    "payload (JSON)",
    "created_at (DateTime)",
  ],
  certification: [
    "id (UUID)",
    "user_id (UUID)",
    "cert_key (String)",
    "issued_at (DateTime)",
    "expires_at (DateTime)",
  ],
  auditLog: [
    "id (UUID)",
    "case_id (UUID)",
    "actor_id (UUID)",
    "actor_is_ai (Boolean)",
    "action_type (String)",
    "reason_code (String)",
    "before_json (JSON)",
    "after_json (JSON)",
    "policy_version_id (UUID)",
    "created_at (DateTime)",
  ],
  aiActivityLog: [
    "id (UUID)",
    "case_id (UUID)",
    "policy_version_id (UUID)",
    "ai_role (String)",
    "model_provider (String)",
    "model_name (String)",
    "model_version (String)",
    "prompt_hash (String)",
    "policy_rule_id (String)",
    "confidence_score (Numeric(5,4))",
    "human_override (Boolean)",
    "incident_type (String)",
    "admin_review_required (Boolean)",
    "resolved_at (DateTime)",
    "created_at (DateTime)",
  ],
};

const consentState = new Map();

const uuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const apiBaseInput = document.getElementById("api-base");

const listCaseStatuses = () => {
  const list = document.getElementById("case-status-list");
  list.innerHTML = "";
  if (!ENUMS.caseStatus.length) {
    const li = document.createElement("li");
    li.textContent = "No CaseStatus enum found in OpenAPI.";
    list.appendChild(li);
    return;
  }
  ENUMS.caseStatus.forEach((status) => {
    const li = document.createElement("li");
    li.textContent = status;
    list.appendChild(li);
  });
};

const listReferralStatuses = () => {
  const list = document.getElementById("referral-status-list");
  list.innerHTML = "";
  if (!ENUMS.referralStatus.length) {
    const li = document.createElement("li");
    li.textContent = "No ReferralStatus enum found in OpenAPI.";
    list.appendChild(li);
    return;
  }
  ENUMS.referralStatus.forEach((status) => {
    const li = document.createElement("li");
    li.textContent = status;
    list.appendChild(li);
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

const renderSchemaList = (targetId, fields) => {
  const container = document.getElementById(targetId);
  container.innerHTML = "";
  const list = document.createElement("ul");
  fields.forEach((field) => {
    const li = document.createElement("li");
    li.textContent = field;
    list.appendChild(li);
  });
  container.appendChild(list);
};

const getApiBase = () => {
  const base = apiBaseInput.value.trim();
  if (!base) {
    return "";
  }
  return base.endsWith("/") ? base.slice(0, -1) : base;
};

const updateResponse = (targetId, payload) => {
  const el = document.getElementById(targetId);
  el.textContent = payload;
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

const parseJsonField = (value) => {
  if (!value) {
    return null;
  }
  return JSON.parse(value);
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

const handleCaseCreate = async (event) => {
  event.preventDefault();
  const form = event.target;
  const programKey = form.program_key.value.trim();
  const createdBy = form.created_by.value.trim();
  const metaRaw = form.meta.value.trim();

  const payload = {
    program_key: programKey,
    created_by: createdBy,
    meta: metaRaw ? parseJsonField(metaRaw) : null,
  };

  const response = await fetch(`${getApiBase()}/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const text = await response.text();
  updateResponse("case-create-response", text);
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
      metaPayload = parseJsonField(metaRaw) || {};
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
  updateResponse("document-upload-response", text);
};

const handleDocumentGet = async (event) => {
  event.preventDefault();
  const form = event.target;
  const docId = form.doc_id.value.trim();
  const response = await fetch(`${getApiBase()}/documents/${docId}`);
  const text = await response.text();
  updateResponse("document-get-response", text);
};

const handleDocumentList = async (event) => {
  event.preventDefault();
  const form = event.target;
  const caseId = form.case_id.value.trim();
  const response = await fetch(`${getApiBase()}/documents/case/${caseId}`);
  const text = await response.text();
  updateResponse("document-list-response", text);
};

const handleConsentGrant = async (event) => {
  event.preventDefault();
  const form = event.target;
  const caseId = form.case_id.value.trim();
  const scopeList = form.scope.value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);

  const response = await fetch(`${getApiBase()}/consent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id: caseId, scope: scopeList }),
  });

  if (response.ok) {
    consentState.set(caseId, { scope: scopeList, revoked: false });
  }

  const text = await response.text();
  updateResponse("consent-grant-response", text);
  updateConsentDependentButtons();
};

const handleConsentRevoke = async (event) => {
  event.preventDefault();
  const form = event.target;
  const caseId = form.case_id.value.trim();

  const response = await fetch(`${getApiBase()}/consent/revoke`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id: caseId }),
  });

  if (response.ok && consentState.has(caseId)) {
    const record = consentState.get(caseId);
    consentState.set(caseId, { ...record, revoked: true });
  }

  const text = await response.text();
  updateResponse("consent-revoke-response", text);
  updateConsentDependentButtons();
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
  updateResponse("referral-queue-response", text);
};

const handleTrainingQuiz = async (event) => {
  event.preventDefault();
  const form = event.target;
  const caseId = form.case_id.value.trim();
  const quizKey = form.quiz_key.value.trim();
  const answersRaw = form.answers.value.trim();

  const response = await fetch(`${getApiBase()}/training/quiz_attempt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      case_id: caseId,
      quiz_key: quizKey,
      answers: parseJsonField(answersRaw) || {},
    }),
  });

  const text = await response.text();
  updateResponse("training-quiz-response", text);
};

const handleAiDryRun = async (event) => {
  event.preventDefault();
  const form = event.target;
  const caseId = form.case_id.value.trim();
  const prompt = form.prompt.value.trim();
  const role = form.role.value;
  const policyRuleId = form.policy_rule_id.value.trim();

  const response = await fetch(`${getApiBase()}/ai/dryrun`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      case_id: caseId,
      prompt,
      role,
      policy_rule_id: policyRuleId,
    }),
  });

  const text = await response.text();
  updateResponse("ai-dryrun-response", text);
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

const updateConsentDependentButtons = () => {
  const referralForm = document.getElementById("referral-queue-form");
  const caseId = referralForm.case_id.value.trim();
  const record = consentState.get(caseId);
  const hasReferralConsent =
    record && !record.revoked && record.scope.includes("referral");

  const consentRevokeForm = document.getElementById("consent-revoke-form");
  const revokeCaseId = consentRevokeForm.case_id.value.trim();
  const revokeRecord = consentState.get(revokeCaseId);
  const canRevoke = revokeRecord && !revokeRecord.revoked;

  const referralButton = document.getElementById("referral-queue-submit");
  const referralValid =
    validateUuid(caseId) && validateUuid(referralForm.partner_id.value.trim());
  referralButton.disabled = !(hasReferralConsent && referralValid);

  const revokeButton = document.getElementById("consent-revoke-submit");
  revokeButton.disabled = !(canRevoke && validateUuid(revokeCaseId));
};

const updateFormValidation = () => {
  const caseForm = document.getElementById("case-create-form");
  const caseButton = document.getElementById("case-create-submit");
  const caseMetaValid = validateJson(caseForm.meta.value);
  caseButton.disabled =
    !caseForm.program_key.value.trim() ||
    !validateUuid(caseForm.created_by.value) ||
    !caseMetaValid;

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
  const docGetButton = document.getElementById("document-get-submit");
  docGetButton.disabled = !validateUuid(docGetForm.doc_id.value);

  const docListForm = document.getElementById("document-list-form");
  const docListButton = document.getElementById("document-list-submit");
  docListButton.disabled = !validateUuid(docListForm.case_id.value);

  const consentGrantForm = document.getElementById("consent-grant-form");
  const consentGrantButton = document.getElementById("consent-grant-submit");
  const scopeValue = consentGrantForm.scope.value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
  consentGrantButton.disabled =
    !validateUuid(consentGrantForm.case_id.value) || scopeValue.length === 0;

  const trainingForm = document.getElementById("training-quiz-form");
  const trainingButton = document.getElementById("training-quiz-submit");
  trainingButton.disabled =
    !validateUuid(trainingForm.case_id.value) ||
    !trainingForm.quiz_key.value.trim() ||
    !validateJson(trainingForm.answers.value) ||
    !trainingForm.answers.value.trim();

  const aiForm = document.getElementById("ai-dryrun-form");
  const aiButton = document.getElementById("ai-dryrun-submit");
  aiButton.disabled =
    !validateUuid(aiForm.case_id.value) ||
    !aiForm.prompt.value.trim() ||
    !aiForm.policy_rule_id.value.trim();

  updateConsentDependentButtons();
};

const wireEvents = () => {
  document
    .getElementById("case-create-form")
    .addEventListener("submit", handleCaseCreate);
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
    .getElementById("consent-grant-form")
    .addEventListener("submit", handleConsentGrant);
  document
    .getElementById("consent-revoke-form")
    .addEventListener("submit", handleConsentRevoke);
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
    .getElementById("doc-type-select")
    .addEventListener("change", () => {
      updateDocumentFields();
      updateFormValidation();
    });

  document.querySelectorAll("input, textarea, select").forEach((el) => {
    el.addEventListener("input", updateFormValidation);
  });
};

const init = async () => {
  try {
    const openApi = await fetchOpenApi();
    const schemas = openApi.components?.schemas;
    ENUMS.caseStatus = extractEnum(schemas, "CaseStatus");
    ENUMS.documentType = extractEnum(schemas, "DocumentType");
    ENUMS.referralStatus = extractEnum(schemas, "ReferralStatus");
  } catch (error) {
    updateResponse(
      "case-create-response",
      "Unable to load OpenAPI schema; enums unavailable."
    );
  }

  listCaseStatuses();
  listReferralStatuses();
  populateSelect("doc-type-select", ENUMS.documentType);
  populateSelect("ai-role-select", ENUMS.aiRoles);

  renderSchemaList("case-schema", MODEL_FIELDS.case);
  renderSchemaList("taskcheck-schema", MODEL_FIELDS.taskcheck);
  renderSchemaList("certification-schema", MODEL_FIELDS.certification);
  renderSchemaList("audit-log-schema", MODEL_FIELDS.auditLog);
  renderSchemaList("ai-log-schema", MODEL_FIELDS.aiActivityLog);

  updateDocumentFields();
  wireEvents();
  updateFormValidation();
};

init();
