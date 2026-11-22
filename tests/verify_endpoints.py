"""
Automated Verification Script for EventIQ Agent Endpoints & Subsystems
Simulates frontend requests, exercises all REST APIs, tests session isolation,
verifies recommendation decision transitions, tests authentication, RBAC, and checks error responses.
"""

import os
import urllib.request
import urllib.parse
import json
import sys
import time

PORT = int(os.environ.get("PORT", 3000))
BASE_URL = f"http://127.0.0.1:{PORT}"

def request_json(method, path, body=None, token=None, headers_extra=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if headers_extra:
        headers.update(headers_extra)

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            content = resp.read().decode("utf-8")
            try:
                return status, json.loads(content)
            except Exception:
                return status, content
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(content)
        except Exception:
            return e.code, content

def run_checks():
    print(f"[*] Testing EventIQ Agent endpoints at {BASE_URL}...")

    # 1. GET /api/health
    status, res = request_json("GET", "/api/health")
    assert status == 200, f"Health check failed with {status}"
    assert res.get("status") == "online", f"Unexpected health status: {res}"
    print("  [OK] GET /api/health passed.")

    # 2. Authentication: Administrator Login
    status, auth_res = request_json("POST", "/api/auth/login", {"username": "admin", "password": "AdminSecure2026!"})
    assert status == 200, f"Admin login failed: {auth_res}"
    admin_token = auth_res.get("session_token")
    admin_csrf = auth_res.get("csrf_token")
    assert admin_token is not None
    print(f"  [OK] POST /api/auth/login passed (Logged in as {auth_res['user']['username']}, role {auth_res['user']['role']}).")

    # 3. GET /api/auth/me
    status, me_res = request_json("GET", "/api/auth/me", token=admin_token)
    assert status == 200
    assert me_res["user"]["role"] == "ADMIN"
    print("  [OK] GET /api/auth/me passed (Verified ADMIN session).")

    # 4. GET /api/clubs
    status, res = request_json("GET", "/api/clubs")
    assert status == 200
    assert len(res.get("clubs", [])) == 6
    print("  [OK] GET /api/clubs passed (6 clubs verified).")

    # 5. GET /api/rankings
    status, res = request_json("GET", "/api/rankings?semester=Spring%202026")
    assert status == 200
    top = res["rankings"][0]
    assert top["club_id"] == "codecraft"
    print(f"  [OK] GET /api/rankings passed (Winner: {top['name']} score {top['composite_score']}).")

    # 6. GET /api/audit
    status, res = request_json("GET", "/api/audit?semester=Spring%202026")
    assert status == 200
    assert res["total_events_audited"] == 24
    print(f"  [OK] GET /api/audit passed (Audited {res['total_events_audited']} events).")

    # 7. POST /api/analytics/compare
    status, res = request_json("POST", "/api/analytics/compare", {"club_a": "CodeCraft", "club_b": "DesignLab", "semester": "Spring 2026"})
    assert status == 200
    assert "comparison" in res
    print(f"  [OK] POST /api/analytics/compare passed (Delta score: {res['comparison']['score_diff']}).")

    # 8. POST /api/agent/chat (Session 1 vs Session 2 Isolation)
    status, res1 = request_json("POST", "/api/agent/chat", {"message": "Who won?", "session_id": "tab_session_1", "semester": "Spring 2026"})
    assert status == 200
    assert "CodeCraft" in res1["content"]

    status, res2 = request_json("POST", "/api/agent/chat", {"message": "Tell me missing data", "session_id": "tab_session_2", "semester": "Spring 2026"})
    assert status == 200
    assert "Missing Attendance" in res2["content"]
    print("  [OK] POST /api/agent/chat passed with independent session contexts.")

    # 9. POST /api/agent/audit (Flagship Multi-Agent Audit - Requires ADMIN or EVALUATOR)
    status, res = request_json("POST", "/api/agent/audit", {"semester": "Spring 2026", "session_id": "test_audit_flow"}, token=admin_token)
    assert status == 200
    assert res["reviewer_verdict"]["verdict"] == "approved"
    print(f"  [OK] POST /api/agent/audit passed with admin authentication (Reviewer verdict: {res['reviewer_verdict']['verdict']}).")

    # 10. GET /api/recommendations
    status, res = request_json("GET", "/api/recommendations")
    assert status == 200
    recs = res["recommendations"]
    assert len(recs) >= 3
    print(f"  [OK] GET /api/recommendations passed ({len(recs)} recommendations loaded).")

    # 11. POST /api/recommendations/decision (Approve decision - Authenticated as ADMIN)
    test_rec_id = recs[0]["id"]
    status, res = request_json("POST", "/api/recommendations/decision", {"id": test_rec_id, "status": "approved", "comment": "Verified by automated test"}, token=admin_token)
    assert status == 200
    assert res["updated_status"] == "approved"
    print(f"  [OK] POST /api/recommendations/decision passed with ADMIN role (Updated {test_rec_id} to approved).")

    # 12. Security Test: Reject Unauthenticated Decision
    status, unauth_res = request_json("POST", "/api/recommendations/decision", {"id": test_rec_id, "status": "approved"})
    assert status == 401
    print("  [OK] Unauthenticated decision attempt rejected (401 Unauthorized).")

    # 13. Security Test: Reject Non-Admin Role (CLUB_LEAD)
    status, lead_auth = request_json("POST", "/api/auth/login", {"username": "lead_codecraft", "password": "CodeCraftLead2026!"})
    assert status == 200
    lead_token = lead_auth.get("session_token")
    status, forbid_res = request_json("POST", "/api/recommendations/decision", {"id": test_rec_id, "status": "rejected"}, token=lead_token)
    assert status == 403
    print("  [OK] CLUB_LEAD unauthorized recommendation decision rejected (403 Forbidden).")

    # 14. Error Handling: Invalid Status
    status, res = request_json("POST", "/api/recommendations/decision", {"id": test_rec_id, "status": "invalid_status"}, token=admin_token)
    assert status == 400
    print("  [OK] Invalid status rejection handled gracefully (400 Bad Request).")

    # 15. Error Handling: Unmatched Route
    status, res = request_json("GET", "/api/nonexistent_route")
    assert status == 404
    print("  [OK] Unmatched API route returned structured 404.")

    # 16. Static Assets (index.html, css/style.css, js/app.js)
    status, _ = request_json("GET", "/")
    assert status == 200
    status, _ = request_json("GET", "/css/style.css")
    assert status == 200
    status, _ = request_json("GET", "/js/app.js")
    assert status == 200
    print("  [OK] Static frontend files (HTML, CSS, JS) verified accessible.")

    # 17. Security Logout & Invalidation
    status, logout_res = request_json("POST", "/api/auth/logout", token=admin_token)
    assert status == 200
    status, me_after = request_json("GET", "/api/auth/me", token=admin_token)
    assert status == 401
    print("  [OK] POST /api/auth/logout invalidated session successfully.")

    # 18. Phase 3: GET /api/clubs with dynamic events payload
    status, res = request_json("GET", "/api/clubs?semester=Spring%202026")
    assert status == 200
    clubs = res.get("clubs", [])
    assert len(clubs) == 6
    assert "events" in clubs[0]
    assert len(clubs[0]["events"]) > 0
    assert "registrations" in clubs[0]["events"][0]
    print(f"  [OK] GET /api/clubs verified with dynamic database events ({len(clubs[0]['events'])} events in first club).")

    # 19. Phase 3: POST /api/reports/generate (Admin auth)
    # Re-login as admin
    status, auth_res = request_json("POST", "/api/auth/login", {"username": "admin", "password": "AdminSecure2026!"})
    assert status == 200
    admin_token_2 = auth_res["session_token"]
    status, gen_rep_res = request_json("POST", "/api/reports/generate", {"semester": "Spring 2026"}, token=admin_token_2)
    assert status == 200
    assert "markdown" in gen_rep_res
    print("  [OK] POST /api/reports/generate successfully generated and archived semester report.")

    # 20. Phase 3: GET /api/reports Archive (Listing & Full Content Retrieval)
    status, rep_list = request_json("GET", "/api/reports?semester=Spring%202026")
    assert status == 200
    reports = rep_list.get("reports", [])
    assert len(reports) > 0
    saved_rep_id = reports[0]["id"]

    status, single_rep = request_json("GET", f"/api/reports?id={saved_rep_id}")
    assert status == 200
    assert len(single_rep.get("reports", [])) == 1
    assert "markdown" in single_rep["reports"][0]
    assert len(single_rep["reports"][0]["markdown"]) > 50
    print(f"  [OK] GET /api/reports archive verified (Retrieved full content for {saved_rep_id}).")

    # 21. Phase 3: GET /api/logs/execution Trace Inspection
    status, trace_res = request_json("GET", "/api/logs/execution?session_id=test_audit_flow", token=admin_token_2)
    assert status == 200
    logs = trace_res.get("logs", [])
    assert len(logs) > 0
    assert "agent_name" in logs[0]
    print(f"  [OK] GET /api/logs/execution verified ({len(logs)} trace steps captured for test_audit_flow).")

    # 22. Phase 4: GET /api/analytics/trends Trajectory
    status, trend_res = request_json("GET", "/api/analytics/trends?club=CodeCraft&semester=Spring%202026")
    assert status == 200
    assert trend_res.get("status") == "success"
    assert len(trend_res.get("trajectory", [])) == 4
    assert "turnout_momentum" in trend_res
    print(f"  [OK] GET /api/analytics/trends verified (CodeCraft trajectory: {trend_res['turnout_momentum']} momentum).")

    # 23. Phase 4: POST /api/analytics/compare-semesters (Abstention on Missing Data)
    status, sem_comp = request_json("POST", "/api/analytics/compare-semesters", {"semester_a": "Spring 2026", "semester_b": "Fall 2025"})
    assert status == 200
    assert sem_comp.get("status") == "no_data"
    assert "Fall 2025" in sem_comp.get("missing_semester", "")
    print("  [OK] POST /api/analytics/compare-semesters verified with transparent abstention on unrecorded semester.")

    # 24. Phase 4: POST /api/recommendations/decision (Mark Completed Lifecycle)
    status, comp_res = request_json("POST", "/api/recommendations/decision", {
        "id": test_rec_id,
        "status": "completed",
        "comment": "Admin verification completed",
        "completion_notes": "All actions successfully enacted and measured"
    }, token=admin_token_2)
    assert status == 200
    assert comp_res["updated_status"] == "completed"
    print(f"  [OK] POST /api/recommendations/decision completed lifecycle verified ({test_rec_id} marked COMPLETED).")

    # 25. Phase 5: Professional Reporting Sections Verification
    status, rep_data = request_json("POST", "/api/reports/generate", {"semester": "Spring 2026"}, token=admin_token_2)
    assert status == 200
    report_md = rep_data["markdown"]
    assert "Institutional Scoring Methodology" in report_md
    assert "Verified Club Rankings" in report_md
    assert "Data Quality & Imputation Disclosure" in report_md
    assert "Multi-Agent Reviewer Verification Results" in report_md
    assert "Action Plan & Governance Approval Status" in report_md
    print("  [OK] Professional report structure verified (All 5 mandatory sections present).")

    # 26. Feature 1: POST /api/intelligence/predict (Predictive Event Intelligence)
    status, pred_res = request_json("POST", "/api/intelligence/predict", {
        "club_name": "CodeCraft",
        "event_type": "Hackathon",
        "semester": "Spring 2026"
    })
    assert status == 200
    assert pred_res["status"] == "success"
    assert pred_res["forecast"]["expected_attendance"] > 0
    assert len(pred_res["influencing_events"]) >= 3
    print(f"  [OK] POST /api/intelligence/predict verified (Expected CodeCraft hackathon turnout: {pred_res['forecast']['expected_attendance']} students).")

    # 27. Feature 2: POST /api/intelligence/plan (Intelligent Event Planning & Budget Optimizer)
    status, plan_res = request_json("POST", "/api/intelligence/plan", {
        "club_name": "CodeCraft",
        "budget": 20000,
        "semester": "Spring 2026"
    })
    assert status == 200
    assert plan_res["status"] == "success"
    assert "budget_allocation" in plan_res
    assert plan_res["budget"] == 20000
    assert plan_res["speaker_strategy"]["status"] == "recommended"
    print(f"  [OK] POST /api/intelligence/plan verified (Plan generated for CodeCraft with ₹20,000 budget).")

    print("\n[SUCCESS] ALL SUBSYSTEM, SECURITY, PHASE 3, 4, 5 & INTELLIGENCE API CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_checks()
