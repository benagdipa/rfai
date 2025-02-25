from sqlalchemy import create_engine, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings
from utils.logger import logger
from contextlib import contextmanager
from typing import Generator
import sqlalchemy.exc as sqlexc

# Database engine with optimized connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,              # Max number of connections in the pool
    max_overflow=10,           # Allow up to 10 additional connections beyond pool_size
    pool_timeout=30,           # Seconds to wait before giving up on getting a connection
    pool_recycle=1800,         # Recycle connections every 30 minutes to prevent stale connections
    pool_pre_ping=True         # Check connection health before use
)

# Session factory for creating database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False     # Prevent attribute expiration on commit for performance
)

# Declarative base for model definitions
Base = declarative_base()

# Define index for DynamicData table (assuming it’s used across agents)
Index(
    'ix_dynamic_data_identifier_timestamp',
    "dynamic_data.identifier",
    "dynamic_data.timestamp",
    postgresql_using="btree"  # Optimize for PostgreSQL; adjust for other DBs if needed
)

# Context manager for session handling with error logging
@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
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
    """
    Dependency to provide a database session for FastAPI endpoints.

    Yields:
        Session: A SQLAlchemy session.

    Raises:
        HTTPException: If database connection fails.
    """
    db = SessionLocal()
    try:
        # Test connection with a lightweight query
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

# Utility function to initialize database schema
def init_db():
    """Initialize the database schema by creating all tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully")
    except sqlexc.SQLAlchemyError as e:
        logger.error(f"Failed to initialize database schema: {str(e)}")
        raise

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
    # Test database setup when run directly
    init_db()
    health = check_db_health()
    print(health)