# CAPABILITY SURFACE AUDIT REPORT

## 1. Domain Inventory

Major capability domains found in repository truth:

Required domains:
- lead intelligence
- foreclosure intelligence
- skiptrace
- essential worker housing
- veteran intelligence
- partner routing
- portfolio
- training
- AI command center
- platform capabilities / capabilities showcase
- investor demo

Additional meaningful domains discovered:
- public application/intake pipeline (`POST /apply`)
- case/workflow operations (case management + foreclosure kanban/analytics)
- referrals + consent governance
- documents/evidence operations
- impact analytics/reporting
- membership/payments + system verification
- BotOps/data operations

## 2. Surface Coverage Matrix

Legend: **present** = full human-usable surface exists; **partial** = some UI exists but still heavily test/button/JSON driven; **missing** = no meaningful surface; **backend-only** = API/service/verify flow with no real surface.

| Domain | Public/User Surface | Operator/Admin Surface | Demo/Presentation Surface | Current repo-truth assessment |
|---|---|---|---|---|
| Lead intelligence | missing | partial | partial | Exists via APIs + admin action cards; operator data table visibility exists, but no dedicated lead workflow UI (ingest/triage/score queue). |
| Foreclosure intelligence | missing | partial | partial | Create/analyze are surfaced primarily as admin action triggers and API calls; no full foreclosure case workspace flow. |
| Skiptrace | missing | partial | missing | Exposed mostly through verification endpoint and command-center buttons; no dedicated skiptrace screen/results workflow. |
| Essential worker housing | missing | partial | missing | APIs exist for profile/benefit/action plan; current surface is command-center button execution, not a guided intake+eligibility UI. |
| Veteran intelligence | missing | partial | partial | Capability exists and is reachable through Mufasa/partner APIs; no dedicated veteran intake/casework workspace page. |
| Partner routing | missing | partial | missing | Referral queue page exists, but true partner routing flow is still primarily API/button-driven and UUID-input based. |
| Portfolio | missing | partial | partial | Property management UI exists, but portfolio add/summary are still mostly API/admin-action driven and not operator-friendly end-to-end. |
| Training | missing | present | partial | Real operator training quiz/certification page exists; public-facing training entry and polished demo narrative are still absent. |
| AI command center | missing | present | partial | Strong admin surface exists with Mufasa assistant and action sections; investor storytelling still chat/output based. |
| Platform capabilities showcase | missing | partial | partial | “Show capabilities” and `/platform/capabilities` exist, but mostly JSON/report output rather than a polished showcase page. |
| Investor demo | missing | partial | partial | “Run Investor Demo” exists in assistant, but currently a sequence of prompts/output rather than guided visual case-story journey. |

## 3. Critical Gaps

Biggest product-surface gaps where capability exists but real workflow/page is weak:

1. **Public intake gap across core personas**
   - There is a public apply API, but no dedicated public pages for homeowner foreclosure help, essential worker benefits, or veteran benefits entry.
2. **Domain workspaces missing for advanced capabilities**
   - Skiptrace, essential worker housing, and veteran intelligence are mostly command-center actions and API outputs.
3. **Presentation surface gap**
   - Platform capabilities and investor demo are still output-first (chat/JSON-like), not narrative-first product experiences.
4. **Operator flow cohesion gap**
   - Existing operator pages (cases/properties/referrals/training/data) are broad but not yet stitched into domain-specific guided workflows (lead -> foreclosure -> skiptrace -> routing -> portfolio outcomes).

## 4. Recommended Surface Architecture

### A) Public landing/intake pages
Build explicit public pathways (separate routes + branded pages):
- **Homeowner Foreclosure Help Intake** (problem, eligibility snapshot, consent, submit).
- **Essential Worker Housing Intake** (profession/employer/income/location, program discovery preview).
- **Veteran Benefits & Housing Intake** (service profile, risk, benefits discovery starter).
- **Shared intake infrastructure** with guided form steps + progress + confirmation + case/application creation.

### B) Operator workspaces
Build domain-specific internal workspaces instead of relying on action buttons:
- **Lead Intelligence Workspace**: ingestion batches, dedupe review, score queue, conversion to case.
- **Foreclosure Intelligence Workspace**: create/update profile, timeline stage, analyze property, priority decisions.
- **Skiptrace Workspace**: run lookup, confidence/results panel, retry/provider selection, audit trail.
- **Essential Worker Workspace**: profile management, eligibility/program matching, action plan/doc packet.
- **Veteran Intelligence Workspace**: profile, benefits matching, action-plan generation, documents and progress.
- **Partner Routing Workspace**: matching recommendations, routing reason capture, status tracking.
- **Portfolio Workspace**: add/update assets, scenario impact, summary dashboards tied to cases.
- **Training Workspace (enhance existing)**: guided lessons, completion tracking, manager review.

### C) Demo/presentation experiences
- **Platform Capabilities Showcase Page**
  - Human-readable module cards, “what it does”, “who uses it”, “proof of outcome”.
- **Investor Story Flow Page**
  - Guided narrative: lead intake -> foreclosure analysis -> skiptrace -> intervention routing -> portfolio/impact outcomes.
  - Visual checkpoints, persona framing, and business impact metrics.
  - Avoid raw JSON-first interaction.

## 5. Build Priority Order

Safest/highest-value order:

1. **Public intake surfaces first** (highest UX gap and external entry value).
2. **Operator workspaces for core path**: lead -> foreclosure -> skiptrace -> routing.
3. **Operator workspaces for benefit programs**: essential worker + veteran.
4. **Portfolio and training workspace hardening** (build continuity and outcome visibility).
5. **Platform showcase + investor story demo** (presentation-ready once workflows are truly human-usable).
6. **Cross-surface polish**: shared design system blocks, consistent audit/compliance indicators, role-aware nav.

## 6. Expected Files / Areas

Likely touch points for future implementation (planning-level):

Frontend:
- `frontend/index.html` (new route sections/nav, public & operator experiences)
- `frontend/main.js` (routing/page state, domain workflow controllers)
- `frontend/src/pages/admin/AdminCommandCenter.tsx` (reduce test-button dependence; transition to deep links/workspaces)
- `frontend/src/components/MufasaAssistant.tsx` (investor flow integration into guided demo surface)
- `frontend/styles.css`, `frontend/crm.css` (new UI layouts/components)

Backend/API:
- `api/main.py` (new page serving paths and router registration as needed)
- `app/api/routes/public_apply.py` (expand to persona-specific intake APIs)
- `api/routes/lead_intelligence.py`, `api/routes/foreclosure.py`, `api/routes/essential_worker.py`, `api/routes/portfolio.py`, `api/routes/training.py`, `api/routes/partners_housing.py`, `api/routes/partner_api.py`, `api/routes/impact_api.py` (workflow-oriented endpoints for UI surfaces)
- Service layer modules in `app/services/*` (orchestrated workflow responses shaped for UI consumption)

## 7. Risk Notes

Do not break/refactor aggressively while surfacing product pages:

- **Policy/authorization gates** must remain intact (`PolicyAuthorizer`, role checks, consent requirements).
- **Audit logging** pathways must stay append-only and complete for actions triggered by new UIs.
- **Verification/system-check endpoints** should remain stable for regression confidence, but should not be mistaken for product surfaces.
- **Existing operator pages** (cases/properties/referrals/training) should be incrementally enhanced, not replaced abruptly.
- **API contracts used by current command center** should be preserved or versioned to avoid breaking admin operations during transition.
- **Investor demo implementation** should use curated, deterministic presentation payloads; avoid exposing internal-only raw diagnostic output as final demo UX.
