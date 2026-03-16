# Platform AI Explainer

## Platform Summary

Universal Pilot is an AI-assisted housing intervention platform that combines foreclosure intelligence, lead scoring, homeowner contact discovery, benefits/program matching, partner routing, and portfolio/impact analytics in one governed operating system.

Key operator interfaces:
- Admin Command Center (capability buttons + response console)
- Mufasa AI assistant (natural-language command + explanation mode)

## Architecture Explanation

### 1) API and service backbone
- FastAPI router composition in `api/main.py` registers domain and admin endpoints.
- Domain logic is implemented in bounded services under `app/services/*`.

### 2) AI orchestration
- `app/services/ai_orchestration_service.py` routes Mufasa prompts to either:
  - executable workflows (lead, foreclosure, skiptrace, housing, veteran, portfolio, diagnostics), or
  - conversational platform explanations using the knowledge engine.

### 3) Platform knowledge engine
- `app/services/platform_knowledge_service.py` summarizes platform docs, module registry entries, and domain service maps.
- Enables Mufasa to answer investor/architecture questions conversationally.

### 4) Governed module runtime
- `module_registry` stores versioned module specs (permissions, required services, actions).
- `ModuleRegistryService` validates module safety and lifecycle.
- `ModuleLoaderService` + `DomainServiceBroker` enforce safe action dispatch and startup loading.

### 5) Auditability
- Mufasa commands are persisted in `AICommandLog` with prompt, response, actions, and results.

## Capability Descriptions

- **Lead intelligence:** ingest leads, score and prioritize, convert to intervention-ready cases.
- **Foreclosure intelligence:** create foreclosure profiles, compute urgency and intervention class.
- **Skiptrace:** locate homeowner/borrower contacts for outreach workflows.
- **Essential worker housing:** profile-based assistance matching and action plan generation.
- **Veteran benefit intelligence:** benefit discovery, valuation, action plans, document automation.
- **Partner routing:** route cases to matching partners and expose partner-facing status/reporting.
- **Portfolio management:** add assets and summarize value/loan/equity state.
- **Impact analytics:** summarize outcomes and opportunity maps for reporting.
- **Training:** serve onboarding and certification-related operational content.

## Demo Walkthrough

1. Open **Admin → Command Center**.
2. Trigger core buttons (lead ingest/score, foreclosure scan, skiptrace, impact summary).
3. Open Mufasa chat and ask:
   - “What does this platform do?”
   - “How does foreclosure intelligence work?”
4. Enable **Investor Mode** in Mufasa Assistant.
5. Run “Run Investor Demo” to execute multi-step orchestration and narrate each output.

## API Entry Points For AI Operations

- `POST /admin/ai/mufasa/chat`: Executes action-oriented prompts or routes explanatory prompts through orchestration.
- `POST /admin/ai/mufasa/explain`: Forces explanation mode for architecture/capability questions.

Execution path for chat-driven actions:

1. Admin UI (`MufasaAssistant`) sends prompt payload.
2. API route (`api/routes/mufasa_ai.py`) enforces admin auth and invokes orchestration.
3. `AIOrchestrationService.handle_mufasa_prompt` determines action vs question.
4. Action path dispatches domain workflows (lead, foreclosure, skiptrace, worker housing, portfolio, etc.).
5. Results and action traces are persisted to `ai_command_logs`.

## Investor Demo Sequence (Current Behavior)

When the prompt includes “run investor demo”, orchestration performs a bundled sequence:

1. Foreclosure lead discovery scan.
2. Lead scoring on discovered opportunities.
3. Case creation from the top lead.
4. Skiptrace/contact lookup for outreach.
5. Essential worker profile + assistance discovery.
6. Action plan generation.
7. Portfolio/equity summary.

This flow demonstrates one-prompt execution of cross-domain interventions with persisted command telemetry.

## Suggested Investor Questions

- What problems does this platform solve in foreclosure prevention?
- How are leads prioritized and converted into actions?
- How does AI remain governed and auditable?
- How does the module system safely extend capabilities?
- What measurable outcomes can we report?
