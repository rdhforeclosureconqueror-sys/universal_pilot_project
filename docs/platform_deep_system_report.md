# Platform Deep System Report

## 1. Executive Summary

Universal Pilot is a housing intervention operations platform that combines foreclosure analytics, lead intelligence, veteran and essential-worker assistance pathways, partner routing, portfolio tracking, and AI-driven operator workflows into a single command surface.

At a practical level, the platform solves three operational problems:

1. **Fragmented intervention workflows**: it centralizes case intake, lead scoring, foreclosure analysis, partner routing, and assistance planning behind one API/backend.
2. **Slow operator execution**: it gives admins both button-driven controls (Admin Command Center) and natural-language execution/explanation via Mufasa.
3. **Governance and extensibility risk**: it introduces a policy-validated module registry/loader and a bounded DomainServiceBroker so runtime expansion is controlled rather than arbitrary.

For engineering teams, the platform is a FastAPI monolith with service-layer orchestration and a static+React-style admin UX surface. For operators, it is a task console with verification endpoints and AI assistance. For investors, it is a system designed to triage and stabilize distressed homeowners with measurable, reportable impact outputs.

---

## 2. System Overview

### Backend runtime

- The backend is assembled in `api/main.py` as a single FastAPI app with domain routers from `api/routes/*` and admin/member routers from `app/api/routes/*`.
- Startup includes two operational bootstrap actions:
  - ensuring admin user existence,
  - loading active modules through `load_modules_on_startup(app)`.

### Frontend/admin layer

- Static frontend assets are mounted from `/frontend` and served via `/static` and root handlers.
- Admin operational UX is implemented under:
  - `frontend/src/pages/admin/AdminCommandCenter.tsx`
  - `frontend/src/components/AdminActionButton.tsx`
  - `frontend/src/components/MufasaAssistant.tsx`
  - `frontend/src/services/apiClient.ts`

### AI orchestration layer

- `app/services/ai_orchestration_service.py` provides:
  - advisory/execute/voice flows,
  - Mufasa action execution (`handle_mufasa_prompt`),
  - Mufasa explainer mode (`handle_mufasa_question`),
  - prompt intent routing and fallback behavior.

### Module system

- `ModuleRegistry` model stores module specs (permissions, required services, data schema, allowed actions, lifecycle flags).
- `ModuleRegistryService` handles validation, policy checks, activation/deprecation, and lifecycle audit logging.
- `ModuleLoaderService` reads active modules and registers runtime routes for module actions.

### API routing structure (high level)

- Core domains: `/leads*`, `/foreclosure*`, `/essential-worker*`, `/portfolio*`, `/membership*`, `/impact*`, `/verify*`, `/pipeline*`, `/partner/v1*`, `/partners*`
- AI admin: `/admin/ai/*` and specifically `/admin/ai/mufasa/*`
- System admin: `/admin/system/*`

---

## 3. AI Orchestration Architecture

### Core files and responsibilities

- `app/services/ai_orchestration_service.py`
  - `handle_mufasa_prompt(...)`: top-level Mufasa router for action vs question behavior.
  - `handle_mufasa_question(...)`: platform explanation/investor Q&A mode.
  - `_execute_mufasa_actions(...)`: multi-domain command execution pipeline.
  - `_is_system_action_prompt(...)`: keyword-based action classifier.

### How `handle_mufasa_prompt` works

1. Receive prompt + user + DB session.
2. Determine prompt type using `_is_system_action_prompt`:
   - action/system command path,
   - platform question/explainer path.
3. If action path:
   - call `_execute_mufasa_actions`,
   - aggregate `actions_executed`, `results`, `response_fragments`.
4. If question path:
   - call `handle_mufasa_question` for conversational answer generation.
5. Persist `AICommandLog` row with prompt, response, executed actions, and results.
6. Return `{response, actions_executed, results}` to API caller.

### Action routing behavior

The action path fans out based on keywords and can trigger multiple services in sequence, including:

- foreclosure scan / lead ingest / scoring / case creation,
- foreclosure profile + priority computation,
- skiptrace owner/borrower lookup,
- essential worker profile/discovery/plan,
- veteran benefit flows,
- portfolio operations,
- diagnostics,
- investor demo macro sequence (`run investor demo`).

