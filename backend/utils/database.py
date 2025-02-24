from sqlalchemy import create_engine, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings

engine = create_engine(settings.DATABASE_URL, pool_size=20, max_overflow=0)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

Index('ix_dynamic_data_identifier_timestamp', "dynamic_data.identifier", "dynamic_data.timestamp")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
