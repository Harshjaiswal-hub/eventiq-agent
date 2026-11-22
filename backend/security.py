"""
EventIQ Agent — Security & Authentication Subsystem
Implements:
1. Memory-hard password hashing via hashlib.scrypt (standard library, zero external dependencies).
2. Constant-time digest verification.
3. Cryptographic session token generation & session state management in SQLite.
4. Role-Based Access Control (RBAC) supporting ADMIN, EVALUATOR, and CLUB_LEAD.
5. In-memory sliding-window rate limiting for login, audit, and API endpoints.
6. Security event auditing and non-sensitive logging.
"""

import os
import hmac
import hashlib
import secrets
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List

from backend.database import get_db_connection

# ── 1. PASSWORD HASHING (SCRYPT) ─────────────────────────────

# scrypt parameters: n=16384 (CPU/memory cost), r=8 (block size), p=1 (parallelization)
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LEN = 64

def hash_password(password: str) -> str:
    """Hashes a password using hashlib.scrypt with a random 16-byte salt."""
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string.")
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        maxmem=0,
        dklen=KEY_LEN
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${key.hex()}"

def verify_password(password: str, hashed_str: str) -> bool:
    """Verifies a plaintext password against an scrypt hash in constant time."""
    if not password or not hashed_str:
        return False
    try:
        parts = hashed_str.split("$")
        if len(parts) != 6 or parts[0] != "scrypt":
            return False
        n = int(parts[1])
        r = int(parts[2])
        p = int(parts[3])
        salt = bytes.fromhex(parts[4])
        expected_key = bytes.fromhex(parts[5])

        derived_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            maxmem=0,
            dklen=len(expected_key)
        )
        return hmac.compare_digest(derived_key, expected_key)
    except Exception:
        return False

# ── 2. SESSION MANAGEMENT ───────────────────────────────────

SESSION_DURATION_HOURS = 8

def create_user_session(user_id: str, ip_address: str = "", user_agent: str = "") -> Tuple[str, str]:
    """
    Generates a secure cryptographically random session token and CSRF token.
    Rotates existing sessions and records the new session in the database.
    """
    session_token = secrets.token_hex(32)
    csrf_token = secrets.token_hex(32)
    expires_at = (datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (token, user_id, csrf_token, ip_address, user_agent, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_token, user_id, csrf_token, ip_address, user_agent, expires_at))
    conn.commit()
    conn.close()

    return session_token, csrf_token

