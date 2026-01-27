# scripts/verify_policies.py

from db.session import SessionLocal
from models.policy_versions import PolicyVersion

def run():
    db = SessionLocal()
    policies = db.query(PolicyVersion).all()

    for p in policies:
        print("Program:", p.program_key)
        print("Version:", p.version)
        print("Active:", p.is_active)
        print("—" * 30)

    db.close()

if __name__ == "__main__":
    run()
