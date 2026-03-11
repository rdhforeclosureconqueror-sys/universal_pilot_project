# Platform Operational Report

This report documents the current platform capabilities and operating model based on the repository as implemented.

---

## 1) Platform Overview

### Architecture layers

1. **AI orchestration layer**
   - Core orchestration behavior lives in `app/services/ai_orchestration_service.py`.
   - It supports advisory/execute/voice flows and an admin-oriented Mufasa natural-language execution flow (`handle_mufasa_prompt`).

2. **Module registry + module loader**
   - Registry model and lifecycle validation exist in `app/models/module_registry.py` and `app/services/module_registry_service.py`.
   - Runtime loader and dynamic route registration are implemented in `app/services/module_loader_service.py`.
   - Active modules are loaded on startup via `load_modules_on_startup(app)` in `api/main.py`.

3. **Domain Service Broker**
   - `DomainServiceBroker` in `module_loader_service.py` safely maps allowed module actions to bounded service handlers.
   - It enforces allowed actions and required service constraints before dispatch.

4. **API routing layer**
   - Main FastAPI wiring is in `api/main.py`, including route registration across domain APIs (`api/routes/*`) and admin/member APIs (`app/api/routes/*`).
   - Verification and diagnostics endpoints are exposed via `/verify/*` and admin system endpoints.

5. **Frontend admin interface**
   - Admin UI source is in `frontend/src/pages/admin/AdminCommandCenter.tsx` plus reusable components:
     - `frontend/src/components/AdminActionButton.tsx`
     - `frontend/src/components/MufasaAssistant.tsx`
     - `frontend/src/services/apiClient.ts`
   - The command center combines button-driven actions and AI chat operations.

6. **AI command interface (Mufasa)**
   - API endpoint: `POST /admin/ai/mufasa/chat` (`api/routes/mufasa_ai.py`).
   - Prompt execution and action fan-out are handled by `handle_mufasa_prompt`.
   - Command history is stored in `AICommandLog` (`app/models/ai_command_logs.py`).

### Layer interaction flow

- **Admin/operator** triggers capability from button panel or Mufasa chat.
- **Frontend API client** (`apiClient`) sends HTTP requests to backend endpoints.
- **Routes** delegate to domain services (lead, foreclosure, veteran, housing, portfolio, etc.).
- **Mufasa orchestration** can invoke multiple domain services in one prompt and aggregate results.
- **Audit/command logs** persist operational traces (including `AICommandLog` for Mufasa commands).
- **Module loader path** allows policy-validated module actions to execute through `DomainServiceBroker` only.

---

## 2) Full Capability Inventory

> Format: **Capability** → Service / API / File / What it does

### System Operations

| Capability | Service Name | API Endpoint(s) | Service File | Description |
|---|---|---|---|---|
| Phase 9 verification | verify route orchestration | `GET /verify/phase9` | `api/routes/verify.py` | End-to-end check: creates foreclosure profile, runs analytics, computes priority, returns operational status. |
| Phase 10 verification | verify route orchestration | `GET /verify/phase10` | `api/routes/verify.py` | Extended pipeline check including partner routing and recommendation generation flags. |
| Policy engine diagnostics | verify route | `GET /verify/policy-engine` | `api/routes/verify.py` | Returns policy-engine health diagnostics (meta-field fallback behavior). |
| Daily risk evaluation | escalation service | `POST /admin/system/run-daily-risk-evaluation` | `app/api/routes/system_admin.py` + `app/services/escalation_service.py` | Executes risk evaluation workflow through admin endpoint. |
| Phase verification runner | verification engine | `POST /admin/system/verify/{phase_key}` | `app/api/routes/system_admin.py` | Runs named phase verification using system admin API. |
| Module startup loading | module loader | app startup hook | `app/services/module_loader_service.py` + `api/main.py` | Loads active modules and dynamic module routes at API startup. |
| Module lifecycle validation | module registry service | (service lifecycle operations) | `app/services/module_registry_service.py` | Validates module schema/policy and activates/deprecates versions safely. |

### Lead Intelligence

