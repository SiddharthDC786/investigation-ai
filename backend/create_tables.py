from app.database import Base, engine
from app.models.case import Case
from app.models.source_record import SourceRecord

Base.metadata.create_all(bind=engine)
print("Tables created successfully")