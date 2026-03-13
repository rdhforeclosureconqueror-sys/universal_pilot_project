# Import Graph Repair Report

## Summary

This repair focused on import graph stabilization (not architecture redesign).

The orchestration gateway architecture remains unchanged:

- AI execution entry point: `handle_mufasa_prompt`
- AI explanation entry point: `handle_mufasa_question`

The key fix was to break a high-risk circular import chain by converting selected top-level imports to local function imports.

---

## Circular Dependency Risks Found

### Risk chain A (high risk)

Potential cycle at import time:

- `api/routes/mufasa_ai.py`
  -> imports `app/services/ai_orchestration_service.py`
- `app/services/ai_orchestration_service.py`
  -> imported `app/services/platform_knowledge_service.py` at module load
- `app/services/platform_knowledge_service.py`
  -> imported `app/services/module_loader_service.py` at module load
- `app/services/module_loader_service.py`
  -> imports many domain services and model dependencies

This large eager-import chain can produce partial module initialization and `ImportError` symptoms like:

`cannot import name 'handle_mufasa_prompt'`.

### Risk chain B (medium risk)

`PlatformKnowledgeService` imported `DomainServiceBroker` at module import time, forcing loader/service graph hydration even when only Mufasa explain path was needed.

---

## Files Modified

1. `app/services/ai_orchestration_service.py`
   - moved `PlatformKnowledgeService` import from module scope to function scope (`handle_mufasa_question`) to defer dependency loading.

2. `app/services/platform_knowledge_service.py`
   - moved `DomainServiceBroker` import from module scope to function scope (`_domain_service_registry`) to prevent eager loader graph import.

3. `docs/import_graph_repair_report.md`
   - added this report.

---

## Dependency Direction Verification

Validated the intended direction:

- **schemas**: only typing/pydantic style imports (no service/route imports)
- **services**: no route imports
- **routes**: import services/schemas as expected

No violations were found for the targeted graph checks.

---

## Export/Import Guarantees

Confirmed these are defined and importable from `app/services/ai_orchestration_service.py`:

- `handle_mufasa_prompt`
- `handle_mufasa_question`

Confirmed `api/routes/mufasa_ai.py` imports them successfully.

---

## Validation Results

1. Static compile:
- `python -m py_compile app/services/ai_orchestration_service.py app/services/platform_knowledge_service.py api/routes/mufasa_ai.py api/main.py`

2. Import checks:
- imported `handle_mufasa_prompt` and `handle_mufasa_question` directly from orchestration service
- imported `api.routes.mufasa_ai`

3. App boot check:
- `uvicorn api.main:app --lifespan off` starts successfully (proves import graph integrity and route loading without startup DB hooks)

4. Route existence checks:
- `/admin/ai/mufasa/chat` loaded
- `/admin/ai/mufasa/explain` loaded

---

## Notes

- The repository’s normal startup (`uvicorn api.main:app`) still depends on database availability because startup hooks execute admin bootstrap/module loading.
- This repair specifically addresses import graph integrity and circular import risk while preserving the current orchestration architecture.