| Capability | Service Name | API Endpoint(s) | Service File | Description |
|---|---|---|---|---|
| Lead ingestion | `ingest_leads` | `POST /leads/intelligence/ingest` | `app/services/lead_intelligence_service.py` + `api/routes/lead_intelligence.py` | Ingests structured leads by source and de-duplicates by source/address. |
| CSV ingestion seed path | `ingest_leads` via route helper | `POST /leads/intelligence/ingest-csv` | `api/routes/lead_intelligence.py` | Route-level ingestion helper for CSV-style lead intake. |
| Lead scoring | `score_property_lead` | `POST /leads/intelligence/score` | `app/services/lead_intelligence_service.py` | Scores foreclosure leads and may auto-create case when threshold is reached. |
| Case creation from lead | `create_case_from_lead` | invoked by scoring/Mufasa | `app/services/lead_intelligence_service.py` | Converts lead into case with policy-backed metadata. |
| Weekly foreclosure scan connectors | `weekly_foreclosure_scan` | `GET /verify/dfw-connectors` | `app/services/lead_intelligence_service.py` + `api/routes/verify.py` | Runs Dallas/Tarrant/Collin connector ingestion aggregation. |

### Foreclosure Intelligence

| Capability | Service Name | API Endpoint(s) | Service File | Description |
|---|---|---|---|---|
| Foreclosure profile creation | `create_foreclosure_profile` | `POST /foreclosure/create-profile` | `app/services/foreclosure_intelligence_service.py` + `api/routes/foreclosure.py` | Creates or reuses foreclosure profile and case context. |
| Foreclosure analysis bundle | route+property analysis | `POST /foreclosure/analyze-property` | `api/routes/foreclosure.py` + `app/services/property_analysis_service.py` | Computes equity/LTV/rescue/acquisition scores and intervention class. |
| Case priority scoring | `calculate_case_priority` | `POST /foreclosure/analyze-property`, pipeline/verify flows | `app/services/foreclosure_intelligence_service.py` | Produces urgency/priority tiers for intervention sequencing. |
| Pipeline orchestration | foreclosure pipeline route | `POST /pipeline/foreclosure-analysis` | `api/routes/pipeline.py` | End-to-end: create profile, analyze, prioritize, route to partner, recommend action. |

### Skiptrace

| Capability | Service Name | API Endpoint(s) | Service File | Description |
|---|---|---|---|---|
| Property owner discovery | `skiptrace_property_owner` | `GET /verify/skiptrace-integration` (verification path), Mufasa execution | `app/services/skiptrace_service.py` | Resolves owner contact details via adapter abstraction (batchdata/propstream/PDL). |
| Case owner discovery | `skiptrace_case_owner` | Mufasa execution | `app/services/skiptrace_service.py` | Returns case-linked contact lookup payload. |

### Essential Worker Housing

| Capability | Service Name | API Endpoint(s) | Service File | Description |
|---|---|---|---|---|
| Worker profile create/update | `upsert_worker_profile` | `POST /essential-worker/profile` | `app/services/essential_worker_housing_service.py` + `api/routes/essential_worker.py` | Creates/updates essential-worker profile for benefit workflows. |
| Program discovery | `discover_housing_programs` | `POST /essential-worker/discover-benefits` | `app/services/essential_worker_housing_service.py` | Matches profile to eligible housing assistance programs. |
| Assistance value calculation | `calculate_assistance_value` | service level + surfaced in housing summary views | `app/services/essential_worker_housing_service.py` | Aggregates matched benefit dollar value for profile. |
| Homebuyer action planning | `generate_homebuyer_action_plan` | `POST /essential-worker/action-plan` | `app/services/essential_worker_housing_service.py` | Produces actionable steps and required documents for housing pathway. |

### Veteran Intelligence

