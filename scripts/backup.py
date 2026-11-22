"""
EventIQ Agent — Automated Database Backup Script
Creates a timestamped SQLite backup using sqlite3's online backup API.
Retains the last 7 daily backups automatically.

Usage:
    python scripts/backup.py

Environment variables:
    DATABASE_PATH — path to live database (default: ./eventiq.db)
    BACKUP_DIR    — backup destination directory (default: ./backups)
    BACKUP_RETAIN — number of backups to keep (default: 7)
"""

import os
import sys
import sqlite3
import glob
import shutil
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(PROJECT_ROOT, "eventiq.db")
)
BACKUP_DIR = os.environ.get("BACKUP_DIR", os.path.join(PROJECT_ROOT, "backups"))
BACKUP_RETAIN = int(os.environ.get("BACKUP_RETAIN", "7"))


def create_backup() -> str:
    """Creates a timestamped backup of the EventIQ database."""
    if not os.path.isfile(DB_PATH):
        print(f"[ERROR] Database not found at: {DB_PATH}")
        sys.exit(1)

    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"eventiq_backup_{timestamp}.db")

    print(f"[INFO] Creating backup: {backup_path}")

    # Use SQLite's online backup API (safe for live databases)
    source_conn = sqlite3.connect(DB_PATH)
    dest_conn = sqlite3.connect(backup_path)
    try:
        source_conn.backup(dest_conn)
        dest_conn.close()
        source_conn.close()
    except Exception as e:
        print(f"[ERROR] Backup failed: {e}")
        dest_conn.close()
        source_conn.close()
        if os.path.exists(backup_path):
            os.remove(backup_path)
        sys.exit(1)

    size_kb = os.path.getsize(backup_path) / 1024
    print(f"[OK] Backup created: {backup_path} ({size_kb:.1f} KB)")
    return backup_path


def prune_old_backups():
    """Removes backups older than the retention limit."""
    pattern = os.path.join(BACKUP_DIR, "eventiq_backup_*.db")
    backups = sorted(glob.glob(pattern))

    if len(backups) <= BACKUP_RETAIN:
        return

    to_delete = backups[:len(backups) - BACKUP_RETAIN]
    for path in to_delete:
        os.remove(path)
        print(f"[INFO] Pruned old backup: {os.path.basename(path)}")


def verify_backup(backup_path: str):
    """Verifies the backup is a valid, readable SQLite database."""
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM clubs")
        club_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM events")
        event_count = cursor.fetchone()[0]
        conn.close()
        print(f"[OK] Verification passed: {club_count} clubs, {event_count} events in backup.")
    except Exception as e:
        print(f"[ERROR] Backup verification failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print(f"=== EventIQ Database Backup ===")
    print(f"Source: {DB_PATH}")
    print(f"Destination: {BACKUP_DIR}")
    print(f"Retention: {BACKUP_RETAIN} backups")
    print()

    backup_file = create_backup()
    verify_backup(backup_file)
    prune_old_backups()

    print()
    print("[DONE] Backup completed successfully.")
