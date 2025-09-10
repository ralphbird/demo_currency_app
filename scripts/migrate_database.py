#!/usr/bin/env python3
"""Database migration script to increase numeric precision."""

import sys

from sqlalchemy import text

from currency_app.database import SessionLocal


def migrate_database():
    """Perform database migration to increase numeric field precision."""
    # List of migration steps for PostgreSQL
    migrations = [
        # Increase precision for conversion_history table
        "ALTER TABLE conversion_history ALTER COLUMN amount TYPE NUMERIC(20,2)",
        "ALTER TABLE conversion_history ALTER COLUMN converted_amount TYPE NUMERIC(20,2)",
        "ALTER TABLE conversion_history ALTER COLUMN exchange_rate TYPE NUMERIC(15,8)",
        # Increase precision for rate_history table
        "ALTER TABLE rate_history ALTER COLUMN rate TYPE NUMERIC(15,8)",
    ]

    print("🔄 Starting database migration to increase numeric precision...")

    with SessionLocal() as db:
        try:
            for i, migration_sql in enumerate(migrations, 1):
                print(f"   Step {i}/{len(migrations)}: {migration_sql}")
                db.execute(text(migration_sql))

            db.commit()
            print("✅ Database migration completed successfully!")
            return 0

        except Exception as e:
            db.rollback()
            print(f"❌ Migration failed: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(migrate_database())