| Capability | Service Name | API Endpoint(s) | Service File | Description |
|---|---|---|---|---|
| Veteran profile upsert | `upsert_veteran_profile` | module/Mufasa/service paths | `app/services/veteran_intelligence_service.py` | Stores veteran profile and triggers audit trail. |
| Benefit matching | `match_benefits` | Mufasa + service flows | `app/services/veteran_intelligence_service.py` | Matches case/profile against benefit registry rules. |
| Benefit value calculation | `calculate_benefit_value` | module/service paths | `app/services/veteran_intelligence_service.py` | Computes monthly/annual/lifetime value breakdowns. |
| Veteran action plan | `generate_action_plan` | Mufasa + module/service paths | `app/services/veteran_intelligence_service.py` | Generates benefits-driven intervention steps. |
| Veteran document generation | `generate_documents` | Mufasa + module/service paths | `app/services/veteran_intelligence_service.py` | Generates veteran-specific document package records. |
| Progress tracking | `update_benefit_progress` | service/module | `app/services/veteran_intelligence_service.py` | Tracks benefit progression status by case and benefit. |
| Partner reporting | `partner_aggregate_report` | `GET /partners/veterans/benefit-discovery-summary` | `app/services/veteran_intelligence_service.py` + `api/routes/partner_api.py` | Returns anonymized partner-facing veteran intelligence summary data. |

### Property Intelligence

| Capability | Service Name | API Endpoint(s) | Service File | Description |
|---|---|---|---|---|
| Equity calculation | `calculate_equity` | used in `/foreclosure/analyze-property`, `/pipeline/foreclosure-analysis`, `/verify/phase9`, `/verify/phase10` | `app/services/property_analysis_service.py` | Calculates estimated equity from value and debt. |
| LTV calculation | `calculate_ltv` | same analysis endpoints | `app/services/property_analysis_service.py` | Computes loan-to-value ratio. |
| Rescue score | `calculate_rescue_score` | same analysis endpoints | `app/services/property_analysis_service.py` | Quantifies rescue feasibility based on arrears/income/stage. |
| Acquisition score | `calculate_acquisition_score` | same analysis endpoints | `app/services/property_analysis_service.py` | Scores acquisition attractiveness by equity/LTV/stage. |
| Intervention classification | `classify_intervention` | same analysis endpoints | `app/services/property_analysis_service.py` | Classifies legal defense, mod, nonprofit support, or acquisition paths. |

### Partner Routing

| Capability | Service Name | API Endpoint(s) | Service File | Description |
|---|---|---|---|---|
| Case-to-partner routing | `route_case_to_partner` | `POST /partners/route-case`, pipeline and verify usage | `app/services/partner_routing_service.py` + `api/routes/partners_housing.py` | Selects/creates referral to partner based on category/state/case. |
| Partner status/readiness reporting | partner API route set | `GET /partners/cases/{case_id}/status`, `GET /partners/cases/{case_id}/workflow-readiness`, `GET /partners/cases/{case_id}/evidence-verification` | `api/routes/partner_api.py` | Exposes partner-consumable case lifecycle and evidence checks. |

### Portfolio Management

| Capability | Service Name | API Endpoint(s) | Service File | Description |
|---|---|---|---|---|
| Property asset creation | `add_property_to_portfolio` | `POST /portfolio/add-property` | `app/services/property_portfolio_service.py` + `api/routes/portfolio.py` | Adds property assets and writes audit trail. |
| Portfolio equity summary | `calculate_portfolio_equity` | `GET /portfolio/summary` | `app/services/property_portfolio_service.py` | Aggregates asset counts, values, loans, and equity totals. |

### Membership

| Capability | Service Name | API Endpoint(s) | Service File | Description |
|---|---|---|---|---|
| Membership creation | `create_membership` | `POST /membership/create` | `app/services/membership_service.py` + `api/routes/membership.py` | Creates member profile/membership artifacts for assistance programs. |
| Membership admin dashboards | admin dashboard service | `GET /admin/memberships`, `/admin/memberships/below-stability`, `/admin/memberships/missed-installments`, `/admin/memberships/{membership_id}` | `app/api/routes/admin_dashboard.py` | Provides admin operational views and risk/quality filtering. |

### Training

| Capability | Service Name | API Endpoint(s) | Service File | Description |
|---|---|---|---|---|
| Training lesson content | training route + service | `GET /training/system-overview`, `GET /training/workflow-guide`, `GET /training/step/{step_id}` | `api/routes/training.py` + `app/services/system_training_service.py` | Returns system training guides and step-level lessons. |
| Lesson completion/quiz | quiz attempt workflow | `POST /training/quiz_attempt` | `api/routes/training.py` | Records quiz attempts and contributes to certification progress tracking. |

