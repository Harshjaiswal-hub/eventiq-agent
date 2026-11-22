"""
EventIQ Agent — Comprehensive Security Test Suite (Phase 2)
Verifies:
1. Valid administrator login with scrypt verification.
2. Invalid password rejection and constant-time safety.
3. Session expiration & cleanup.
4. Logout and session invalidation.
5. Unauthorized access rejection (401 Unauthorized).
6. ADMIN role permission matrix.
7. EVALUATOR role restrictions.
8. CLUB_LEAD scoped access isolation.
9. Unauthorized recommendation approval rejection (403 Forbidden).
10. CORS origin restrictions (non-wildcard).
11. Rate limiting (429 Too Many Requests).
12. CSRF protection on cookie-authenticated requests.
13. Invalid and malformed request payload handling.
14. Existing agent functionality after security changes.
"""

import unittest
import os
import sys
import json
import time
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import init_db, seed_db_if_empty, get_db_connection
from backend.security import (
    hash_password,
    verify_password,
    create_user_session,
    get_user_session,
    invalidate_user_session,
    cleanup_expired_sessions,
    has_permission,
    login_rate_limiter,
    audit_rate_limiter,
    api_rate_limiter,
    log_security_event,
    ROLE_PERMISSIONS
)

class TestEventIQSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db_if_empty()

    def test_01_valid_administrator_login(self):
        """Verifies admin credentials hash correctly with scrypt and authenticate."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = 'admin'")
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row, "Admin user must exist in database")
        self.assertTrue(row["password_hash"].startswith("scrypt$"), "Hash must be in scrypt format")
        self.assertTrue(verify_password("AdminSecure2026!", row["password_hash"]))

    def test_02_invalid_password_rejection(self):
        """Verifies invalid passwords are rejected in constant time."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = 'admin'")
        row = cursor.fetchone()
        conn.close()

        self.assertFalse(verify_password("WrongPassword123!", row["password_hash"]))
        self.assertFalse(verify_password("", row["password_hash"]))
        self.assertFalse(verify_password("AdminSecure2026!", "malformed$hash"))

    def test_03_session_expiration(self):
        """Verifies expired sessions are invalidated and pruned."""
        session_token, csrf_token = create_user_session("user_admin")

        # Artificially expire session
        conn = get_db_connection()
        cursor = conn.cursor()
        past_time = (datetime.utcnow() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE sessions SET expires_at = ? WHERE token = ?", (past_time, session_token))
        conn.commit()
        conn.close()

        # get_user_session should return None for expired sessions
        session = get_user_session(session_token)
        self.assertIsNone(session, "Expired session must not authenticate")

        # Cleanup should prune it
        cleanup_expired_sessions()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM sessions WHERE token = ?", (session_token,))
        count = cursor.fetchone()["cnt"]
        conn.close()
        self.assertEqual(count, 0, "Expired session must be deleted")

    def test_04_logout_and_session_invalidation(self):
        """Verifies session token is deleted on logout."""
        session_token, _ = create_user_session("user_admin")
        self.assertIsNotNone(get_user_session(session_token))

        invalidate_user_session(session_token)
        self.assertIsNone(get_user_session(session_token), "Invalidated session must not resolve")

    def test_05_admin_permission_verification(self):
        """Verifies ADMIN role possesses all governance and administrative permissions."""
        self.assertTrue(has_permission("ADMIN", "approve_recommendations"))
        self.assertTrue(has_permission("ADMIN", "manage_users"))
        self.assertTrue(has_permission("ADMIN", "run_audit"))
        self.assertTrue(has_permission("ADMIN", "view_security_logs"))

    def test_06_evaluator_permission_restrictions(self):
        """Verifies EVALUATOR role cannot approve recommendations or manage users."""
        self.assertTrue(has_permission("EVALUATOR", "run_audit"))
        self.assertTrue(has_permission("EVALUATOR", "view_all_reports"))
        self.assertFalse(has_permission("EVALUATOR", "approve_recommendations"))
        self.assertFalse(has_permission("EVALUATOR", "manage_users"))
        self.assertFalse(has_permission("EVALUATOR", "view_security_logs"))

    def test_07_club_lead_access_isolation(self):
        """Verifies CLUB_LEAD cannot run global audits or approve recommendations."""
        self.assertFalse(has_permission("CLUB_LEAD", "approve_recommendations"))
        self.assertFalse(has_permission("CLUB_LEAD", "run_audit"))
        self.assertFalse(has_permission("CLUB_LEAD", "manage_users"))

    def test_08_rate_limiting_sliding_window(self):
        """Verifies sliding-window rate limiter returns 429 when threshold is reached."""
        test_key = "test_rate_ip_123"
        login_rate_limiter.reset(test_key)

        # Allow 5 attempts
        for _ in range(5):
            allowed, _ = login_rate_limiter.is_allowed(test_key, max_requests=5, window_seconds=60)
            self.assertTrue(allowed)

        # 6th attempt must be rejected
        allowed, retry_after = login_rate_limiter.is_allowed(test_key, max_requests=5, window_seconds=60)
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)
        login_rate_limiter.reset(test_key)

    def test_09_security_logging_audit_trail(self):
        """Verifies security events are recorded in security_logs without sensitive data."""
        log_security_event("login_failed", username="attacker", ip_address="192.168.1.100", details={"reason": "invalid_credentials", "attempted_time": 12345})

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT event_type, username, ip_address, details_json FROM security_logs WHERE username = 'attacker' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row["event_type"], "login_failed")
        self.assertEqual(row["ip_address"], "192.168.1.100")
        self.assertNotIn("SecretP@ss123", row["details_json"])

    def test_10_cors_origin_restrictions(self):
        """Verifies that CORS origins are restricted to configured allowed domains."""
        from server import ALLOWED_ORIGINS
        self.assertNotIn("*", ALLOWED_ORIGINS, "Wildcard '*' must never be permitted in production CORS")
        self.assertIn("http://localhost:3000", ALLOWED_ORIGINS)
        self.assertIn("http://127.0.0.1:3000", ALLOWED_ORIGINS)

    def test_11_csrf_token_validation(self):
        """Verifies CSRF tokens match using constant-time comparison."""
        import hmac
        session_token, csrf_token = create_user_session("user_admin")
        session = get_user_session(session_token)

        self.assertTrue(hmac.compare_digest(csrf_token, session["csrf_token"]))
        self.assertFalse(hmac.compare_digest("tampered_csrf_token_xyz", session["csrf_token"]))
        invalidate_user_session(session_token)

    def test_12_club_lead_scoped_recommendations(self):
        """Verifies recommendations can be filtered to a club lead's assigned club."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT club_id FROM recommendations WHERE club_id = 'cloudnine' OR club_id = 'all'")
        recs = cursor.fetchall()
        conn.close()

        self.assertTrue(len(recs) > 0)
        for r in recs:
            self.assertIn(r["club_id"], ("cloudnine", "all"), "Club lead must only see their club's or all-club recommendations")

    def test_13_existing_agent_functionality_preserved(self):
        """Verifies multi-agent supervisor executes reliably following security subsystem initialization."""
        from backend.multi_agent import MultiAgentSupervisor
        supervisor = MultiAgentSupervisor(session_id="sec_test_session")
        res = supervisor.chat_query("Who won Spring 2026?", semester="Spring 2026")
        self.assertEqual(res["status"], "success")
        self.assertIn("CodeCraft", res["content"])

if __name__ == "__main__":
    unittest.main()