### Question/explainer behavior

`handle_mufasa_question` builds a context bundle from `PlatformKnowledgeService` and then:

1. attempts OpenAI response generation if `OPENAI_API_KEY` is available,
2. otherwise returns deterministic fallback explanation using domain/capability summaries.

### Fallback logic

- If OpenAI SDK/API fails at runtime, the function catches and falls back to deterministic summary text.
- This ensures the `/chat` and `/explain` surfaces still return meaningful responses in disconnected environments.

### Investor mode

- `investor_mode` is passed from API schema to orchestration.
- In explainer path, investor mode modifies system prompt intent to emphasize business value, differentiation, and impact framing.

### Prompt-to-action step-by-step (example)

Prompt: **“Analyze foreclosure case and run skiptrace”**

1. API receives prompt at `/admin/ai/mufasa/chat`.
2. Route verifies admin role and invokes `handle_mufasa_prompt`.
3. `_is_system_action_prompt` classifies as system command.
4. `_execute_mufasa_actions` executes matching handlers:
   - foreclosure analysis/priority path,
   - skiptrace lookup path.
5. Aggregated response text + action/result payloads are returned.
6. `AICommandLog` stores full interaction for audit/debugging.
7. Frontend chat renders response and executed actions list.

---

## 4. Platform Knowledge Engine

### Service

`app/services/platform_knowledge_service.py`

### Purpose

Provides a normalized knowledge layer so AI can explain what the platform is, what it can do, how architecture works, and what modules/services are currently registered.

### Methods

- `get_platform_overview()`
  - combines operational report excerpt, architecture summary, and capability summary.
- `get_capability_summary()`
  - returns capability-report excerpt plus known domain list.
- `get_domain_capabilities(domain_name)`
  - returns service map for requested domain and known domains list.
- `get_architecture_summary()`
  - returns architecture-doc excerpt + operational-doc excerpt.
- `get_module_descriptions()`
  - queries `ModuleRegistry` entries and returns module metadata for AI context.

### Knowledge inputs used

- `docs/platform_operational_report.md`
- `docs/platform_capability_report.md`
- `docs/platform_v1_architecture.md`
- module registry DB rows
- DomainServiceBroker allowed-services map

### Why this matters

Mufasa can answer “what does the platform do?” and “how is it architected?” using concrete internal context rather than generic LLM priors.

---

## 5. Module System Architecture

### Core components

1. **Model**: `ModuleRegistry` (`app/models/module_registry.py`)
   - module_name, module_type, version
   - permissions, required_services, data_schema, allowed_actions
   - lifecycle: status, validation_errors, policy_validation_status, is_active, activated_at

2. **Service**: `ModuleRegistryService` (`app/services/module_registry_service.py`)
   - registers module specs
   - validates structure and policy constraints
   - activates modules (and deprecates prior active versions)
   - logs lifecycle audit events

3. **Runtime loader**: `ModuleLoaderService` (`app/services/module_loader_service.py`)
   - loads active modules,
   - validates spec compatibility,
   - registers module action routes dynamically

4. **Startup hook**: `load_modules_on_startup(app)`
   - called in `api/main.py` startup event
   - ensures active module actions are available without manual route edits

### Validation/policy controls

- Structural checks enforce non-empty permissions/required_services/data_schema/allowed_actions.
- Default policy hook forbids wildcard permissions/actions (`*`).
- Activation path enforces validation before module activation.

### Runtime extension mechanism

- Module definitions can introduce new action capabilities (bounded to broker mappings).
- Loader registers routes for active module actions dynamically.
- This supports controlled expansion without core API redeploy of static route code.

---

## 6. Domain Service Broker

### Design summary

`DomainServiceBroker` is a bounded dispatcher between module actions and internal domain service handlers.

### Key controls

1. **Allowed services registry**
   - broker maintains explicit `allowed_services` set.
2. **Action-handler map**
   - action names map to `(service_name, handler, requires_actor)` tuples.
3. **Safety checks before execution**
   - action must be in module `allowed_actions`.
   - mapped service must appear in module `required_services`.
   - actor requirements are enforced when needed.
