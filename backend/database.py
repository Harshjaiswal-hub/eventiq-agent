"""
EventIQ Agent — Persistent Storage & Database Layer
Uses SQLite for zero-configuration, robust academic persistence.
Tables:
- semesters
- clubs
- events (records observed vs imputed values)
- conversations & messages (short-term conversational memory)
- reports (historical report archive)
- recommendations (human-in-the-loop review statuses)
- documents (RAG vector/text chunks and metadata)
- execution_logs (multi-agent audit trail)
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "eventiq.db")
)

def get_db_connection():
    """Returns a connection to the SQLite database with row factory and WAL/FK pragmas enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn

def init_db():
    """Initializes all database tables, constraints, indexes, and WAL journal mode."""
    conn = get_db_connection()
    conn.execute("PRAGMA journal_mode = WAL")
    cursor = conn.cursor()

    # 1. Semesters Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semesters (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Clubs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clubs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            tagline TEXT,
            color TEXT NOT NULL,
            icon TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Events Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            club_id TEXT NOT NULL,
            semester TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            date TEXT NOT NULL,
            registrations INTEGER NOT NULL,
            attendance INTEGER,
            is_attendance_imputed BOOLEAN DEFAULT 0,
            feedback_json TEXT, -- array of ratings [1..5]
            speaker_rating REAL,
            duration_hours REAL,
            resources_used REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(club_id) REFERENCES clubs(id)
        )
    """)

    # 4. Conversations & Messages (Short-Term Memory)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL, -- 'user', 'assistant', 'system'
            content TEXT NOT NULL,
            tool_calls_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )
    """)

    # 5. Saved Reports (Long-Term Memory)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            semester TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            markdown_content TEXT NOT NULL,
            provenance_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 6. Recommendations & Human-in-the-Loop Decisions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id TEXT PRIMARY KEY,
            semester TEXT NOT NULL,
            club_id TEXT,
            recommendation_text TEXT NOT NULL,
            evidence_metric TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'revision_requested'
            reviewer_comment TEXT,
            decision_timestamp TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 7. Document Chunks for RAG Retrieval
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            doc_type TEXT NOT NULL, -- 'policy', 'rubric', 'report'
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata_json TEXT,
            embedding_json TEXT, -- serialised float vector
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 8. Execution Logs (Multi-Agent Trace)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            agent_name TEXT NOT NULL,
            action TEXT NOT NULL,
            details_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 9. Authentication, Users & Sessions (Phase 2 Security)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL, -- 'ADMIN', 'EVALUATOR', 'CLUB_LEAD'
            club_id TEXT,       -- assigned club if CLUB_LEAD
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            csrf_token TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            username TEXT,
            user_id TEXT,
            ip_address TEXT,
            details_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 10. Performance, Concurrency & Security Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_club_sem ON events(club_id, semester)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recs_sem_status ON recommendations(semester, status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_logs_session ON execution_logs(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_security_logs_event ON security_logs(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_security_logs_user ON security_logs(username)")

    conn.commit()
    conn.close()

def seed_db_if_empty():
    """
    Safely seeds initial database from canonical data without duplicating records.
    Also ensures initial security accounts (admin, evaluator, leads) are initialized.
    """
    init_db()
    from backend.security import seed_security_accounts_if_empty
    seed_security_accounts_if_empty()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM clubs")
    if cursor.fetchone()["cnt"] > 0:
        conn.close()
        return

    # Seed Semester
    cursor.execute("""
        INSERT OR REPLACE INTO semesters (id, name, start_date, end_date)
        VALUES ('spring_2026', 'Spring 2026', '2026-01-15', '2026-05-30')
    """)

    # Seed canonical clubs and events
    clubs_data = [
        {
            "id": "codecraft", "name": "CodeCraft", "tagline": "Competitive Programming & DSA",
            "color": "#7c3aed", "icon": "⚡",
            "events": [
                {"id": "cc1", "name": "DSA Bootcamp", "type": "Workshop", "date": "2026-01-22", "reg": 120, "att": 108, "fb": [4,5,5,4,5,3,4,5,4,4,5,5,4,3,5,4,5,4,4,5,5,4,4,5,3,4,5,5,4,4], "spk": 4.7, "hrs": 6, "res": 850},
                {"id": "cc2", "name": "Hackathon 3.0", "type": "Hackathon", "date": "2026-02-14", "reg": 200, "att": 188, "fb": [5,5,4,5,5,5,4,5,5,5,4,4,5,5,5,4,5,5,3,5,5,4,5,5,4,5,5,5,4,5,5,5,4,5,5,5,4,4,5], "spk": 4.9, "hrs": 24, "res": 2200},
                {"id": "cc3", "name": "LeetCode Weekly Grind", "type": "Practice Session", "date": "2026-03-08", "reg": 80, "att": None, "fb": [4,4,3,5,4,4,5,3,4,4,4,5,4,3,4], "spk": 4.1, "hrs": 3, "res": 100},
                {"id": "cc4", "name": "Inter-College Code War", "type": "Competition", "date": "2026-04-20", "reg": 150, "att": 142, "fb": [5,5,5,4,5,4,5,5,4,5,5,5,4,5,5,5,4,5,5,4,5,5,5,4,5], "spk": 4.8, "hrs": 8, "res": 1800}
            ]
        },
        {
            "id": "robotech", "name": "RoboTech", "tagline": "Robotics & Embedded Systems",
            "color": "#0891b2", "icon": "🤖",
            "events": [
                {"id": "rt1", "name": "Arduino Workshop", "type": "Workshop", "date": "2026-01-28", "reg": 90, "att": 85, "fb": [4,5,4,4,5,4,3,4,5,4,4,4,3,5,4,4,5,4,4,3], "spk": 4.4, "hrs": 5, "res": 1200},
                {"id": "rt2", "name": "Bot Brawl Championship", "type": "Competition", "date": "2026-02-22", "reg": 60, "att": 55, "fb": [5,4,5,5,4,4,5,4,5,5,4,5,4,5,5,4,4,5], "spk": 4.6, "hrs": 10, "res": 3000},
                {"id": "rt3", "name": "Drone Racing Demo", "type": "Demo", "date": "2026-03-15", "reg": 110, "att": 98, "fb": None, "spk": 4.5, "hrs": 3, "res": 500},
                {"id": "rt4", "name": "IoT Summit", "type": "Seminar", "date": "2026-05-10", "reg": 75, "att": 60, "fb": [3,4,3,4,4,3,3,4,4,3,4,4,3,3,4], "spk": 3.9, "hrs": 4, "res": 700}
            ]
        },
        {
            "id": "cybershield", "name": "CyberShield", "tagline": "Cybersecurity & Ethical Hacking",
            "color": "#dc2626", "icon": "🛡️",
            "events": [
                {"id": "cs1", "name": "CTF Beginners Edition", "type": "Competition", "date": "2026-02-01", "reg": 95, "att": 90, "fb": [5,4,5,5,4,5,5,4,5,5,5,4,5,5,4,5,5,4,5,5], "spk": 4.8, "hrs": 8, "res": 600},
                {"id": "cs2", "name": "Kali Linux Deep Dive", "type": "Workshop", "date": "2026-03-05", "reg": 70, "att": 65, "fb": [4,5,4,4,5,4,5,4,4,5,4,5,4,4,5], "spk": 4.6, "hrs": 6, "res": 400},
                {"id": "cs3", "name": "Cyber Hygiene Talk", "type": "Seminar", "date": "2026-04-08", "reg": 130, "att": 118, "fb": [4,4,3,5,4,4,5,3,4,4,4,3,4,4,5,4,3,4,4,5,4,4,3,4,4,4,4,5,4,4], "spk": 4.3, "hrs": 2, "res": 200},
                {"id": "cs4", "name": "Advanced CTF Finals", "type": "Competition", "date": "2026-05-18", "reg": 50, "att": 48, "fb": [5,5,5,4,5,5,5,5,4,5,5,5,4,5,5], "spk": 4.9, "hrs": 12, "res": 900}
            ]
        },
        {
            "id": "dataminds", "name": "DataMinds", "tagline": "Data Science & Machine Learning",
            "color": "#059669", "icon": "📊",
            "events": [
                {"id": "dm1", "name": "Python for Data Science", "type": "Workshop", "date": "2026-01-30", "reg": 140, "att": 125, "fb": [4,5,4,4,5,4,3,4,5,4,4,4,3,5,4,4,5,4,4,3,4,5,4,4,5], "spk": 4.5, "hrs": 8, "res": 500},
                {"id": "dm2", "name": "Kaggle Hackathon Prep", "type": "Workshop", "date": "2026-02-20", "reg": 85, "att": 70, "fb": [3,4,3,4,4,3,3,4,4,3,4,4,3,3,4,3,4,3,4,4], "spk": 3.8, "hrs": 5, "res": 300},
                {"id": "dm3", "name": "ML Model Showdown", "type": "Competition", "date": "2026-03-28", "reg": 100, "att": None, "fb": [4,5,5,4,5,4,5,5,4,4,5,4,5,5,4,5,5,4,4,5], "spk": 4.7, "hrs": 6, "res": 200},
                {"id": "dm4", "name": "AI Ethics Panel", "type": "Seminar", "date": "2026-05-05", "reg": 180, "att": 160, "fb": [4,4,5,4,4,5,4,4,5,4,4,4,5,4,4,5,4,4,5,4,4,4,5,4,4,5,4,4,4,5], "spk": 4.6, "hrs": 3, "res": 300}
            ]
        },
        {
            "id": "cloudnine", "name": "CloudNine", "tagline": "Cloud Computing & DevOps",
            "color": "#d97706", "icon": "☁️",
            "events": [
                {"id": "cn1", "name": "AWS Fundamentals", "type": "Workshop", "date": "2026-02-10", "reg": 110, "att": 88, "fb": [3,4,3,3,4,3,4,4,3,3,4,3,3,4,3,3,4,3,4,4], "spk": 3.7, "hrs": 6, "res": 800},
                {"id": "cn2", "name": "Docker & Kubernetes Crash Course", "type": "Workshop", "date": "2026-03-18", "reg": 75, "att": 60, "fb": [4,3,4,4,3,4,3,4,4,3,4,4,3,4,4], "spk": 4.0, "hrs": 7, "res": 600},
                {"id": "cn3", "name": "Cloud Build Challenge", "type": "Competition", "date": "2026-04-14", "reg": 55, "att": 40, "fb": [3,3,4,3,3,4,3,3,4,3,3,3], "spk": 3.5, "hrs": 8, "res": 1000},
                {"id": "cn4", "name": "DevOps Culture Talk", "type": "Seminar", "date": "2026-05-20", "reg": 90, "att": None, "fb": None, "spk": None, "hrs": 2, "res": 150}
            ]
        },
        {
            "id": "designlab", "name": "DesignLab", "tagline": "UI/UX Design & Product Thinking",
            "color": "#db2777", "icon": "🎨",
            "events": [
                {"id": "dl1", "name": "Figma Masterclass", "type": "Workshop", "date": "2026-01-25", "reg": 95, "att": 90, "fb": [5,5,4,5,5,4,5,5,4,5,5,4,5,5,5,4,5,5,4,5], "spk": 4.8, "hrs": 5, "res": 300},
                {"id": "dl2", "name": "Design Thinking Sprint", "type": "Workshop", "date": "2026-02-28", "reg": 70, "att": 68, "fb": [4,5,5,4,5,5,4,5,5,4,5,4,5,5,4,5,4,5], "spk": 4.7, "hrs": 8, "res": 500},
                {"id": "dl3", "name": "UX Research Symposium", "type": "Seminar", "date": "2026-04-02", "reg": 60, "att": 52, "fb": [4,4,5,4,4,5,4,4,4,5,4,4,5,4,4], "spk": 4.4, "hrs": 3, "res": 200},
                {"id": "dl4", "name": "UI Redesign Challenge", "type": "Competition", "date": "2026-05-25", "reg": 80, "att": 75, "fb": [5,5,4,5,5,5,4,5,5,4,5,5,5,4,5,5,4,5,5,5], "spk": 4.9, "hrs": 6, "res": 400}
            ]
        }
    ]

    for c in clubs_data:
        cursor.execute("""
            INSERT OR REPLACE INTO clubs (id, name, tagline, color, icon)
            VALUES (?, ?, ?, ?, ?)
        """, (c["id"], c["name"], c["tagline"], c["color"], c["icon"]))

        for ev in c["events"]:
            fb_str = json.dumps(ev["fb"]) if ev["fb"] is not None else None
            is_imputed = 1 if ev["att"] is None else 0
            cursor.execute("""
                INSERT OR REPLACE INTO events 
                (id, club_id, semester, name, type, date, registrations, attendance, is_attendance_imputed, feedback_json, speaker_rating, duration_hours, resources_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ev["id"], c["id"], "Spring 2026", ev["name"], ev["type"], ev["date"],
                ev["reg"], ev["att"], is_imputed, fb_str, ev["spk"], ev["hrs"], ev["res"]
            ))

    # Seed baseline recommendations
    cursor.execute("""
        INSERT OR REPLACE INTO recommendations (id, semester, club_id, recommendation_text, evidence_metric, status)
        VALUES 
        ('rec_1', 'Spring 2026', 'cloudnine', 'Implement compulsory pre-event RSVP reminders to increase attendance rate from 68.3% to over 80%.', 'attendance_rate = 68.3%', 'pending'),
        ('rec_2', 'Spring 2026', 'all', 'Standardize digital check-in across all technical clubs using QR verification to eradicate missing attendance logs.', 'missing_attendance = 3 events', 'pending'),
        ('rec_3', 'Spring 2026', 'codecraft', 'Organize peer-led technical workshops where CodeCraft mentors other clubs on hackathon engagement.', 'rank = 1, composite = 94.2', 'approved')
    """)

    # Seed reference documents for RAG
    seed_rag_documents(cursor)

    conn.commit()
    conn.close()

def seed_rag_documents(cursor):
    """Seeds institutional knowledge and evaluation policies for RAG retrieval."""
    docs = [
        {
            "id": "policy_eval_criteria",
            "doc_type": "policy",
            "title": "Spring 2026 Student Club Performance Evaluation Framework",
            "content": (
                "Official Evaluation Weights for Spring 2026 Technical Clubs: "
                "1. Attendance Rate carries 30% weight, measuring participant turnout relative to registrations. "
                "2. Participant Feedback Score carries 30% weight, evaluated on a 1.0 to 5.0 Likert scale. "
                "3. Speaker & Mentor Rating carries 15% weight, measuring guest quality. "
                "4. Attendance Consistency carries 15% weight, measured as the inverse standard deviation of attendance rates across events. "
                "5. Event Frequency carries 10% weight, rewarding continuous academic engagement. "
                "Formula: Composite Score = sum(Normalized_Metric * Weight). Clubs with incomplete attendance must have missing records imputed via the club's average known turnout ratio."
            ),
            "metadata": {"year": 2026, "type": "evaluation_rubric"}
        },
        {
            "id": "policy_data_integrity",
            "doc_type": "policy",
            "title": "Campus Data Governance and Event Verification Standard",
            "content": (
                "Data Quality Standard: Event attendance records must be finalized within 48 hours of event completion. "
                "If unrecorded, the event is marked 'Imputed' and an attendance rate equal to the club's recorded events mean is applied. "
                "Imputed records must never be disguised as observed empirical attendance in jury presentations. "
                "Digital QR scanning or university card swipe is mandatory starting Fall 2026."
            ),
            "metadata": {"governance": "academic_affairs"}
        },
        {
            "id": "historical_archive_policy",
            "doc_type": "report",
            "title": "Semester Performance Archive Policy",
            "content": (
                "Historical Archive Registry: Spring 2026 is the baseline semester for the automated EventIQ Agent. "
                "Previous semester records (Fall 2025 and earlier) were managed via paper registries and have not yet been digitized into SQLite. "
                "When queried about previous semesters, the agent must inform the user that prior digital records are unavailable rather than fabricating metrics."
            ),
            "metadata": {"archive": "status"}
        }
    ]

    for d in docs:
        cursor.execute("""
            INSERT OR REPLACE INTO documents (id, doc_type, title, content, metadata_json)
            VALUES (?, ?, ?, ?, ?)
        """, (d["id"], d["doc_type"], d["title"], d["content"], json.dumps(d["metadata"])))
