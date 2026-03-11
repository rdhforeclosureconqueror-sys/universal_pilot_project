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

## Suggested Investor Questions

- What problems does this platform solve in foreclosure prevention?
- How are leads prioritized and converted into actions?
- How does AI remain governed and auditable?
- How does the module system safely extend capabilities?
- What measurable outcomes can we report?