4. **No arbitrary execution path**
   - unknown action returns 501.
   - unknown service requirement fails validation.

### Why this reduces unsafe AI execution

The AI/module layer cannot directly run arbitrary DB/code operations. It can only invoke pre-mapped, reviewed handlers that are explicitly permitted by module spec and broker policy checks.

---

## 7. Domain Capability Breakdown

> For each domain: service, purpose, key functions, API routes, expected outputs.

### A) Lead Intelligence

- **Service**: `app/services/lead_intelligence_service.py`
- **Purpose**: ingest and score distressed-property leads, convert strong leads into cases.
- **Key functions**:
  - `ingest_leads`
  - `deduplicate_leads`
  - `score_property_lead`
  - `create_case_from_lead`
  - `weekly_foreclosure_scan`
- **API endpoints**:
  - `POST /leads/intelligence/ingest`
  - `POST /leads/intelligence/score`
  - `POST /leads/intelligence/ingest-csv`
  - `GET /leads/` (basic lead listing)
- **Expected outputs**:
  - lead ingest counts,
  - score/grade/recommended action,
  - optional created case ID,
  - connector scan totals.

### B) Foreclosure Intelligence

- **Services**:
  - `app/services/foreclosure_intelligence_service.py`
  - `app/services/property_analysis_service.py`
- **Purpose**: construct foreclosure case profiles and compute intervention urgency/classification.
- **Key functions**:
  - `create_foreclosure_profile`
  - `calculate_case_priority`
  - `calculate_equity`, `calculate_ltv`, `calculate_rescue_score`, `calculate_acquisition_score`, `classify_intervention`
- **API endpoints**:
  - `POST /foreclosure/create-profile`
  - `POST /foreclosure/analyze-property`
  - `POST /pipeline/foreclosure-analysis`
- **Expected outputs**:
  - profile/case references,
  - equity/LTV/scores,
  - intervention classification,
  - priority tier and route recommendation.

### C) Veteran Intelligence

- **Service**: `app/services/veteran_intelligence_service.py`
- **Purpose**: veteran profile management, benefit eligibility/value/plans/docs, partner reporting.
- **Key functions**:
  - `upsert_veteran_profile`
  - `match_benefits`
  - `calculate_benefit_value`
  - `generate_action_plan`
  - `generate_documents`
  - `update_benefit_progress`
  - `partner_aggregate_report`
- **API endpoints**:
  - `GET /partner/v1/veterans/benefit-discovery-summary`
  - `POST /partner/v1/veterans/integration-ping`
  - plus Mufasa action paths
- **Expected outputs**:
  - eligible benefits and values,
  - action plans/documents,
  - aggregate partner-facing reporting.

### D) Essential Worker Housing

- **Service**: `app/services/essential_worker_housing_service.py`
- **Purpose**: match worker profiles to assistance programs and produce actionable plans.
- **Key functions**:
  - `upsert_worker_profile`
  - `discover_housing_programs`
  - `calculate_assistance_value`
  - `generate_homebuyer_action_plan`
  - `generate_required_documents`
- **API endpoints**:
  - `POST /essential-worker/profile`
  - `POST /essential-worker/discover-benefits`
  - `POST /essential-worker/action-plan`
- **Expected outputs**:
  - profile IDs,
  - eligible program list + estimated totals,
  - plan steps + required documents.

### E) Skiptrace

- **Service**: `app/services/skiptrace_service.py`
- **Purpose**: contact discovery for owner/borrower outreach.
- **Key functions**:
  - `skiptrace_property_owner`
  - `skiptrace_case_owner`
- **API endpoints**:
  - verification path: `GET /verify/skiptrace-integration`
  - Mufasa action paths for property/case skiptrace
- **Expected outputs**:
  - owner/contact details including phone/email arrays.

### F) Property Analysis

- **Service**: `app/services/property_analysis_service.py`
- **Purpose**: valuation/risk/acquisition scoring primitives used by foreclosure and pipeline routes.
- **Key functions**:
  - `calculate_equity`
  - `calculate_ltv`
  - `calculate_rescue_score`
  - `calculate_acquisition_score`
  - `classify_intervention`
