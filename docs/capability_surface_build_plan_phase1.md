# CAPABILITY SURFACE BUILD PLAN — PHASE 1

## 1. Audience Map

### Public users / applicants
Main surfaces needed:
- Public landing hub with clear persona entry points.
- Guided intake experiences for general housing help.
- Application status confirmation and next-steps page.

### Homeowners in foreclosure
Main surfaces needed:
- Foreclosure help landing page (what help exists, urgency framing, trust/compliance language).
- Multi-step foreclosure intake (property, delinquency stage, timeline, consent, contact).
- Submission confirmation with case handoff expectations.

### Essential workers
Main surfaces needed:
- Essential worker benefits landing/intake page.
- Eligibility-first guided intake (role/employer/location/income/program fit).
- Results summary with routed follow-up path.

### Veterans
Main surfaces needed:
- Veteran housing/benefits landing/intake page.
- Veteran profile and risk/needs capture flow.
- Benefits discovery preview and operator follow-up handoff page.

### Operators / admins
Main surfaces needed:
- Domain workspaces with clear queue, profile, actions, outcomes.
- Lead intelligence workspace for triage and conversion.
- Foreclosure intelligence workspace for case progression.
- Skiptrace workspace for contact-resolution workflows.
- Partner routing workspace for match, route, and status tracking.
- Portfolio workspace for asset/outcome visibility.
- Training center enhancements for role-based completion and readiness.

### Partners
Main surfaces needed:
- Partner-facing referral visibility (initially operator-mediated view).
- Routing status + assignment context.
- Compliance-visible interaction trail.

### Investors / stakeholders
Main surfaces needed:
- Platform capabilities showcase page (human-readable module overview).
- Investor guided story/demo page with narrative checkpoints and outcomes.
- Outcome summary cards (operational + impact + business indicators).

## 2. Navigation Architecture

### Public-facing navigation (top-level)
Main nav should include:
- Home
- Get Help
  - Foreclosure Help
  - Essential Worker Programs
  - Veteran Housing & Benefits
- How It Works
- About / Trust & Compliance
- Sign In

Public landing structure:
- `/` = branded value proposition + three guided entry cards.
- Persona landing pages = decision support + CTA into intake.
- Intake pages should be linear, guided, and low-distraction (minimal nav during completion).

### Operator/admin navigation
Admin nav should include:
- Command Center (existing, unchanged as primary launch point)
- Workspaces
  - Lead Intelligence
  - Foreclosure Intelligence
  - Skiptrace
  - Partner Routing
  - Portfolio
- Training Center
- Existing Operations (Cases, Referrals, Properties, Data Ops) as stable legacy anchors during migration.

Deep-linked workspaces:
- Each workspace should support deep links from command center actions/alerts.
- URL should encode workspace context (e.g., queue type, record id, stage).
- Command-center actions should open the new workspace panels, not raw JSON output.

### Demo/showcase navigation
Demo nav should include:
- Platform Capabilities
- Investor Story Demo

Safeguard:
- Demo routes must be clearly segmented from live operator routes and use curated presentation payloads.

## 3. Route/Page Blueprint

| Route (proposed) | Page | Audience | Purpose | Surface Type |
|---|---|---|---|---|
| `/help/foreclosure` | Foreclosure Intake | Homeowners in foreclosure | Capture urgent housing risk, consent, and intervention profile | Public |
| `/help/essential-worker` | Essential Worker Intake | Essential workers | Capture profile for program eligibility and housing support routing | Public |
| `/help/veteran` | Veteran Intake | Veterans | Capture service + household context for benefits/housing triage | Public |
| `/admin/workspaces/leads` | Lead Intelligence Workspace | Operators/admins | Intake-to-triage queue, dedupe, scoring, conversion to case | Operator |
| `/admin/workspaces/foreclosure` | Foreclosure Workspace | Operators/admins | Foreclosure case lifecycle, risk stage, intervention decisions | Operator |
| `/admin/workspaces/skiptrace` | Skiptrace Workspace | Operators/admins | Contact discovery, confidence review, retry/escalation decisions | Operator |
| `/admin/workspaces/partner-routing` | Partner Routing Workspace | Operators/admins/partner ops | Match candidates to partners, capture route rationale, track outcomes | Operator |
| `/admin/workspaces/portfolio` | Portfolio Workspace | Operators/admins | Portfolio-level asset/outcome visibility tied to active interventions | Operator |
| `/admin/training` | Training Center | Operators/admins | Learning modules, certification, role readiness tracking | Operator |
| `/platform/capabilities` | Platform Capabilities Showcase | Investors/stakeholders/partners | Explain modules, audience fit, and outcome proof points | Demo |
| `/demo/investor-story` | Investor Story/Demo | Investors/stakeholders | Guided narrative from intake through measurable impact/outcomes | Demo |

