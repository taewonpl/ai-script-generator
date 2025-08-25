"""
Migration: Add next_episode_number column to projects table
"""

import sqlite3
from pathlib import Path


def migrate_database(db_path: str) -> None:
    """Add next_episode_number column and initialize values"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(projects)")
        columns = [column[1] for column in cursor.fetchall()]

        if "next_episode_number" in columns:
            print("✅ next_episode_number column already exists")
            return

        # Begin transaction
        cursor.execute("BEGIN IMMEDIATE")

        # Add the column
        cursor.execute(
            """
            ALTER TABLE projects
            ADD COLUMN next_episode_number INTEGER DEFAULT 1
        """
        )

        # Initialize existing projects with max episode order + 1
        # Note: Currently episodes table has 'order' column, not 'number'
        cursor.execute(
            """
            UPDATE projects
            SET next_episode_number = (
                SELECT COALESCE(MAX(e."order"), 0) + 1
                FROM episodes e
                WHERE e.project_id = projects.id
            )
        """
        )

        # Commit transaction
        conn.commit()
        print(
            "✅ Migration completed: next_episode_number column added and initialized"
        )

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