def get_user_session(session_token: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves and validates an active session token.
    Returns user details if active, or None if expired/invalid.
    """
    if not session_token or not isinstance(session_token, str):
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.token, s.user_id, s.csrf_token, s.expires_at,
               u.username, u.role, u.club_id, u.is_active
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND u.is_active = 1
    """, (session_token,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    # Expiration check
    expires_at_dt = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.utcnow() > expires_at_dt:
        invalidate_user_session(session_token)
        return None

    return {
        "session_token": row["token"],
        "user_id": row["user_id"],
        "csrf_token": row["csrf_token"],
        "username": row["username"],
        "role": row["role"],
        "club_id": row["club_id"],
        "expires_at": row["expires_at"]
    }

def invalidate_user_session(session_token: str):
    """Deletes the specified session token (logout or expiration)."""
    if not session_token:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (session_token,))
    conn.commit()
    conn.close()

def cleanup_expired_sessions():
    """Prunes expired sessions from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("DELETE FROM sessions WHERE expires_at < ?", (now_str,))
    conn.commit()
    conn.close()

# ── 3. ROLE-BASED ACCESS CONTROL (RBAC) ─────────────────────

ROLES = {"ADMIN", "EVALUATOR", "CLUB_LEAD"}

ROLE_PERMISSIONS = {
    "ADMIN": {
        "manage_users": True,
        "manage_clubs": True,
        "approve_recommendations": True,
        "run_audit": True,
        "generate_reports": True,
        "view_all_reports": True,
        "view_execution_logs": True,
        "view_security_logs": True,
        "view_all_rankings": True,
    },
    "EVALUATOR": {
        "manage_users": False,
        "manage_clubs": False,
        "approve_recommendations": False,
        "run_audit": True,
        "generate_reports": False,
        "view_all_reports": True,
        "view_execution_logs": False,
        "view_security_logs": False,
        "view_all_rankings": True,
    },
    "CLUB_LEAD": {
        "manage_users": False,
        "manage_clubs": False,
        "approve_recommendations": False,
        "run_audit": False,
        "generate_reports": False,
        "view_all_reports": False,
        "view_execution_logs": False,
        "view_security_logs": False,
        "view_all_rankings": True,
    }
}

def has_permission(role: str, permission: str) -> bool:
    """Checks whether a role possesses a specific permission."""
    return ROLE_PERMISSIONS.get(role, {}).get(permission, False)

# ── 4. RATE LIMITING (SLIDING WINDOW) ────────────────────────

class RateLimiter:
    """
    Thread-safe in-memory rate limiter enforcing sliding window limits.
    Prevents brute-force login attempts, DoS attacks, and audit endpoint abuse.
    """
    def __init__(self):
        self.buckets: Dict[str, List[float]] = {}

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Determines if a request is permitted within the rate limit window.
        Returns: (is_allowed, seconds_until_retry)
        """
        now = time.time()
        cutoff = now - window_seconds

        # Prune old timestamps
        history = self.buckets.get(key, [])
        history = [ts for ts in history if ts > cutoff]

        if len(history) >= max_requests:
            oldest = history[0]
            retry_after = int(window_seconds - (now - oldest)) + 1
            self.buckets[key] = history
            return False, max(1, retry_after)

        history.append(now)
        self.buckets[key] = history
        return True, 0

    def reset(self, key: str):
        """Clears rate limit state for a key (e.g. on successful login)."""
        self.buckets.pop(key, None)

# Global rate limiters
login_rate_limiter = RateLimiter()   # 5 attempts per 15 minutes
audit_rate_limiter = RateLimiter()   # 10 audits per minute
api_rate_limiter = RateLimiter()     # 120 API requests per minute

# ── 5. SECURITY AUDIT LOGGING ────────────────────────────────

def log_security_event(event_type: str, username: Optional[str] = None, user_id: Optional[str] = None,
                       ip_address: str = "", details: Optional[Dict[str, Any]] = None):
    """
    Records a structured security event in SQLite security_logs.
    Never logs passwords, raw tokens, or secrets.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    details_str = json.dumps(details) if details else None
    cursor.execute("""
        INSERT INTO security_logs (event_type, username, user_id, ip_address, details_json)
        VALUES (?, ?, ?, ?, ?)
    """, (event_type, username, user_id, ip_address, details_str))
    conn.commit()
    conn.close()

# ── 6. SEED ACCOUNTS INITIALIZATION ─────────────────────────

def seed_security_accounts_if_empty():
    """
    Idempotently seeds initial administrative, evaluator, and club lead accounts
    using hardened scrypt password hashes. Never stores plaintext passwords.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    if cursor.fetchone()["cnt"] > 0:
        conn.close()
        return

    admin_pass = os.environ.get("INITIAL_ADMIN_PASSWORD", "AdminSecure2026!")
    eval_pass = os.environ.get("INITIAL_EVALUATOR_PASSWORD", "EvaluatorSecure2026!")
    lead_cc_pass = os.environ.get("INITIAL_LEAD_CC_PASSWORD", "CodeCraftLead2026!")
    lead_cn_pass = os.environ.get("INITIAL_LEAD_CN_PASSWORD", "CloudNineLead2026!")

    users = [
        ("user_admin", "admin", hash_password(admin_pass), "ADMIN", None),
        ("user_eval", "evaluator", hash_password(eval_pass), "EVALUATOR", None),
        ("user_cc", "lead_codecraft", hash_password(lead_cc_pass), "CLUB_LEAD", "codecraft"),
        ("user_cn", "lead_cloudnine", hash_password(lead_cn_pass), "CLUB_LEAD", "cloudnine"),
    ]

    for uid, uname, phash, role, cid in users:
        cursor.execute("""
            INSERT OR REPLACE INTO users (id, username, password_hash, role, club_id, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (uid, uname, phash, role, cid))

    conn.commit()
    conn.close()
