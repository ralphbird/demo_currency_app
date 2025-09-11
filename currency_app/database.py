"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from currency_app.config import settings
from currency_app.models.database import Base

# Database configuration
DATABASE_URL = settings.database_url

# Create engine with database-specific optimizations
if DATABASE_URL.startswith("sqlite://"):
    # SQLite configuration for local development and testing
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Needed for SQLite
        echo=False,  # Set to True for SQL debugging
    )
else:
    # PostgreSQL configuration for Docker/production
    engine = create_engine(
        DATABASE_URL,
        pool_size=50,  # Connection pool size (increased for high load)
        max_overflow=100,  # Additional connections beyond pool_size (increased for high load)
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False,  # Set to True for SQL debugging
    )

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
