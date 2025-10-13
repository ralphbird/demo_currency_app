"""Database configuration and session management."""

import time
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.exc import TimeoutError as SQLTimeoutError
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
        pool_size=3,  # Connection pool size
        max_overflow=0,  # Additional connections
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_timeout=5,  # Timeout after 5 seconds waiting for connection
        echo=False,  # Set to True for SQL debugging
    )

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get database session."""
    start_time = time.time()
    db = None

    try:
        db = SessionLocal()
        # Update connection pool metrics
        from currency_app.middleware.metrics import update_connection_pool_metrics

        update_connection_pool_metrics(engine)

        yield db

    except SQLTimeoutError:
        # Record connection timeout
        from currency_app.middleware.metrics import record_database_connection_timeout

        record_database_connection_timeout()
        raise
    except Exception as e:
        # Record connection error
        from currency_app.middleware.metrics import record_database_connection_error

        error_type = type(e).__name__
        record_database_connection_error(error_type)
        raise
    finally:
        if db:
            db.close()

        # Record session duration
        duration = time.time() - start_time
        from currency_app.middleware.metrics import record_database_query_duration

        record_database_query_duration("session", "general", duration)


@contextmanager
def get_db_with_metrics():
    """Context manager for database sessions with comprehensive metrics tracking."""
    start_time = time.time()
    db = None

    try:
        db = SessionLocal()
        # Update connection pool metrics
        from currency_app.middleware.metrics import update_connection_pool_metrics

        update_connection_pool_metrics(engine)

        yield db

    except SQLTimeoutError:
        # Record connection timeout
        from currency_app.middleware.metrics import record_database_connection_timeout

        record_database_connection_timeout()
        raise
    except Exception as e:
        # Record connection error
        from currency_app.middleware.metrics import record_database_connection_error

        error_type = type(e).__name__
        record_database_connection_error(error_type)
        raise
    finally:
        if db:
            db.close()

        # Record session duration
        duration = time.time() - start_time
        from currency_app.middleware.metrics import record_database_query_duration

        record_database_query_duration("session", "general", duration)
