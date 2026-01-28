# scripts/runtime_smoke_check.py
from policy.modules.foreclosure_policy_module import ForeclosurePolicy
from database.session import get_db
from audit.engine import audit_engine

def run_smoke_checks():
    errors = []

    # Policy registered
    try:
        policy = ForeclosurePolicy()
    except Exception as e:
        errors.append(f"Policy load failed: {e}")

    # DB reachable
    try:
        db = next(get_db())
        db.execute("SELECT 1")
    except Exception as e:
        errors.append(f"DB unreachable: {e}")

    # Audit engine alive
    try:
        audit_engine.ping()
    except Exception as e:
        errors.append(f"Audit engine failure: {e}")

    if errors:
        raise RuntimeError(f"Startup checks failed: {errors}")
