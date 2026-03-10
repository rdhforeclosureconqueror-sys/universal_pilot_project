# Universal Pilot Platform Capability Report (Current State)

## 1) Executive Overview
Universal Pilot is a policy-controlled service delivery platform that combines case management, AI orchestration, dynamic module activation, veteran-focused benefit intelligence, and impact reporting.

It solves three common operational problems:
- fragmented program delivery across disconnected tools,
- inconsistent policy/compliance enforcement,
- weak impact visibility for funders and partners.

It is designed for:
- nonprofit operators and housing organizations,
- state and local government program teams,
- enterprise/financial partners,
- investors and grant/funding stakeholders.

Why it is valuable:
- accelerates service delivery with AI-assisted workflows,
- keeps execution policy-gated and auditable,
- supports extensibility through module registry + runtime module loading,
- provides measurable impact metrics and partner reporting.

## 2) Core Platform Architecture
### Application surface and API composition
The FastAPI application composes a broad set of routers (core operations, partner APIs, impact APIs, admin/member routes, webhooks) and boots dynamic module loading during startup.

### AI orchestration layer
The orchestration service parses intent, builds advisory responses, and routes executable intents through a controlled gateway rather than unrestricted direct execution.

### Dynamic module system
The platform includes a registry for module specs and a runtime loader that registers module routes from active registry entries.

### Domain service broker
Dynamic module actions are mediated by a broker that maps actions to explicit service handlers and validates required service declarations.

### Policy authorization layer
PolicyAuthorizer enforces role-session and policy-permission checks and audits allow/deny decisions.

### Case/workflow + document automation
Case and document operations are policy-gated, and veteran document generation writes standardized artifacts into the document subsystem.

### Impact analytics and partner reporting
Impact APIs provide summary and opportunity-map views; partner routes include veteran aggregate reporting.

### Capability registry
A capability endpoint publishes current platform capabilities for partners and licensing clients.

## 3) Dynamic Module System
### ModuleRegistry
`ModuleRegistry` stores module name/type/version plus permissions, required services, data schema, allowed actions, status, and activation metadata.

### Module lifecycle and governance
`ModuleRegistryService` supports create -> validate -> policy-check -> activate flows, rejects invalid specs, denies wildcard actions/permissions in default policy hook, versions active modules, and writes lifecycle audit events.

### Runtime loading and endpoint generation
`ModuleLoaderService`:
- queries active modules,
- validates specs at load time,
- registers runtime route `/modules/{module_name}/actions/{action_name}`,
- enforces `PolicyAuthorizer` before action execution,
- dispatches only through `DomainServiceBroker` mappings,
- logs module load and invocation events.

### Expansion without full redeploy
Because active module specs are read from registry at startup and mapped into runtime routers, capabilities can be extended via governed module lifecycle and activation workflows.

## 4) Veteran Intelligence Platform
Implemented through `veteran_intelligence_service` + veteran data models.

### Capabilities
- veteran profile upsert per case,
- deterministic categorization,
- registry-seeded benefit programs,
- rule-based eligibility matching,
- benefit progress state tracking,
- structured action plan generation,
- advisory responses for benefit/refi/foreclosure questions,
- partner aggregate reporting,
- automated veteran document artifact generation.

### Benefit Value Engine
`calculate_benefit_value(case_id)`:
- retrieves matched benefits,
- calculates monthly total,
- calculates annual total,
- calculates lifetime total (annual x 30 years),
- returns per-benefit breakdown (monthly/annual/lifetime).

Dynamic module action exposed: `calculate_veteran_benefit_value` via `DomainServiceBroker`.

## 5) Impact Analytics System
`impact_analytics_service` provides:
- `get_impact_summary(db)`
- `get_opportunity_map(db)`

Impact API routes:
- `GET /impact/summary`
- `GET /impact/opportunity-map`

Tracked metrics include:
- veterans served,
- benefits discovered,
- benefits claimed,
- benefit value unlocked,
- foreclosures prevented.

Operational utility:
- nonprofits: program throughput and outcomes,
- agencies: state-by-state needs/opportunity targeting,
- partner orgs: referral/integration impact visibility,
- funders: evidence for ROI and grant outcomes.

## 6) Platform Capability Registry
`get_platform_capabilities()` returns a static capability inventory and status labels, exposed via `GET /platform/capabilities`.

This supports:
- partner due diligence,
- integration planning,
- licensing transparency,
- sales/presentation readiness.

## 7) Document Automation
Veteran module `generate_documents()` auto-creates package artifacts and stores them as documents with metadata snapshots:
- VA Form 26-1880,
- VA hardship letter,
- loan modification package,
- grant application package.

Core `/documents` APIs also support upload/read/list with policy checks.

## 8) Partner and Licensing Capabilities
### Deployment/Licensing paths
- Nonprofit program stack (case + benefits + reporting)
- Government deployment (policy-controlled eligibility + impact tracking)
- Housing organizations (foreclosure mitigation + benefit workflows)
- Financial institutions (partner reporting + benefit/refinance support)

### Available partner/reporting APIs
- `GET /partner/v1/cases/{case_id}/status`
- `GET /partner/v1/cases/{case_id}/workflow-readiness`
- `GET /partner/v1/cases/{case_id}/evidence-verification`
- `GET /partner/v1/veterans/benefit-discovery-summary`
- `POST /partner/v1/veterans/integration-ping`
- `GET /impact/summary`
- `GET /impact/opportunity-map`
- `GET /platform/capabilities`

## 9) Example Use Cases (Current)
1. Veteran benefits discovery and claims guidance.
2. Foreclosure prevention support through matched benefits + escalation workflows.
3. Housing assistance eligibility guidance (e.g., HUD-VASH pathways).
4. Case management for nonprofit service teams.
5. Impact reporting for grant-funded programs and partner dashboards.

## 10) Platform Value Proposition
Universal Pilot operates as a social-impact technology platform because it combines:
- AI-assisted service delivery,
- automated eligibility + benefit discovery,
- document and workflow automation,
- measurable impact analytics,
- modular extension architecture for rapid expansion,
- partner-facing APIs and capability transparency.

## 11) Presentation Slide Outline (12 Slides)
1. Market Problem: Fragmented service delivery + compliance burden
2. Universal Pilot Solution Overview
3. Core Architecture (Policy + AI + Services + Data)
4. Dynamic Module System (Registry/Loader/Broker)
5. Veteran Intelligence Platform
6. Benefit Value Engine
7. Document Automation + Workflow Support
8. Impact Analytics (Summary + Opportunity Map)
9. Partner API & Reporting Layer
10. Capability Registry + Integration Readiness
11. Licensing Models (SaaS, Gov, Nonprofit)
12. Roadmap & Expansion Strategy

## 12) Licensing Pitch Version
### SaaS Model
Multi-tenant managed offering for nonprofits/housing networks with configuration, module activation, and analytics dashboards.

### Government Deployment
Policy-controlled deployment with role sessions, auditability, impact reporting, and controlled partner interfaces.

### Nonprofit Technology Platform
Program operations backbone for veteran/housing services with automated benefit discovery, application support, and funder-grade outcomes reporting.

### Why license now
The platform already includes governed dynamic modules, veteran applied intelligence, impact analytics, and capability APIs—forming a launch-ready v1.0 base for partner onboarding.
