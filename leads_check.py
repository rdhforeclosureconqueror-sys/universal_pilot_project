# leads_check.py

from sqlalchemy import create_engine, text
from settings import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM leads LIMIT 5"))
    for row in result:
        print(dict(row))