- **API endpoints**:
  - invoked by `/foreclosure/analyze-property`, `/pipeline/foreclosure-analysis`, `/verify/phase9`, `/verify/phase10`
- **Expected outputs**:
  - numeric analytics for intervention selection.

### G) Partner Routing

- **Service**: `app/services/partner_routing_service.py`
- **Purpose**: assign case routing to partner organizations by category/state context.
- **Key functions**:
  - `route_case_to_partner`
- **API endpoints**:
  - `POST /partners/route-case`
  - partner read APIs under `/partner/v1/cases/*`
- **Expected outputs**:
  - referral IDs, routing categories, referral statuses.

### H) Portfolio Management

- **Service**: `app/services/property_portfolio_service.py`
- **Purpose**: maintain asset inventory and summarize portfolio equity.
- **Key functions**:
  - `add_property_to_portfolio`
  - `calculate_portfolio_equity`
- **API endpoints**:
  - `POST /portfolio/add-property`
  - `GET /portfolio/summary`
- **Expected outputs**:
  - asset IDs,
  - totals for assets/value/loans/equity.

### I) Membership System

- **Service**: `app/services/membership_service.py`
- **Purpose**: create and manage member program profiles/installments.
- **Key functions**:
  - `create_membership`
  - membership/admin dashboard supporting services
- **API endpoints**:
  - `POST /membership/create`
  - admin dashboards: `/admin/memberships*`
- **Expected outputs**:
  - membership IDs/status metadata,
  - filtered admin risk and installment views.

### J) Training System

- **Service**: `app/services/system_training_service.py`
- **Purpose**: provide training content and certification-adjacent workflow support.
- **Key functions**:
  - training overview/guide/step retrieval functions
- **API endpoints**:
  - `POST /training/quiz_attempt`
  - `GET /training/system-overview`
  - `GET /training/workflow-guide`
  - `GET /training/step/{step_id}`
- **Expected outputs**:
  - training content payloads,
  - quiz attempt persistence responses.

### K) Impact Analytics

- **Service**: `app/services/impact_analytics_service.py`
- **Purpose**: summarize outcomes across veteran/housing interventions and opportunities.
- **Key functions**:
  - `get_impact_summary`
  - `get_opportunity_map`
  - `get_housing_summary`
- **API endpoints**:
  - `GET /impact/summary`
  - `GET /impact/opportunity-map`
  - `GET /impact/housing-summary`
  - `GET /platform/capabilities`
- **Expected outputs**:
  - rolled-up impact counts/values,
  - state-level opportunity maps,
  - housing stabilization metrics,
  - capability status snapshot.

---

## 8. API Surface Overview

### `/leads`

- `GET /leads/` – baseline lead table retrieval.
- `POST /leads/intelligence/ingest` – structured lead ingest.
- `POST /leads/intelligence/score` – lead scoring by lead ID.
- `POST /leads/intelligence/ingest-csv` – route helper for CSV-style ingest.

### `/foreclosure`

- `POST /foreclosure/create-profile` – create/update foreclosure profile.
- `POST /foreclosure/analyze-property` – analytics + classification + priority response.

### `/essential-worker`

- `POST /essential-worker/profile`
- `POST /essential-worker/discover-benefits`
- `POST /essential-worker/action-plan`

### `/portfolio`

- `POST /portfolio/add-property`
- `GET /portfolio/summary`

### `/membership`

- `POST /membership/create`

### `/impact`

- `GET /impact/summary`
- `GET /impact/opportunity-map`
- `GET /impact/housing-summary`
- `GET /platform/capabilities`

### `/verify`

- `GET /verify/phase9`
- `GET /verify/phase10`
- `GET /verify/policy-engine`
- `GET /verify/essential-worker-module`
- `GET /verify/lead-intelligence`
- `GET /verify/dfw-connectors`
- `GET /verify/skiptrace-integration`

### `/pipeline`

- `POST /pipeline/foreclosure-analysis`

### `/partner` and `/partners`

- `/partner/v1/cases/{case_id}/status`
- `/partner/v1/cases/{case_id}/workflow-readiness`
- `/partner/v1/cases/{case_id}/evidence-verification`
- `/partner/v1/veterans/benefit-discovery-summary`
- `/partner/v1/veterans/integration-ping`
- `/partners/route-case`

