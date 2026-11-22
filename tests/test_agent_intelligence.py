"""
EventIQ Agent — Comprehensive Multi-Agent Intelligence Test Suite
Evaluates natural language question answering across all operational domains:
1. General Platform Knowledge & Rubrics
2. Institutional Rankings & Top/Bottom Performers
3. Detailed Club Deep-Dives & XAI Attribution
4. Head-to-Head Comparative Analytics
5. Campus-Wide Attendance & Turnout Metrics
6. Campus-Wide Feedback & Satisfaction Ratings
7. Event Portfolio & Format Breakdown (Workshops vs Hackathons)
8. Data Quality Governance & Imputation Audit
9. What-If Counterfactual Simulations
10. Predictive Attendance Forecasting
11. Event Execution Planning & Budget Optimization
12. Multi-Turn Conversational Memory & Pronoun Resolution ('it', 'why', 'improve')
13. Out-of-Domain Graceful Scope Handling
"""

import unittest
from backend.database import init_db, seed_db_if_empty
from backend.multi_agent import MultiAgentSupervisor


class TestAgentIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db_if_empty()

    def setUp(self):
        self.supervisor = MultiAgentSupervisor(session_id=f"test_intel_{self._testMethodName}")

    def test_01_general_platform_overview(self):
        """Tests general platform overview question: 'What is EventIQ?'"""
        res = self.supervisor.chat_query("What is EventIQ?")
        self.assertEqual(res["status"], "success")
        self.assertIn("Scoring Methodology", res["content"])
        self.assertEqual(res["agent_used"], "knowledge_agent")
        self.assertGreaterEqual(len(res["next_prompts"]), 2)

    def test_02_scoring_methodology_and_rubric(self):
        """Tests methodology query: 'How does the scoring methodology work?'"""
        res = self.supervisor.chat_query("How does the scoring methodology work?")
        self.assertEqual(res["status"], "success")
        self.assertIn("Attendance Rate", res["content"])
        self.assertIn("30%", res["content"])
        self.assertIn("Student Feedback", res["content"])
        self.assertEqual(res["agent_used"], "knowledge_agent")

    def test_03_institutional_rankings_winner(self):
        """Tests top performer query: 'Who performed best this semester?'"""
        res = self.supervisor.chat_query("Who performed best this semester?")
        self.assertEqual(res["status"], "success")
        self.assertIn("CodeCraft", res["content"])
        self.assertIn("#1", res["content"])
        self.assertEqual(res["agent_used"], "institutional_analytics_agent")

    def test_04_institutional_rankings_lowest(self):
        """Tests lowest performer query: 'Which club performed worst?'"""
        res = self.supervisor.chat_query("Which club performed worst?")
        self.assertEqual(res["status"], "success")
        self.assertIn("CloudNine", res["content"])
        self.assertIn("#6", res["content"])

    def test_05_club_deep_dive_profile(self):
        """Tests club deep-dive: 'Tell me everything about CodeCraft'"""
        res = self.supervisor.chat_query("Tell me everything about CodeCraft")
        self.assertEqual(res["status"], "success")
        self.assertIn("Complete Club Profile: CodeCraft", res["content"])
        self.assertIn("Explainable AI (XAI) Attribution", res["content"])
        self.assertIn("Primary Performance Driver", res["content"])
        self.assertEqual(res["agent_used"], "club_analysis_agent")

    def test_06_club_why_ranked(self):
        """Tests explainability query: 'Why is CloudNine ranked 6th?'"""
        res = self.supervisor.chat_query("Why is CloudNine ranked 6th?")
        self.assertEqual(res["status"], "success")
        self.assertIn("CloudNine", res["content"])
        self.assertIn("#6", res["content"])

    def test_07_head_to_head_comparison(self):
        """Tests comparison: 'Compare CodeCraft and DesignLab'"""
        res = self.supervisor.chat_query("Compare CodeCraft and DesignLab")
        self.assertEqual(res["status"], "success")
        self.assertIn("Head-to-Head Comparison: CodeCraft vs DesignLab", res["content"])
        self.assertIn("Delta", res["content"])
        self.assertEqual(res["agent_used"], "comparison_agent")

    def test_08_campus_wide_attendance_metrics(self):
        """Tests turnout metrics: 'What is the average attendance across campus?'"""
        res = self.supervisor.chat_query("What is the average attendance across campus?")
        self.assertEqual(res["status"], "success")
        self.assertIn("Overall Campus Attendance Rate", res["content"])
        self.assertIn("79.5%", res["content"])
        self.assertEqual(res["agent_used"], "institutional_analytics_agent")

    def test_09_campus_wide_feedback_metrics(self):
        """Tests satisfaction metrics: 'What is the overall student feedback rating?'"""
        res = self.supervisor.chat_query("What is the overall student feedback rating?")
        self.assertEqual(res["status"], "success")
        self.assertIn("Campus Average Feedback Score", res["content"])
        self.assertIn("4.27", res["content"])

    def test_10_events_catalog_highest_attendance(self):
        """Tests event query: 'Which event had the highest attendance?'"""
        res = self.supervisor.chat_query("Which event had the highest attendance?")
        self.assertEqual(res["status"], "success")
        self.assertIn("Hackathon 3.0", res["content"])
        self.assertEqual(res["agent_used"], "event_intelligence_agent")

    def test_11_event_format_comparison(self):
        """Tests format comparison: 'How do workshops compare to hackathons?'"""
        res = self.supervisor.chat_query("How do workshops compare to hackathons?")
        self.assertEqual(res["status"], "success")
        self.assertIn("Workshops vs Hackathons", res["content"])
        self.assertIn("Average Turnout Rate", res["content"])
        self.assertEqual(res["agent_used"], "event_intelligence_agent")

    def test_12_data_quality_and_imputation(self):
        """Tests data audit: 'Are there any data quality issues in our records?'"""
        res = self.supervisor.chat_query("Are there any data quality issues in our records?")
        self.assertEqual(res["status"], "success")
        self.assertIn("Data Governance & Quality Audit", res["content"])
        self.assertIn("Data Completeness Score", res["content"])
        self.assertIn("Statistical Imputation Protocol", res["content"])
        self.assertEqual(res["agent_used"], "data_quality_agent")

    def test_13_what_if_simulation(self):
        """Tests counterfactual simulation: 'What if CloudNine attendance increased by 10%?'"""
        res = self.supervisor.chat_query("What if CloudNine attendance increased by 10%?")
        self.assertEqual(res["status"], "success")
        self.assertIn("Counterfactual What-If Simulation", res["content"])
        self.assertIn("CloudNine", res["content"])
        self.assertIn("Simulated Value", res["content"])
        self.assertEqual(res["agent_used"], "simulation_agent")

    def test_14_predictive_attendance_forecast(self):
        """Tests forecasting: 'How many students are expected to attend CodeCraft's next hackathon?'"""
        res = self.supervisor.chat_query("How many students are expected to attend CodeCraft's next hackathon?")
        self.assertEqual(res["status"], "success")
        self.assertIn("Predictive Attendance Forecast", res["content"])
        self.assertIn("Expected Attendance", res["content"])
        self.assertIn("CodeCraft", res["content"])
        self.assertEqual(res["agent_used"], "predictive_agent")

    def test_15_event_planning_budget_optimizer(self):
        """Tests budget optimization: 'Plan a technical event for CodeCraft with a budget of ₹20,000'"""
        res = self.supervisor.chat_query("Plan a technical event for CodeCraft with a budget of ₹20,000")
        self.assertEqual(res["status"], "success")
        self.assertIn("Event Execution Plan & Budget Proposal", res["content"])
        self.assertIn("Budget Allocation", res["content"])
        self.assertIn("20,000", res["content"])
        self.assertEqual(res["agent_used"], "event_planner_agent")

    def test_16_conversational_pronoun_resolution_chain(self):
        """Tests multi-turn conversation memory with pronoun resolution chain."""
        chain_session = MultiAgentSupervisor(session_id="test_pronoun_chain_session")

        # Turn 1: Ask about lowest performing club
        t1 = chain_session.chat_query("Which club performed worst?")
        self.assertIn("CloudNine", t1["content"])

        # Turn 2: Follow-up pronoun question "Why?"
        t2 = chain_session.chat_query("Why?")
        self.assertIn("CloudNine", t2["content"])
        self.assertIn("Complete Club Profile: CloudNine", t2["content"])

        # Turn 3: Follow-up pronoun question "How can it improve?"
        t3 = chain_session.chat_query("How can it improve?")
        self.assertIn("CloudNine", t3["content"])
        self.assertIn("Recommendations & Improvement Roadmap", t3["content"])

        # Turn 4: Compare pronoun "it" with another club
        t4 = chain_session.chat_query("Compare it with CyberShield")
        self.assertIn("CloudNine vs CyberShield", t4["content"])

    def test_17_out_of_domain_graceful_handling(self):
        """Tests graceful boundary enforcement on out-of-domain query."""
        res = self.supervisor.chat_query("What is the capital of France?")
        self.assertEqual(res["status"], "success")
        self.assertIn("Welcome to EventIQ Intelligent Analytics", res["content"])
        self.assertEqual(res["agent_used"], "general_assistant")


if __name__ == "__main__":
    unittest.main(verbosity=2)
