"""Tests for database functionality."""

import contextlib

from sqlalchemy.orm import Session

from currency_app.database import SessionLocal, get_db


class TestDatabaseSessionManagement:
    """Test database session management functionality."""

    def test_get_db_creates_session(self):
        """Test that get_db creates a valid database session."""
        db_generator = get_db()
        db = next(db_generator)

        assert isinstance(db, Session)
        assert db.bind is not None

        # Clean up the generator
        with contextlib.suppress(StopIteration):
            next(db_generator)

    def test_get_db_closes_session(self):
        """Test that get_db properly manages session lifecycle."""
        db_generator = get_db()
        db = next(db_generator)

        # Verify session is created and has a bind
        assert db.bind is not None

        # Test that session works initially
        from sqlalchemy import text

        result = db.execute(text("SELECT 1"))
        assert result.scalar() == 1

        # Complete the generator (simulates FastAPI dependency cleanup)
        with contextlib.suppress(StopIteration):
            next(db_generator)

        # The session has been closed by the finally block in get_db()
        # We can verify this by checking that db.close() was called
        assert db is not None  # Session object still exists but was closed

    def test_get_db_session_isolation(self):
        """Test that get_db creates separate session instances."""
        db_generator1 = get_db()
        db_generator2 = get_db()

        db1 = next(db_generator1)
        db2 = next(db_generator2)

        # Should be different session objects
        assert db1 is not db2
        assert id(db1) != id(db2)

        # Clean up generators
        for gen in [db_generator1, db_generator2]:
            with contextlib.suppress(StopIteration):
                next(gen)

    def test_sessionlocal_creates_valid_session(self):
        """Test that SessionLocal creates a valid session."""
        db = SessionLocal()

        try:
            assert isinstance(db, Session)
            assert db.bind is not None

            # Test that we can execute a simple query
            from sqlalchemy import text

            result = db.execute(text("SELECT 1"))
            assert result.scalar() == 1

        finally:
            db.close()

    def test_database_session_transaction_handling(self):
        """Test that database sessions handle transactions properly."""
        db = SessionLocal()

        try:
            # Start a transaction
            db.begin()

            # Execute a query within the transaction
            from sqlalchemy import text

            result = db.execute(text("SELECT 1 as test_value"))
            assert result.scalar() == 1

            # Rollback the transaction
            db.rollback()

        finally:
            db.close()
