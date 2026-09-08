from sqlalchemy import create_engine, text

from app.config import settings

engine = create_engine(settings.database_url)

with engine.connect() as connection:
    result = connection.execute(text("SELECT 1"))
    print("Connection successful:", result.fetchone())