### Impact Analytics

| Capability | Service Name | API Endpoint(s) | Service File | Description |
|---|---|---|---|---|
| Impact summary | `get_impact_summary` | `GET /impact/summary` | `app/services/impact_analytics_service.py` + `api/routes/impact_api.py` | Aggregates served veterans, claimed benefits, unlocked value, foreclosures prevented. |
| Opportunity map | `get_opportunity_map` | `GET /impact/opportunity-map` | `app/services/impact_analytics_service.py` | State-level opportunity and value concentration reporting. |
| Housing impact summary | `get_housing_summary` | `GET /impact/housing-summary` | `app/services/impact_analytics_service.py` | Housing-focused impact metrics (homes saved, equity preserved, etc.). |
| Capability report API | `get_platform_capabilities` | `GET /platform/capabilities` | `app/services/platform_capability_service.py` + `api/routes/impact_api.py` | Returns top-level platform capabilities/status list. |

---

## 3) Admin Command Center

### UI code locations

- Main page: `frontend/src/pages/admin/AdminCommandCenter.tsx`
- Reusable action button: `frontend/src/components/AdminActionButton.tsx`
- HTTP helper: `frontend/src/services/apiClient.ts`
- AI chat panel: `frontend/src/components/MufasaAssistant.tsx`

### How button actions work

- Each capability action is defined as `{ label, endpoint, method, payload }` in the command center page.
- `AdminActionButton` receives those props and executes the request through `apiClient.request(endpoint, { method, payload })`.
- The button reports success/error metadata through an `onResult` callback to the parent page.

### Response console behavior

- `AdminCommandCenter` stores action results in local `history` state.
- The right-side console panel renders the latest results as formatted JSON (`JSON.stringify(history, null, 2)`).
- This gives operators immediate visibility of backend output/errors for each click.

### Capability panel structure

- Panels are grouped by domain sections (System, Lead, Foreclosure, Skiptrace, Essential Worker, Veteran, Partner, Portfolio, Training, AI).
- Each panel renders a list of `AdminActionButton` controls.
- The Mufasa chat panel is included at the top as a natural-language command surface.

---

## 4) Mufasa AI Assistant

### Endpoint and schemas

- **Endpoint:** `POST /admin/ai/mufasa/chat`
- **Request schema (`MufasaChatRequest`):**
  ```json
  {
    "prompt": "string"
  }
  ```
- **Response schema (`MufasaChatResponse`):**
  ```json
  {
    "response": "string",
    "actions_executed": ["..."],
    "results": {}
  }
  ```

### Prompt parsing and execution model

- Route-level admin gate verifies caller role is `admin`.
- Route delegates to `handle_mufasa_prompt(prompt, user_id, db)`.
- Orchestration flow:
  1. Normalize prompt text.
  2. Use parser context (`parse_command`) and keyword-based intent routing.
  3. Execute one or more domain-service actions (lead scan/score/case creation, foreclosure, skiptrace, housing programs, veteran operations, portfolio, diagnostics).
  4. Aggregate `actions_executed` and `results`.
  5. Return a human-readable response string.

### Logging behavior

- Every Mufasa command is persisted to `AICommandLog` with:
  - `user_id`
  - `message` (prompt)
  - `ai_response`
  - `actions_triggered`
  - `results`
  - `created_at`

### Example prompts currently supported

- `Find foreclosure leads in Dallas`
- `Scan foreclosure filings`
- `Ingest leads`
- `Score leads`
- `Create case from lead`
- `Run skiptrace for homeowner`
- `Discover housing assistance programs`
- `Generate homeowner rescue action plan`
- `Discover veteran benefits`
- `Generate veteran action plan`
- `Generate veteran documents`
- `Show portfolio summary`
- `Verify platform`
- `Run daily risk evaluation` (recognized by parser in AI command parser context)

---

## 5) Investor Demo Instructions

### 1. Open Admin Command Center