### `/admin/ai/mufasa`

- `POST /admin/ai/mufasa/chat` – mixed action/explainer endpoint.
- `POST /admin/ai/mufasa/explain` – explanation-focused endpoint.

---

## 9. Admin Command Center

### Components

- `AdminCommandCenter.tsx`
  - defines capability panels and button configs.
  - renders response console.
  - embeds `MufasaAssistant` panel.
- `AdminActionButton.tsx`
  - reusable button for endpoint + method + payload execution.
- `MufasaAssistant.tsx`
  - chat thread + input + investor mode toggle + investor demo button.
- `apiClient.ts`
  - generic fetch wrapper with response parsing.

### Button execution flow

1. Admin clicks capability button.
2. `AdminActionButton` calls `apiClient.request`.
3. Result is pushed to parent `history` callback.
4. JSON console renders updated action outputs.

### Chat integration

- `MufasaAssistant` posts prompts to `/admin/ai/mufasa/chat` with `investor_mode` flag.
- Responses are rendered in streaming-style text updates.
- Action names from response are shown in-message for operational visibility.

---

## 10. Mufasa AI Interaction Flow

**Lifecycle**

1. **User prompt** in Mufasa UI.
2. **API call** to `POST /admin/ai/mufasa/chat`.
3. **Route authorization** ensures admin role.
4. **Orchestration** in `handle_mufasa_prompt`:
   - classify prompt type,
   - execute actions or produce explanation.
5. **(Action path)** domain services executed directly via orchestration helpers.
6. **Response formatting** into natural-language summary + action/result payloads.
7. **AI command logging** into `AICommandLog`.
8. **Frontend rendering** in message thread and operator console.

> Note: module/broker pathways are used for dynamic module actions; direct Mufasa action routing currently executes mapped service calls inside orchestration rather than invoking module action endpoints.

---

## 11. AI Command Logging

### Model

`app/models/ai_command_logs.py` (`AICommandLog`)

### Logged fields

- `user_id`
- `message` (prompt)
- `ai_response`
- `actions_triggered` (JSON array)
- `results` (JSON payload)
- `created_at`

### Operational value

- **Audit trail**: traces AI-driven operator activity.
- **Debugging**: inspect per-step action and result payloads from failed/complex prompts.
- **Observability**: provides command history for QA, incident review, and demo playback.

---

## 12. Data Model Overview

### ModuleRegistry

Holds versioned module specs and lifecycle state for dynamic capability extension (permissions, required services, allowed actions, policy/activation status).

### VeteranProfile family

- `VeteranProfile`, `BenefitRegistry`, `BenefitProgress`, `BenefitDiscoveryAggregate`
- Together support eligibility matching, benefit valuations, progress tracking, and aggregate reporting.

### Lead Intelligence models

- `LeadSource`, `PropertyLead`, `LeadScore`
- Track source metadata, normalized property leads, and scoring outcomes with case linkage.

### Housing Intelligence models

- `ForeclosureCaseData`, `PartnerOrganization`, `PartnerReferral`, `PropertyAsset`, `MembershipProfile`, `ForeclosureLeadImport`, `TrainingGuideStep`
- Cover foreclosure case data, partner operations, portfolio assets, and training scaffolding.

### Essential Worker models

- `EssentialWorkerProfile`, `EssentialWorkerBenefitMatch`
- Store assistance eligibility context and matched program/value outputs.

### AICommandLog

Persists AI command requests/responses/action traces for Mufasa operations.

---

## 13. Platform Capability Inventory (Master List)

Current platform capabilities include:

1. AI orchestration (advisory, execute, voice, Mufasa action/explainer paths)
2. Natural-language admin AI assistant (Mufasa chat + explain endpoints)
3. Platform knowledge engine for self-description and investor Q&A
4. Dynamic module registry, validation, activation, and runtime loading
5. Bounded domain broker for safe module action dispatch
6. Lead ingestion/scoring/case-conversion workflows
7. Foreclosure profile + intervention analytics + priority scoring
8. Skiptrace contact discovery for property/case owners
9. Essential-worker profile and housing assistance workflows
10. Veteran benefit intelligence (matching/value/plans/documents/progress/reporting)
11. Partner routing and partner API reporting surfaces
12. Portfolio asset intake and equity summaries
13. Membership creation and admin monitoring surfaces
14. Training guides/steps and quiz attempt endpoints
15. Impact analytics and capability-reporting endpoints
16. Verification endpoints for phase/system readiness checks
17. Admin Command Center with grouped capability controls and JSON response console

