"""SQLAlchemy database models."""

from datetime import UTC, datetime

import uuid_utils.compat as uuid
from sqlalchemy import Column, DateTime, Integer, Numeric, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ConversionHistory(Base):
    """Database model for conversion history."""

    __tablename__ = "conversion_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversion_id = Column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid7())
    )
    request_id = Column(String(36), nullable=True)
    amount = Column(Numeric(20, 2), nullable=False)
    from_currency = Column(String(3), nullable=False)
    to_currency = Column(String(3), nullable=False)
    converted_amount = Column(Numeric(20, 2), nullable=False)
    exchange_rate = Column(Numeric(15, 8), nullable=False)
    account_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    conversion_timestamp = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    def __repr__(self) -> str:
        """Return string representation of ConversionHistory."""
        return (
            f"<ConversionHistory("
            f"id={self.id}, "
            f"conversion_id='{self.conversion_id}', "
            f"account_id='{self.account_id}', "
            f"user_id='{self.user_id}', "
            f"from_currency='{self.from_currency}', "
            f"to_currency='{self.to_currency}', "
            f"amount={self.amount}"
            f")>"
        )


class RateHistory(Base):
    """Database model for historical exchange rates."""

    __tablename__ = "rate_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rate_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid7()))
    currency = Column(String(3), nullable=False)
    rate = Column(Numeric(15, 8), nullable=False)
    base_currency = Column(String(3), nullable=False, default="USD")
    recorded_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    rate_source = Column(String(50), nullable=False, default="simulated")

    def __repr__(self) -> str:
        """Return string representation of RateHistory."""
        return (
            f"<RateHistory("
            f"id={self.id}, "
            f"rate_id='{self.rate_id}', "
            f"currency='{self.currency}', "
            f"rate={self.rate}, "
            f"recorded_at={self.recorded_at}"
            f")>"
        )