## 4. Shared Surface Model

Standardize these reusable patterns across all new surfaces:
- **Landing/Intake Page Shell**: headline, trust/compliance block, stepper, CTA.
- **Operator Workspace Shell**: queue pane + detail pane + action pane layout.
- **Results/Analysis Panel**: structured insights, confidence, source/time metadata.
- **Action Sidebar**: role-gated actions with required rationale and confirmation.
- **Progress/Status Card**: stage, SLA timers, blockers, ownership.
- **Compliance/Consent Panel**: consent state, policy checks, disclosure acknowledgments.
- **Audit Trail Panel**: immutable action/event log with actor, timestamp, payload summary.

Cross-cutting conventions:
- Shared empty/loading/error states.
- Shared policy failure UI language.
- Shared “next best action” pattern for both public and operator contexts.

## 5. First Build Slice Recommendation

### Recommended smallest high-value slice
Build **one end-to-end persona path plus one operator path**:
1. Public **Foreclosure Intake** (`/help/foreclosure`)
2. Operator **Foreclosure Workspace (MVP)** (`/admin/workspaces/foreclosure`)
3. Operator **Lead Intelligence queue linkage** (minimal deep-link handoff from command center or intake-created lead into foreclosure workflow)

### Why this should go first
- Foreclosure path has clear urgency and direct user impact.
- It closes the biggest “backend-capable but human-unsurfaced” gap with minimal domain sprawl.
- It validates key platform completeness criteria in one slice: find → understand → enter → use → see results.
- It exercises critical shared components (intake shell, workspace shell, compliance, audit trail) that can be reused for essential worker and veteran paths next.
- It minimizes risk by extending existing command center/admin operations rather than replacing them.

## 6. Expected Files/Areas (First Slice)

Likely modules touched for planning-aligned implementation:

Frontend:
- `frontend/src/pages/` (new public foreclosure intake page, route wiring)
- `frontend/src/pages/admin/` (new foreclosure workspace page)
- `frontend/src/components/` (shared intake/workspace/compliance/audit panels)
- `frontend/src/services/apiClient.ts` (typed calls for intake submit + workspace data)
- `frontend/main.js` or router configuration entry points (route registration/deep-link handling)
- `frontend/styles.css` and/or `frontend/crm.css` (shared shell/layout primitives)

Backend/API:
- `api/main.py` (route registration if required)
- Foreclosure/public intake routes (existing apply/intelligence endpoints, adding UI-oriented payload shapes only where needed)
- Service layer response shapers for queue-friendly/workspace-friendly data
- Audit/policy integration points to ensure all new actions remain logged and authorized

## 7. Safety Notes

The following must remain stable during build execution:
- **Auth/policy gates**: no relaxation of role checks, consent requirements, or policy authorizer behavior.
- **Audit logging**: every new intake/workspace action must preserve append-only traceability.
- **Existing admin workflows**: command center and current operational pages remain functional during incremental rollout.
- **Current command center actions**: no breaking contract changes; use deep links/adapters instead of hard replacement.
- **Onboarding/tour system**: preserve current onboarding entry points and behavior while adding new workspace routes.
- **Action payload reliability layer**: maintain existing action execution semantics, retries, and response contracts; avoid refactors in Phase 1.
