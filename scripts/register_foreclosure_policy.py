import os
import sys
import uuid
from datetime import datetime

# ✅ Make sure root directory is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from db.session import SessionLocal
from app.models.policy_versions import PolicyVersion
from policy.modules.foreclosure_policy_module import FORECLOSURE_POLICY


def run():
    db = SessionLocal()

    policy = PolicyVersion(
        id=str(uuid.uuid4()),
        program_key="foreclosure_stabilization_v1",
        version_tag="v1.0.0",
        is_active=True,
        config_json=FORECLOSURE_POLICY,
        created_at=datetime.utcnow()
    )

    db.add(policy)
    db.commit()
    print("✅ Foreclosure policy inserted.")

    db.close()


if __name__ == "__main__":
    run()