---

## 14. Investor Demo Walkthrough

### Step 1 — Explain platform

Prompt: **“What does this platform do?”**

Expected behavior:
- Mufasa routes to question path and returns architecture/capability summary.
- In investor mode, response emphasizes business value and impact.

### Step 2 — Show capability breadth

Prompt: **“Show platform capabilities”**

Expected behavior:
- Mufasa explainer summarizes domains/services/modules and operational surfaces.

### Step 3 — Foreclosure intelligence action

Prompt: **“Analyze foreclosure case”**

Expected behavior:
- Action path executes foreclosure profile/priority logic.
- Response includes analytics and classification context.

### Step 4 — Veteran intelligence action

Prompt: **“Match veteran benefits”**

Expected behavior:
- Action path executes veteran eligibility matching and returns benefit context.

### Step 5 — Multi-step macro demo

Prompt: **“Run investor demo”**

Expected behavior:
- Orchestration runs multi-step workflow across lead, skiptrace, housing, and portfolio outputs.
- Chat displays execution sequence and final summarized response.

### Suggested live narration

- “We can run direct actions with deterministic outputs or ask platform-level questions conversationally.”
- “Every AI interaction is logged with action traces for governance and replay.”
- “The module system lets us add governed capabilities without unsafe runtime code execution.”

---

## 15. System Strengths

1. **AI orchestration with dual mode**
   - Executes actions and answers questions about system architecture.

2. **Governed modular expansion**
   - Module lifecycle plus startup loader enables controlled runtime growth.

3. **Bounded execution model**
   - DomainServiceBroker enforces explicit action/service constraints.

4. **Domain-intelligence breadth**
   - End-to-end workflows across lead → analysis → routing → assistance → reporting.

5. **Self-explaining AI layer**
   - PlatformKnowledgeService turns internal docs + module metadata into explainable AI context.

6. **Operational observability**
   - AICommandLog and admin response console provide high transparency.

---

## 16. Future Expansion Possibilities

The current architecture can scale with low rewrite cost because extension points already exist:

1. **Add new domain capabilities via services + routes**
   - New service functions can be integrated into Mufasa action path and/or module broker mapping.

2. **Add new modules via registry activation**
   - New module specs can be validated/activated and loaded at startup into dynamic action routes.

3. **Improve AI reasoning depth safely**
   - Expand prompt-router sophistication (intent classifier, policy gating) while keeping bounded action handlers.

4. **Expand knowledge corpus**
   - Add more docs/runbooks/metrics feeds to PlatformKnowledgeService context.

5. **Add investor/operator personas**
   - Investor mode already exists; additional persona prompts and response templates can be layered without core API redesign.

6. **Strengthen analytics and reporting**
   - Impact, partner, and portfolio summaries can be extended into richer dashboards and cohort-level reporting.

7. **Operational hardening**
   - Add deeper endpoint-level integration tests and execution tracing dashboards without changing architecture shape.

---

## Appendix: Key Files Referenced

- `api/main.py`
- `api/routes/mufasa_ai.py`
- `app/services/ai_orchestration_service.py`
- `app/services/platform_knowledge_service.py`
- `app/services/module_loader_service.py`
- `app/services/module_registry_service.py`
- `app/models/module_registry.py`
- `app/models/ai_command_logs.py`
- `app/models/veteran_intelligence.py`
- `app/models/lead_intelligence.py`
- `app/models/housing_intelligence.py`
- `app/models/essential_worker.py`
- `frontend/src/pages/admin/AdminCommandCenter.tsx`
- `frontend/src/components/AdminActionButton.tsx`
- `frontend/src/components/MufasaAssistant.tsx`
- `frontend/src/services/apiClient.ts`
