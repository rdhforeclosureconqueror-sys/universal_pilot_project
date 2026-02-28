from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# ✅ Use localhost for tests & dev runtime
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/universal_case_os"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ✅ Canonical DB dependency (runtime + tests)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# register workflow sync listeners
import app.models.workflow_events  # noqa: F401
