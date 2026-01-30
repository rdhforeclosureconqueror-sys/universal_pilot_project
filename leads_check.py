# leads_check.py

from sqlalchemy import inspect
from db.session import get_db  # adjust path if needed

with next(get_db()) as session:
    engine = session.get_bind()
    inspector = inspect(engine)
    print("\n✅ Tables found in database:")
    for t in inspector.get_table_names():
        print(f" - {t}")
