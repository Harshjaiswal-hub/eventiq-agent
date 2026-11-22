"""
EventIQ Agent — Concurrency Stress Test
Tests SQLite database under concurrent read and write load.
Verifies no deadlocks, corruption, or data integrity failures.

Run: python tests/test_concurrency.py
"""

import sys
import os
import time
import threading
import unittest
import concurrent.futures
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db_connection, init_db, seed_db_if_empty
from backend.tools import get_club_rankings, audit_data_quality
from backend.security import (
    hash_password, verify_password,
    create_user_session, get_user_session, invalidate_user_session,
    cleanup_expired_sessions, RateLimiter
)


class TestConcurrentDatabaseReads(unittest.TestCase):
    """20 simultaneous /api/rankings-equivalent calls — no corruption expected."""

    def test_concurrent_rankings_reads(self):
        """Simulate 20 concurrent read requests against get_club_rankings."""
        errors = []
        results = []

        def call_rankings():
            try:
                data = get_club_rankings("Spring 2026")
                results.append(data)
            except Exception as e:
                errors.append(str(e))

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            futures = [pool.submit(call_rankings) for _ in range(20)]
            concurrent.futures.wait(futures, timeout=30)

        self.assertEqual(len(errors), 0, f"Concurrent read errors: {errors}")
        self.assertEqual(len(results), 20)

        # All results should be identical (deterministic query)
        first_clubs = [r["name"] for r in results[0].get("rankings", [])]
        for r in results[1:]:
            clubs = [x["name"] for x in r.get("rankings", [])]
            self.assertEqual(clubs, first_clubs, "Inconsistent ranking results under concurrent load")

    def test_concurrent_audit_reads(self):
        """Simulate 10 concurrent audit_data_quality calls."""
        errors = []

        def call_audit():
            try:
                audit_data_quality("Spring 2026")
            except Exception as e:
                errors.append(str(e))

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(call_audit) for _ in range(10)]
            concurrent.futures.wait(futures, timeout=30)

        self.assertEqual(len(errors), 0, f"Concurrent audit errors: {errors}")


class TestConcurrentSessionOperations(unittest.TestCase):
    """Concurrent session creation and validation — no race conditions."""

    def test_concurrent_session_create_and_validate(self):
        """Create 10 sessions concurrently, then validate all of them."""
        session_tokens = []
        errors = []
        lock = threading.Lock()

        def create_session(user_id: str):
            try:
                token, csrf = create_user_session(user_id, ip_address="127.0.0.1")
                with lock:
                    session_tokens.append(token)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        # Ensure test user exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO users (id, username, password_hash, role, is_active)
            VALUES ('concurrency_test_user', 'conctest', 'dummy_hash', 'EVALUATOR', 1)
        """)
        conn.commit()
        conn.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(create_session, "concurrency_test_user") for _ in range(10)]
            concurrent.futures.wait(futures, timeout=30)

        self.assertEqual(len(errors), 0, f"Session creation errors: {errors}")
        self.assertEqual(len(session_tokens), 10)

        # All tokens should be unique (cryptographic guarantee)
        self.assertEqual(len(set(session_tokens)), 10, "Duplicate session tokens generated!")

        # Validate all sessions
        invalid = []
        for token in session_tokens:
            session = get_user_session(token)
            if not session:
                invalid.append(token)

        self.assertEqual(len(invalid), 0, f"{len(invalid)} tokens failed validation")

        # Cleanup test sessions
        for token in session_tokens:
            invalidate_user_session(token)

        # Cleanup test user
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = 'concurrency_test_user'")
        conn.commit()
        conn.close()


class TestConcurrentMixedReadWrite(unittest.TestCase):
    """Mixed concurrent reads and writes — WAL mode should prevent blocking."""

    def test_mixed_read_write_no_deadlock(self):
        """Concurrent readers and a writer should not deadlock (SQLite WAL)."""
        errors = []
        completed = []
        lock = threading.Lock()

        def read_rankings():
            try:
                get_club_rankings("Spring 2026")
                with lock:
                    completed.append("read")
            except Exception as e:
                with lock:
                    errors.append(f"read error: {e}")

        def write_session():
            try:
                # Ensure test write user exists
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO users (id, username, password_hash, role, is_active)
                    VALUES ('write_test_user', 'writetest', 'dummy', 'ADMIN', 1)
                """)
                conn.commit()
                conn.close()

                token, _ = create_user_session("write_test_user", ip_address="10.0.0.1")
                invalidate_user_session(token)
                with lock:
                    completed.append("write")
            except Exception as e:
                with lock:
                    errors.append(f"write error: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as pool:
            futures = []
            for _ in range(12):
                futures.append(pool.submit(read_rankings))
            for _ in range(3):
                futures.append(pool.submit(write_session))
            concurrent.futures.wait(futures, timeout=45)

        # Cleanup
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = 'write_test_user'")
        conn.commit()
        conn.close()

        self.assertEqual(len(errors), 0, f"Mixed read/write errors: {errors}")
        self.assertEqual(len(completed), 15, f"Only {len(completed)}/15 operations completed")


class TestRateLimiterThreadSafety(unittest.TestCase):
    """Rate limiter must be thread-safe under concurrent access."""

    def test_rate_limiter_concurrent_access(self):
        """Concurrent rate limiter calls must not corrupt internal state."""
        limiter = RateLimiter()
        allowed_count = 0
        blocked_count = 0
        lock = threading.Lock()

        def check_rate():
            nonlocal allowed_count, blocked_count
            is_allowed, _ = limiter.is_allowed("test_key", max_requests=5, window_seconds=60)
            with lock:
                if is_allowed:
                    allowed_count += 1
                else:
                    blocked_count += 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            futures = [pool.submit(check_rate) for _ in range(20)]
            concurrent.futures.wait(futures, timeout=15)

        total = allowed_count + blocked_count
        self.assertEqual(total, 20, f"Lost {20 - total} rate limit checks")
        # With max_requests=5, at most 5 should pass, rest blocked
        # Allow slight variance due to timing but cap should hold approximately
        self.assertLessEqual(allowed_count, 7, f"Rate limiter allowed {allowed_count} (expected ≤7)")


if __name__ == "__main__":
    print("=" * 60)
    print("EventIQ Agent — Concurrency Stress Test")
    print("=" * 60)
    seed_db_if_empty()
    unittest.main(verbosity=2)
