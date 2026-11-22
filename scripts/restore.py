"""
EventIQ Agent — Database Restore Script
Restores the live database from a timestamped backup.
Always creates a safety backup of the current live database before overwriting.

Usage:
    python scripts/restore.py backups/eventiq_backup_20261122_143000.db

Environment variables:
    DATABASE_PATH — path to live database (default: ./eventiq.db)
"""

import os
import sys
import sqlite3
import shutil
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(PROJECT_ROOT, "eventiq.db")
)


def restore_from_backup(backup_path: str):
    """Restores the live database from the specified backup file."""
    backup_path = os.path.abspath(backup_path)

    if not os.path.isfile(backup_path):
        print(f"[ERROR] Backup file not found: {backup_path}")
        sys.exit(1)

    # Verify the backup is a valid SQLite database before proceeding
    print(f"[INFO] Verifying backup integrity: {backup_path}")
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM clubs")
        club_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM events")
        event_count = cursor.fetchone()[0]
        conn.close()
        print(f"[OK] Backup verified: {club_count} clubs, {event_count} events.")
    except Exception as e:
        print(f"[ERROR] Backup verification failed — restore aborted: {e}")
        sys.exit(1)

    # Safety: create a snapshot of the current live database
    if os.path.isfile(DB_PATH):
        safety_path = DB_PATH + f".pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
        shutil.copy2(DB_PATH, safety_path)
        print(f"[INFO] Safety snapshot of current database: {safety_path}")

    # Perform restore using SQLite online backup API
    print(f"[INFO] Restoring from: {backup_path}")
    source_conn = sqlite3.connect(backup_path)
    dest_conn = sqlite3.connect(DB_PATH)
    try:
        source_conn.backup(dest_conn)
        dest_conn.close()
        source_conn.close()
    except Exception as e:
        print(f"[ERROR] Restore failed: {e}")
        dest_conn.close()
        source_conn.close()
        sys.exit(1)

    # Final verification of restored database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM clubs")
        restored_clubs = cursor.fetchone()[0]
        conn.close()
        print(f"[OK] Restore verified: live database now has {restored_clubs} clubs.")
    except Exception as e:
        print(f"[ERROR] Post-restore verification failed: {e}")
        sys.exit(1)

    print("[DONE] Database restored successfully.")
    print(f"       Start the server: python server.py")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/restore.py <backup_file_path>")
        print("Example: python scripts/restore.py backups/eventiq_backup_20261122_143000.db")
        sys.exit(1)

    restore_from_backup(sys.argv[1])
