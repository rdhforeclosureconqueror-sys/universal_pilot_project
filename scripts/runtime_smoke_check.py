from db.session import SessionLocal
from app.models.policy_versions import PolicyVersion
from sqlalchemy import text


def run_smoke_checks():
    errors = []

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
    except Exception as e:
        errors.append(f"DB unreachable: {e}")
    finally:
        try:
            db.close()
        except Exception:
            pass

    try:
        db = SessionLocal()
        db.query(PolicyVersion).first()
    except Exception as e:
        errors.append(f"Policy query failed: {e}")
    finally:
        try:
            db.close()
        except Exception:
            pass

    if errors:
        raise RuntimeError(f"Startup checks failed: {errors}")


if __name__ == "__main__":
    run_smoke_checks()
