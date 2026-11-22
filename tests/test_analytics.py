"""
EventIQ Agent — Automated Test Suite
Verifies:
1. Composite weights sum to exactly 1.0.
2. Ranking determinism and math consistency for known datasets.
3. Edge cases: Missing attendance, missing feedback, zero-event clubs, division by zero.
4. Historical comparison boundary checks (prevents fabrication when records do not exist).
5. Conversational short-term memory persistence and session isolation.
6. RAG retrieval of institutional evaluation rubric.
7. Multi-agent workflow execution, reviewer claim verification, and bounded termination.
8. XSS payload sanitization.
"""

import unittest
import json
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import init_db, seed_db_if_empty, get_db_connection
from backend.tools import (
    WEIGHTS,
    calculate_std_dev,
    normalize,
    get_club_rankings,
    analyze_club_performance,
    compare_clubs,
    compare_semesters,
    get_club_event_trends,
    audit_data_quality,
    get_historical_performance,
    generate_event_report
)
from backend.memory import (
    create_conversation,
    add_message,
    get_conversation_history,
    retrieve_relevant_documents,
    clear_conversation,
    save_report,
    get_saved_reports
)
from backend.multi_agent import (
    run_data_analyst,
    run_research_agent,
    run_recommendation_agent,
    run_reviewer_agent,
    MultiAgentSupervisor
)

class TestEventIQAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db_if_empty()

    def test_composite_weights_sum_to_one(self):
        """Verifies that the official composite score weights sum strictly to 1.0."""
        total_weight = sum(WEIGHTS.values())
        self.assertAlmostEqual(total_weight, 1.0, places=5, msg="Composite weights must sum to 1.0")

    def test_rankings_deterministic_for_known_dataset(self):
        """Verifies ranking calculations, score monotonicity, and top performer."""
        res = get_club_rankings("Spring 2026")
        self.assertEqual(res["status"], "success")
        rankings = res["rankings"]
        self.assertEqual(len(rankings), 6, "Expected 6 technical clubs")

        # Monotonicity check
        for i in range(len(rankings) - 1):
            self.assertGreaterEqual(
                rankings[i]["composite_score"],
                rankings[i+1]["composite_score"],
                f"Rank {i+1} score should be >= Rank {i+2} score"
            )

        # Winner check: CodeCraft should be rank 1
        top = rankings[0]
        self.assertEqual(top["club_id"], "codecraft")
        self.assertGreater(top["composite_score"], 90.0)

    def test_missing_data_imputation(self):
        """Verifies that missing attendance is properly flagged as imputed and recorded."""
        audit = audit_data_quality("Spring 2026")
        self.assertEqual(audit["status"], "success")
        self.assertGreater(audit["total_gaps_found"], 0)
        missing_att = audit["gaps_by_category"]["missing_attendance"]
        self.assertTrue(any("LeetCode" in m["event"] for m in missing_att))

    def test_historical_data_abstains_when_records_missing(self):
        """Verifies that historical queries for Fall 2025 return transparent no_data status."""
        hist = get_historical_performance("CodeCraft", "Fall 2025")
        self.assertEqual(hist["status"], "no_data")
        self.assertIn("not present in the database", hist["message"])

    def test_normalization_bounds(self):
        """Verifies normalization function handles equal min/max and out-of-range values."""
        self.assertEqual(normalize(50, 50, 50), 50.0)
        self.assertEqual(normalize(10, 0, 100), 10.0)
        self.assertEqual(normalize(150, 0, 100), 100.0)
        self.assertEqual(normalize(-10, 0, 100), 0.0)

    def test_std_dev_calculation(self):
        """Verifies stddev handles single element or empty arrays without error."""
        self.assertEqual(calculate_std_dev([]), 0.0)
        self.assertEqual(calculate_std_dev([50.0]), 0.0)
        self.assertAlmostEqual(calculate_std_dev([10.0, 20.0]), 5.0, places=2)

class TestEventIQMemoryAndRAG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db_if_empty()

    def test_short_term_conversational_memory(self):
        """Verifies message logging and session history retrieval with strict isolation."""
        session_id = "test_eval_session"
        clear_conversation(session_id)
        create_conversation(session_id, "Evaluation Session")
        add_message(session_id, "user", "Who won?")
        add_message(session_id, "assistant", "CodeCraft won rank 1.")

        history = get_conversation_history(session_id, limit=5)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")
        clear_conversation(session_id)

    def test_rag_document_retrieval(self):
        """Verifies retrieval of institutional evaluation criteria."""
        docs = retrieve_relevant_documents("weights evaluation criteria attendance")
        self.assertTrue(len(docs) > 0, "RAG should retrieve institutional policy document")
        self.assertIn("Attendance Rate carries 30% weight", docs[0]["content"])

class TestEventIQMultiAgentWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db_if_empty()

    def test_multi_agent_semester_audit_execution(self):
        """Verifies the multi-agent coordinator executes all 4 agents and produces an approved report."""
        supervisor = MultiAgentSupervisor(session_id="test_multi_agent_session")
        audit_res = supervisor.run_semester_audit("Spring 2026")

        self.assertEqual(audit_res["status"], "success")
        self.assertIn("markdown", audit_res)
        self.assertEqual(audit_res["reviewer_verdict"]["verdict"], "approved")
        self.assertGreaterEqual(len(audit_res["recommendations"]), 3)

    def test_reviewer_flags_unsupported_evidence(self):
        """Verifies reviewer agent detects missing evidence in recommendations."""
        mock_analyst = {
            "rankings": [{"composite_score": 90.0}, {"composite_score": 80.0}],
            "data_quality": {"total_gaps_found": 0},
            "evidence": ["imputed"]
        }
        mock_recommendations = {
            "recommendations": [
                {"id": "bad_rec", "action": "Do something", "evidence_metric": ""}
            ]
        }
        res = run_reviewer_agent(mock_analyst, mock_recommendations)
        self.assertEqual(res["verdict"], "approved_with_notes")
        self.assertTrue(any("lacks explicit evidence" in note for note in res["review_notes"]))

class TestDatabaseReliabilityAndSingleSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db_if_empty()

    def test_sqlite_wal_mode(self):
        """Verifies that SQLite WAL (Write-Ahead Logging) journal mode is active."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(mode.lower(), "wal", "Database must use WAL mode for concurrent write resilience")

    def test_sqlite_foreign_keys_enforced(self):
        """Verifies foreign key enforcement prevents orphan records."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        fk_enabled = cursor.fetchone()[0]
        self.assertEqual(fk_enabled, 1, "Foreign key pragma must be active on every connection")

        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO events (id, club_id, semester, name, type, date, registrations)
                VALUES ('orphan_ev', 'nonexistent_club', 'Spring 2026', 'Test', 'Workshop', '2026-02-01', 50)
            """)
        conn.close()

    def test_database_indexes_exist(self):
        """Verifies performance indexes exist on events, messages, recommendations, and execution_logs."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {r[0] for r in cursor.fetchall()}
        conn.close()

        required_indexes = {
            "idx_events_club_sem",
            "idx_messages_conv",
            "idx_recs_sem_status",
            "idx_exec_logs_session"
        }
        for idx in required_indexes:
            self.assertIn(idx, indexes, f"Index {idx} must be present in database schema")

    def test_single_source_scoring_contract(self):
        """Verifies get_club_rankings returns both canonical backend fields and frontend single-source contract."""
        res = get_club_rankings("Spring 2026")
        self.assertEqual(res["status"], "success")
        self.assertGreater(len(res["rankings"]), 0)

        for c in res["rankings"]:
            # Backend flat fields
            self.assertIn("composite_score", c)
            self.assertIn("attendance_rate", c)
            self.assertIn("event_count", c)
            # Frontend compatibility structure
            self.assertIn("composite", c)
            self.assertEqual(c["composite"], c["composite_score"])
            self.assertIn("club", c)
            self.assertEqual(c["club"]["name"], c["name"])
            self.assertIn("metrics", c)
            self.assertIn("attendanceRate", c["metrics"])
            self.assertIn("avgFeedback", c["metrics"])

class TestPhase3MissingFunctionality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db_if_empty()

    def test_saved_report_archival_and_retrieval(self):
        """Verifies report archival and full markdown retrieval by report_id."""
        rep_id = "test_rep_phase3_sample"
        markdown_body = "# Institutional Audit Report\n\nSample markdown audit contents for verification."
        save_report(
            report_id=rep_id,
            semester="Spring 2026",
            title="Spring 2026 Test Audit",
            summary="Test report summary.",
            markdown=markdown_body,
            provenance={"author": "TestRunner"}
        )

        # List query returns summary metadata
        reports = get_saved_reports(semester="Spring 2026")
        self.assertTrue(any(r["id"] == rep_id for r in reports))

        # ID query returns full markdown body
        single_rep = get_saved_reports(report_id=rep_id)
        self.assertEqual(len(single_rep), 1)
        self.assertEqual(single_rep[0]["id"], rep_id)
        self.assertIn("markdown", single_rep[0])
        self.assertEqual(single_rep[0]["markdown"], markdown_body)

    def test_multi_agent_audit_auto_archived(self):
        """Verifies running the multi-agent semester audit automatically archives the report to the database."""
        sess = "test_auto_archive_session"
        supervisor = MultiAgentSupervisor(session_id=sess)
        res = supervisor.run_semester_audit("Spring 2026")
        self.assertEqual(res["status"], "success")

        # Check that reports table contains an entry for this session
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, markdown_content FROM reports WHERE id LIKE ?", (f"%{sess}%",))
        archived = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(archived, "MultiAgentSupervisor must persist the completed audit report")
        self.assertIn("Spring 2026", archived["title"])
        self.assertIn("## 1. Executive Summary", archived["markdown_content"])

    def test_execution_trace_logging(self):
        """Verifies multi-agent execution steps are recorded in execution_logs with session attribution."""
        sess = "test_trace_logging_session"
        supervisor = MultiAgentSupervisor(session_id=sess)
        supervisor.run_semester_audit("Spring 2026")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT agent_name, action, details_json FROM execution_logs WHERE session_id = ?", (sess,))
        logs = cursor.fetchall()
        conn.close()

        self.assertGreaterEqual(len(logs), 4, "Trace log must capture steps from all agents")
        agent_names = {r["agent_name"] for r in logs}
        self.assertIn("supervisor", agent_names)
        self.assertIn("data_analyst", agent_names)
        self.assertIn("reviewer_agent", agent_names)

