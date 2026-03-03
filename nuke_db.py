from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execution_options(isolation_level="AUTOCOMMIT")

    print("Dropping public schema...")
    conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
    
    print("Recreating public schema...")
    conn.execute(text("CREATE SCHEMA public;"))

    print("Database nuked clean.")

print("Done.")
