# EventIQ Agent — Backup, Recovery & Business Continuity Manual

## 1. Backup Strategy Overview

EventIQ Agent stores all operational data (clubs, events, sessions, reports, recommendations, audit logs) in an embedded **SQLite** database (`eventiq.db`).

- **Journal Mode:** Write-Ahead Logging (`WAL`).
- **Concurrency:** Safe live backups while readers and writers are actively querying the system.
- **Mechanism:** `sqlite3.Connection.backup()` online API (non-blocking).

---

## 2. Automated Scheduled Backups

The backup utility `scripts/backup.py` creates a point-in-time snapshot, verifies database integrity, and automatically prunes snapshots older than the retention threshold (default: 7).

### Running a Manual Backup
```bash
python scripts/backup.py
```

Sample output:
```
=== EventIQ Database Backup ===
Source: C:\Users\Admin\Downloads\agentic_ai\eventiq.db
Destination: C:\Users\Admin\Downloads\agentic_ai\backups
Retention: 7 backups

[INFO] Creating backup: C:\Users\Admin\Downloads\agentic_ai\backups\eventiq_backup_20261122_144850.db
[OK] Backup created: C:\Users\Admin\Downloads\agentic_ai\backups\eventiq_backup_20261122_144850.db (660.0 KB)
[OK] Verification passed: 6 clubs, 24 events in backup.
[DONE] Backup completed successfully.
```

### Setting up Scheduled Backups

#### Windows (Task Scheduler)
Create a daily scheduled task to run at 02:00:
```powershell
$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "C:\Users\Admin\Downloads\agentic_ai\scripts\backup.py" -WorkingDirectory "C:\Users\Admin\Downloads\agentic_ai"
$Trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $Action -Trigger $Trigger -TaskName "EventIQ_Daily_Backup" -Description "Daily snapshot of EventIQ SQLite database"
```

#### Linux (Cron)
```bash
0 2 * * * cd /opt/eventiq && /usr/bin/python3 scripts/backup.py >> /var/log/eventiq_backup.log 2>&1
```

---

## 3. Disaster Recovery & Restoration

The restore utility `scripts/restore.py` handles safe restoration:
1. Verifies the target backup is uncorrupted.
2. Creates an immediate safety snapshot of the live database (`.pre_restore_timestamp.bak`).
3. Safely streams the backup data into `eventiq.db`.
4. Performs post-restore validation.

### Restoring from Backup
```bash
python scripts/restore.py backups/eventiq_backup_20261122_144850.db
```

Sample output:
```
[INFO] Verifying backup integrity: backups/eventiq_backup_20261122_144850.db
[OK] Backup verified: 6 clubs, 24 events.
[INFO] Safety snapshot of current database: eventiq.db.pre_restore_20261122_144850.bak
[INFO] Restoring from: backups/eventiq_backup_20261122_144850.db
[OK] Restore verified: live database now has 6 clubs.
[DONE] Database restored successfully.
```

---

## 4. Recovery Time & Point Objectives (RTO / RPO)

- **Recovery Point Objective (RPO):** Maximum 24 hours with daily backups; 1 hour if backup cron is set hourly.
- **Recovery Time Objective (RTO):** Less than 2 minutes (restore script executes in < 2 seconds).
