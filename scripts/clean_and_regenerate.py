#!/usr/bin/env python3
"""Script to clean database and regenerate demo data with correct USD rates."""

import sys

from currency_app.database import SessionLocal, engine
from currency_app.models.database import Base
from currency_app.services.rates_history_service import RatesHistoryService


def main():
    """Clean database and regenerate demo data."""
    print("🧹 Cleaning existing database...")

    # Drop all tables and recreate them
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    print("✅ Database cleaned and recreated")

    # Create database session
    db = SessionLocal()

    try:
        # Initialize rates history service
        history_service = RatesHistoryService(db)

        print("🔄 Generating fresh demo historical exchange rate data...")

        # Generate 30 days of historical data (4 snapshots per day = 120 records per currency)
        total_records = history_service.generate_historical_data_for_demo(days_back=30)

        print(f"✅ Generated {total_records} historical rate records")
        print(f"   - {total_records // 10} records per currency")
        print("   - USD rates are all exactly 1.000000 (base currency)")
        print("   - Other currencies have realistic volatility")

        # Also store current rates as a snapshot
        current_records = history_service.store_current_rates()
        print(f"✅ Stored {current_records} current rate snapshots")

        print("\n📊 Clean regeneration complete!")
        print("   USD rates are now correctly fixed at 1.000000")

    except Exception as e:
        print(f"❌ Error regenerating data: {e}")
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
