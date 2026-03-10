# Phase 11 — Lead Intelligence & Essential Worker Expansion

## Architecture
Lead Discovery
↓
Case Creation
↓
Property Analysis
↓
Partner Routing
↓
Buyer Matching

## Components
- `essential_worker_housing_service` for worker profile, program discovery, assistance value estimation, action plans, and required documents.
- `lead_intelligence_service` for ingestion, deduplication, lead scoring, connectors, and lead-to-case automation.
- DFW connectors:
  - dallas_county_foreclosure_connector
  - tarrant_county_trustee_connector
  - collin_county_notice_connector
- `skiptrace_service` with provider adapters:
  - batchdata_adapter
  - propstream_adapter
  - peopledatalabs_adapter

## Policy engine compatibility
Case intake now supports both:
- `allowed_meta_fields`
- `allowed_fields`

and retains support for legacy `custom_fields`.

## Verification endpoints
- `GET /verify/policy-engine`
- `GET /verify/essential-worker-module`
- `GET /verify/lead-intelligence`
- `GET /verify/dfw-connectors`
- `GET /verify/skiptrace-integration`

## API surface
- `POST /essential-worker/profile`
- `POST /essential-worker/discover-benefits`
- `POST /essential-worker/action-plan`
- `POST /leads/intelligence/ingest`
- `POST /leads/intelligence/score`
- `POST /leads/intelligence/ingest-csv`

## Automation
When lead score exceeds threshold, a case is created automatically and linked in lead scores.
