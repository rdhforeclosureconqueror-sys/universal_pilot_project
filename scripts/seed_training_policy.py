import json
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
from models.policy_versions import PolicyVersion
from db.session import SessionLocal

def load_seed_policy():
    with open("seeds/TRAINING_CONFIG_SEED.json", "r") as f:
        config = json.load(f)

    db: Session = SessionLocal()

    existing = db.query(PolicyVersion).filter_by(
        program_key="training_sandbox",
        version_tag="seed_v1"
    ).first()

    if existing:
        print("Seed policy already loaded.")
        return

    new_policy = PolicyVersion(
        id=str(uuid4()),
        program_key="training_sandbox",
        version_tag="seed_v1",
        is_active=True,
        config_json=config["training_config"],
        created_at=datetime.utcnow()
    )

    db.add(new_policy)
    db.commit()
    db.close()

    print("✅ Training seed policy inserted.")

if __name__ == "__main__":
    load_seed_policy()