1. Launch the platform frontend.
2. Navigate to **Admin → Command Center**.
3. Confirm you can see:
   - capability panels,
   - right-side response console,
   - **Mufasa Assistant** chat panel.

### 2. Run capability buttons

1. In **Lead Intelligence**, click **Ingest Leads** then **Score Leads**.
2. In **Foreclosure Intelligence**, click **Run Foreclosure Scan**.
3. In **Skiptrace**, run **Skiptrace Property Owner**.
4. Watch right-side response console for structured output payloads.

### 3. Use Mufasa AI assistant

1. In Mufasa input, enter: `Find foreclosure leads in Dallas`.
2. Send additional prompts like:
   - `Score leads`
   - `Create case from lead`
   - `Run skiptrace for homeowner`
   - `Discover housing assistance programs`
3. Observe streamed AI response text and action execution summaries in-thread.

### 4. Run investor demo scenario

1. Click **Run Investor Demo** in Mufasa Assistant.
2. The UI executes sequential prompts:
   - find foreclosure leads,
   - score leads,
   - create case,
   - run skiptrace,
   - assess rescue eligibility,
   - discover programs,
   - generate plan,
   - show portfolio impact.
3. Narrate response console + chat actions as proof of orchestration breadth.

### What investors should see

- Multi-domain automation from one control surface.
- Structured API outputs tied to real service capabilities.
- Explainable action logs and deterministic operational pathways.
- Combined button-driven and natural-language operation modes.

---

## 6) Example Investor Demo Script

| Operator Action | System Action | Expected Output |
|---|---|---|
| “Find foreclosure leads in Dallas.” | Mufasa runs foreclosure/lead scan routine. | Lead ingestion/scan result and action list in chat response. |
| “Score leads.” | Scores latest lead via lead intelligence service. | Score payload (grade, score, optional created case). |
| “Create case from highest scoring lead.” | Converts lead into case workflow artifact. | Case ID in Mufasa results. |
| “Run skiptrace on top case.” | Executes property/case owner contact lookup. | Contact details (phones/emails/owner name). |
| “Generate homeowner rescue plan.” | Runs assistance discovery + plan generation path. | Action plan steps and matched program context. |
| “Route case to partner.” | Executes partner routing service by category/state logic. | Referral payload with partner route metadata. |
| “Show portfolio summary.” | Computes current portfolio aggregates. | Total assets, portfolio value/loans/equity summary. |

---

## 7) Platform Verification Checklist

### Verification endpoints

- `GET /verify/phase9`
- `GET /verify/phase10`
- `GET /verify/policy-engine`
- `GET /verify/essential-worker-module`
- `GET /verify/lead-intelligence`
- `GET /verify/dfw-connectors`
- `GET /verify/skiptrace-integration`
- `POST /admin/ai/phase7/verify`

### How to confirm operational status

1. Execute each endpoint with authenticated admin credentials.
2. Confirm HTTP success and expected semantic fields:
   - `phase` / `status` / `system_status` / `pipeline_status`
   - booleans such as `case_created`, `priority_calculated`, `partner_routed`
   - diagnostics objects where applicable.
3. Verify downstream behavior:
   - lead ingestion counts on connectors,
   - skiptrace returns contact presence,
   - policy engine returns diagnostics payload,
   - phase verify routes report operational readiness.

---

## 8) System Readiness Summary (Investor-Facing)

The platform is an integrated **AI housing intelligence command center** that combines domain automation, governed execution, and operational transparency in one environment. It can ingest and score distressed-property leads, prioritize foreclosure interventions, discover assistance options, route cases to partners, track veteran/benefit outcomes, and report impact metrics through APIs and admin controls.

What makes it unique is the combination of:

- **Natural-language orchestration** (Mufasa Assistant),
- **Policy-aware modular runtime loading** (module registry + brokered action dispatch), and
- **Cross-domain intervention intelligence** (lead, foreclosure, skiptrace, benefits, portfolio, and impact analytics).

For housing intervention stakeholders, this creates a high-leverage operating model: faster case triage, more consistent rescue-path generation, and measurable program impact with auditable execution trails.

