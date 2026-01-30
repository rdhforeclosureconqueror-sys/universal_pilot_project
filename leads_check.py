# leads_check.py
from sqlalchemy import inspect
from db.session import get_db

engine = get_db().get_bind()
inspector = inspect(engine)

tables = inspector.get_table_names()
print("Tables in DB:", tables)
