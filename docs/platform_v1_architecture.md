# Universal Pilot Platform v1.0 Architecture

## Overview
Universal Pilot v1.0 combines policy-controlled AI orchestration, dynamic module activation, veteran benefit intelligence, and impact analytics for launch readiness.

## AI Orchestration Layer
- JWT-authenticated, policy-authorized requests are routed through the AI gateway.
- AI outputs structured intents and actions only.
- Domain execution is mediated through platform services and audit logging.

## Module System (Phase 8)
- `module_registry` stores versioned, policy-validated module specs.
- `ModuleLoaderService` loads active modules at startup and registers scoped runtime routes.
- `DomainServiceBroker` ensures module actions can execute only mapped domain-service handlers.

## Veteran Intelligence Platform (Phase 8.5)
- `VeteranProfile` engine captures benefit-relevant veteran attributes per case.
- Deterministic categorization defines eligibility pathways.
- `BenefitRegistry` + matching engine identifies program eligibility and priority.
- Action plan and document automation support benefit application workflows.
- Progress tracking states enable operational dashboards.

## Impact Analytics Layer (Phase 9)
- Impact summary reports:
  - veterans served
  - benefits discovered
  - benefits claimed
  - benefit value unlocked
  - foreclosures prevented
- Opportunity map aggregates by state for partner strategy.
- Benefit Value Engine estimates monthly, annual, and lifetime benefit totals per case.

## Partner and Capability Interfaces
- `/impact/*` APIs provide executive and partner metrics.
- `/platform/capabilities` publishes launch capability registry.
- Partner integrations consume anonymized benefit-discovery aggregates.

## Launch Readiness
Version 1.0 is launch-ready with:
- policy-controlled AI actions
- dynamic governed module activation
- applied veteran intelligence workflows
- measurable impact and opportunity analytics
- partner-facing capability and reporting endpoints