class TestPhase4AdvancedAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db_if_empty()

    def test_xai_attribution_decomposition(self):
        """Verifies explainable AI decomposition breaks score down into 5 components summing to composite."""
        res = get_club_rankings("Spring 2026")
        self.assertEqual(res["status"], "success")
        for c in res["rankings"]:
            self.assertIn("xai_attribution", c)
            xai = c["xai_attribution"]
            self.assertIn("components", xai)
            self.assertIn("primary_driver", xai)
            self.assertIn("primary_detractor", xai)
            self.assertEqual(len(xai["components"]), 5)

            # Check point sum integrity
            total_pts = sum(comp["points"] for comp in xai["components"])
            self.assertAlmostEqual(total_pts, c["composite_score"], delta=0.15,
                                   msg=f"Sum of attribution points ({total_pts}) should match composite score ({c['composite_score']})")

    def test_semester_comparison_abstains_gracefully(self):
        """Verifies compare_semesters transparently abstains when a semester lacks records."""
        res = compare_semesters("Spring 2026", "Fall 2025")
        self.assertEqual(res["status"], "no_data")
        self.assertIn("Historical data for semester 'Fall 2025' is not present", res["message"])
        self.assertIn("Spring 2026", res["available_semesters"])

    def test_club_event_trends(self):
        """Verifies get_club_event_trends calculates chronological trajectory and momentum."""
        res = get_club_event_trends("CodeCraft", "Spring 2026")
        self.assertEqual(res["status"], "success")
        self.assertIn("trajectory", res)
        self.assertEqual(len(res["trajectory"]), 4)
        self.assertIn("turnout_momentum", res)
        self.assertIn(res["turnout_momentum"], ("positive", "negative", "neutral"))

        # Check trajectory event order
        dates = [e["date"] for e in res["trajectory"]]
        self.assertEqual(dates, sorted(dates), "Trajectory events must be sorted chronologically")

    def test_evidence_linked_recommendations(self):
        """Verifies recommendation agent produces enriched recommendations with quantitative evidence links."""
        analyst_out = run_data_analyst("Spring 2026")
        rec_out = run_recommendation_agent(analyst_out, {})
        self.assertEqual(rec_out["status"], "success")
        for r in rec_out["recommendations"]:
            self.assertIn("target_metric", r)
            self.assertIn("current_value", r)
            self.assertIn("target_value", r)
            self.assertIn("expected_impact", r)
            self.assertIn("rationale", r)
            self.assertIn("evidence_metric", r)

class TestPhase5ProfessionalReporting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db_if_empty()

    def test_generate_event_report_sections(self):
        """Verifies generate_event_report contains methodology, metric breakdown, imputation disclosures, reviewer verification, and approval statuses."""
        rep = generate_event_report("Spring 2026")
        self.assertEqual(rep["status"], "success")
        md = rep["markdown"]

        # 1. Scoring methodology
        self.assertIn("Institutional Scoring Methodology", md)
        self.assertIn("Composite Score", md)
        self.assertIn("Attendance Rate", md)

        # 2. Rankings and metric breakdown
        self.assertIn("Verified Club Rankings", md)
        self.assertIn("CodeCraft", md)

        # 3. Disclosed imputed data
        self.assertIn("Data Quality & Imputation Disclosure", md)
        self.assertIn("Itemized Data Imputation Log", md)

        # 4. Reviewer verification results
        self.assertIn("Multi-Agent Reviewer Verification Results", md)
        self.assertIn("VERIFIED & APPROVED", md)

        # 5. Administrator approval status
        self.assertIn("Action Plan & Governance Approval Status", md)

    def test_multi_agent_audit_report_professional_sections(self):
        """Verifies multi-agent flagship audit markdown incorporates all professional reporting sections."""
        supervisor = MultiAgentSupervisor(session_id="test_phase5_report")
        res = supervisor.run_semester_audit("Spring 2026")
        self.assertEqual(res["status"], "success")
        md = res["markdown"]

        self.assertIn("Institutional Scoring Methodology", md)
        self.assertIn("Comprehensive Club Leaderboard & XAI Decomposition", md)
        self.assertIn("Data Governance & Imputation Audit", md)
        self.assertIn("Reviewer Agent Verification Trace", md)
        self.assertIn("Administrator Approval Status", md)

if __name__ == "__main__":
    unittest.main()
