from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# The "engine" is the actual connection pool to the database
engine = create_engine(settings.database_url)

# SessionLocal is a factory that creates new "conversations" with the DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is what all your table models will inherit from
Base = declarative_base()

# This function gives each API request its own database session,
# and makes sure it's closed properly afterward
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()