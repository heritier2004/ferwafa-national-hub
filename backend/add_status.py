import os, sys
from sqlalchemy import create_engine, text
sys.path.insert(0, r'c:\Users\User\Documents\NEW_VERSION')
from backend.app.config.database import DATABASE_URL
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE institutions ADD COLUMN status VARCHAR DEFAULT 'PENDING';"))
    conn.commit()
    print('Column status added successfully.')
