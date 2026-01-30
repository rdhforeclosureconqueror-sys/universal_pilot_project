# db_check.py

from sqlalchemy import create_engine, inspect
from settings import settings  # adjust this import if needed

engine = create_engine(settings.DATABASE_URL)
inspector = inspect(engine)

print("\n✅ TABLES PRESENT IN DB:\n")
for t in inspector.get_table_names():
    print(f" - {t}")
