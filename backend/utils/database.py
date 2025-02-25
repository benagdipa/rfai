from sqlalchemy import create_engine, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from utils.logger import logger
from contextlib import contextmanager
from typing import Generator, Dict, Any  # Added Dict to imports
import sqlalchemy.exc as sqlexc
from fastapi import HTTPException

# Declarative base for model definitions (defined at module level, no settings needed yet)
Base = declarative_base()

# Engine and session factory will be initialized later
engine = None
SessionLocal = None

# Define index for DynamicData table (no settings dependency here)
Index(
    'ix_dynamic_data_identifier_timestamp',
    "dynamic_data.identifier",
    "dynamic_data.timestamp",
    postgresql_using="btree"  # Optimize for PostgreSQL; adjust for other DBs if needed
)

# Initialization function to set up the database with settings
def init_db(database_url: str) -> None:
    """Initialize the database engine and session factory with the provided URL."""
    global engine, SessionLocal
    try:
        engine = create_engine(
            database_url,
            pool_size=20,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
        )
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            expire_on_commit=False,
        )
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully")
    except sqlexc.SQLAlchemyError as e:
        logger.error(f"Failed to initialize database schema: {str(e)}")
        raise

# Context manager for session handling with error logging
@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except sqlexc.SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error occurred: {str(e)}")
        raise
    finally:
        session.close()

# Dependency for FastAPI to provide DB sessions
def get_db() -> Generator[Session, None, None]:
    """Dependency to provide a database session for FastAPI endpoints."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    db = SessionLocal()
    try:
        db.execute("SELECT 1")
        yield db
    except sqlexc.OperationalError as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Database unavailable")
    except Exception as e:
        logger.error(f"Unexpected database error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        db.close()

# Utility function to check database health
def check_db_health() -> Dict[str, Any]:
    """Check the health of the database connection."""
    with session_scope() as session:
        try:
            session.execute("SELECT 1")
            return {"status": "healthy", "details": "Database connection is active"}
        except sqlexc.OperationalError as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {"status": "unhealthy", "details": str(e)}

if __name__ == "__main__":
    from config.settings import load_settings
    settings = load_settings()
    init_db(settings.DATABASE_URL)
    health = check_db_health()
    print(health)