"""
Migration: Add number column to episodes table
"""

import sqlite3
from pathlib import Path


def migrate_database(db_path: str) -> None:
    """Add number column to episodes table and initialize values"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(episodes)")
        columns = [column[1] for column in cursor.fetchall()]

        if "number" in columns:
            print("✅ number column already exists in episodes table")
            return

        # Begin transaction
        cursor.execute("BEGIN IMMEDIATE")

        # Add the number column
        cursor.execute(
            """
            ALTER TABLE episodes
            ADD COLUMN number INTEGER
        """
        )

        # Initialize episode numbers based on order within each project
        cursor.execute(
            """
            UPDATE episodes
            SET number = (
                SELECT ROW_NUMBER() OVER (
                    PARTITION BY project_id
                    ORDER BY "order", created_at
                )
                FROM episodes e2
                WHERE e2.id = episodes.id
            )
        """
        )

        # Commit transaction
        conn.commit()
        print("✅ Migration completed: number column added to episodes and initialized")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


def main():
    """Run migration on default database paths"""
    db_paths = ["data/projects.db", "src/data/projects.db"]

    for db_path in db_paths:
        if Path(db_path).exists():
            print(f"🔄 Migrating database: {db_path}")
            migrate_database(db_path)


if __name__ == "__main__":
    main()
