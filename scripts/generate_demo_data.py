#!/usr/bin/env python3
"""Script to generate demo historical exchange rate data."""

import sys

from currency_app.database import SessionLocal, create_tables
from currency_app.services.rates_history_service import RatesHistoryService


def main():
    """Generate demo historical data."""
    print("🔄 Generating demo historical exchange rate data...")

    # Ensure tables exist
    create_tables()

    # Create database session
    db = SessionLocal()

    try:
        # Initialize rates history service
        history_service = RatesHistoryService(db)

        # Generate 30 days of historical data (4 snapshots per day = 120 records per currency)
        total_records = history_service.generate_historical_data_for_demo(days_back=30)

        print(f"✅ Generated {total_records} historical rate records")
        print(f"   - {total_records // 10} records per currency")
        print("   - Covers last 30 days with 4 snapshots per day")

        # Also store current rates as a snapshot
        current_records = history_service.store_current_rates()
        print(f"✅ Stored {current_records} current rate snapshots")

        print("\n📊 Demo data generation complete!")
        print("   You can now view historical trends in the dashboard")

    except Exception as e:
        print(f"❌ Error generating demo data: {e}")
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
