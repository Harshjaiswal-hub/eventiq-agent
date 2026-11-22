"""
EventIQ Agent — Unit Tests for Predictive Intelligence & Event Planning Optimizer
Tests:
1. Attendance forecasting baseline, small-sample bounds, and confidence limitations.
2. Refusal to forecast when insufficient historical data exists (<2 events).
3. Exact historical event attribution / influencing events breakdown.
4. Intelligent event planning with budget constraints and category allocations.
5. Evidence-conditioned speaker recommendations (only when past rating >= 4.5).
6. Supervisor intent routing for natural language predictive and planning queries.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db_connection, init_db, seed_db_if_empty
from backend.tools import predict_event_attendance, optimize_event_plan
from backend.multi_agent import MultiAgentSupervisor


class TestPredictiveEventIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db_if_empty()

    def test_predict_codecraft_hackathon(self):
        """Tests attendance prediction for CodeCraft hackathon with range and influencing events."""
        res = predict_event_attendance("CodeCraft", event_type="hackathon", semester="Spring 2026")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["club"], "CodeCraft")

        forecast = res["forecast"]
        self.assertGreater(forecast["expected_attendance"], 100)
        self.assertGreater(forecast["expected_registrations"], 120)
        self.assertLessEqual(forecast["expected_attendance"], forecast["expected_registrations"])

        # Check range bounds
        att_range = forecast["attendance_range"]
        self.assertEqual(len(att_range), 2)
        self.assertLessEqual(att_range[0], forecast["expected_attendance"])
        self.assertGreaterEqual(att_range[1], forecast["expected_attendance"])

        # Check influencing events
        influencers = res["influencing_events"]
        self.assertGreaterEqual(len(influencers), 3)
        hackathon_event = next((e for e in influencers if "hackathon" in e["type"].lower() or "hackathon" in e["name"].lower()), None)
        self.assertIsNotNone(hackathon_event, "Historical hackathon event must be among influencing events")
        self.assertTrue(hackathon_event["format_match"])

        # Check small-sample limitations disclosure
        self.assertIn("limitations", res)
        self.assertTrue(any("N=" in lit for lit in res["limitations"]))

    def test_predict_refuses_on_insufficient_data(self):
        """Verifies system explicitly refuses to forecast when less than 2 events exist."""
        conn = get_db_connection()
        cursor = conn.cursor()
        # Create a club with only 1 event
        cursor.execute("INSERT OR REPLACE INTO clubs (id, name, tagline, color, icon) VALUES ('sparse_club', 'SparseClub', 'Low Data Club', '#111', '❓')")
        cursor.execute("DELETE FROM events WHERE club_id = 'sparse_club'")
        cursor.execute("""
            INSERT INTO events (id, club_id, semester, name, type, date, registrations, attendance, duration_hours, resources_used)
            VALUES ('sp1', 'sparse_club', 'Spring 2026', 'Solo Workshop', 'Workshop', '2026-02-01', 50, 40, 3, 200)
        """)
        conn.commit()
        conn.close()

        res = predict_event_attendance("SparseClub", semester="Spring 2026")
        self.assertEqual(res["status"], "insufficient_data")
        self.assertIn("Insufficient historical data", res["message"])

        # Cleanup
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM events WHERE club_id = 'sparse_club'")
        cursor.execute("DELETE FROM clubs WHERE id = 'sparse_club'")
        conn.commit()
        conn.close()

    def test_predict_unknown_club(self):
        """Verifies graceful error handling when club is not found."""
        res = predict_event_attendance("NonExistentClub12345", semester="Spring 2026")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error_code"], "CLUB_NOT_FOUND")


class TestIntelligentEventPlanningOptimizer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db_if_empty()

    def test_plan_codecraft_with_budget_20000(self):
        """Tests event planning for CodeCraft with ₹20,000 budget."""
        res = optimize_event_plan("CodeCraft", budget=20000.0, semester="Spring 2026")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["club"], "CodeCraft")
        self.assertEqual(res["budget"], 20000.0)

        # Budget allocations sum to total budget
        alloc = res["budget_allocation"]
        total_allocated = sum(item["amount"] for item in alloc.values())
        self.assertAlmostEqual(total_allocated, 20000.0, delta=100)

        # Key elements present
        self.assertIn("unit_economics", res)
        self.assertGreater(res["unit_economics"]["expected_attendance"], 50)
        self.assertGreater(res["duration_hours"], 0)
        self.assertGreater(len(res["required_resources"]), 3)
        self.assertGreater(len(res["improvements"]), 0)
        self.assertGreater(len(res["risks"]), 0)

        # Speaker strategy: CodeCraft has past speaker ratings 4.7, 4.9, 4.8 -> should recommend
        speaker_strat = res["speaker_strategy"]
        self.assertEqual(speaker_strat["status"], "recommended")

    def test_plan_cloudnine_speaker_caution(self):
        """Tests that CloudNine (which has lower/mixed speaker ratings) receives caution or withheld speaker advice."""
        res = optimize_event_plan("CloudNine", budget=10000.0, semester="Spring 2026")
        self.assertEqual(res["status"], "success")
        self.assertIn(res["speaker_strategy"]["status"], ("caution_peer_preferred", "withheld_insufficient_data"))

    def test_plan_invalid_budget(self):
        """Verifies rejection of negative or zero budget."""
        res = optimize_event_plan("CodeCraft", budget=-500)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error_code"], "INVALID_BUDGET")


class TestSupervisorIntentRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db_if_empty()

    def test_supervisor_predict_query_routing(self):
        """Tests conversational prediction query: 'How many students are expected to attend CodeCraft's next hackathon?'"""
        supervisor = MultiAgentSupervisor(session_id="test_predict_routing")
        response = supervisor.chat_query("How many students are expected to attend CodeCraft's next hackathon?", semester="Spring 2026")

        self.assertEqual(response["status"], "success")
        self.assertIn("Predictive Attendance Forecast", response["content"])
        self.assertIn("Expected Attendance", response["content"])
        self.assertIn("CodeCraft", response["content"])

        # Tool call recorded
        tool_names = [tc["tool"] for tc in response["tool_calls"]]
        self.assertIn("predict_event_attendance", tool_names)

    def test_supervisor_planning_query_routing(self):
        """Tests conversational planning query: 'Plan a technical event for CodeCraft with a budget of ₹20,000.'"""
        supervisor = MultiAgentSupervisor(session_id="test_plan_routing")
        response = supervisor.chat_query("Plan a technical event for CodeCraft with a budget of ₹20,000.", semester="Spring 2026")

        self.assertEqual(response["status"], "success")
        self.assertIn("Event Execution Plan & Budget Proposal", response["content"])
        self.assertIn("Budget Allocation", response["content"])
        self.assertIn("20,000", response["content"])

        # Tool call recorded
        tool_names = [tc["tool"] for tc in response["tool_calls"]]
        self.assertIn("optimize_event_plan", tool_names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
