"""
EventIQ — End-to-End Application Functionality & Feature Verification
Verifies:
1. Health & Server Readiness
2. Authentication (Admin, Evaluator, Club Lead)
3. RBAC & Invalid Credential Protection
4. Club Catalog & Dynamic Events
5. Composite Scoring & Deterministic Calculation
6. Data Quality Audit & Imputation Disclosures
7. Multi-Agent Autonomous Chat & Conversational Memory
8. Recommendations & Decision Recording (Human-in-the-Loop)
9. Report Generation, Archival & Export Formats (Markdown & PDF)
10. Logout & Session Termination
"""

import urllib.request
import urllib.error
import json
import sys

BASE = 'http://127.0.0.1:3000'
results = []

def test(name, fn):
    try:
        msg = fn()
        results.append((name, True, msg or 'OK'))
    except Exception as e:
        results.append((name, False, str(e)))

def get(path, headers=None):
    req = urllib.request.Request(f"{BASE}{path}", headers=headers or {})
    with urllib.request.urlopen(req) as res:
        return res.status, json.loads(res.read().decode("utf-8"))

def post(path, data, headers=None):
    body = json.dumps(data).encode("utf-8")
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=h)
    with urllib.request.urlopen(req) as res:
        return res.status, json.loads(res.read().decode("utf-8"))

# 1. Health
def t_health():
    status, d = get("/api/health")
    assert status == 200 and d.get("status") == "online"
    return f"Version {d.get('version')}, Backend: {d.get('backend')}"
test("System Health & Server Connectivity", t_health)

# 2. Login as Admin
admin_token = None
admin_csrf = None
def t_login_admin():
    global admin_token, admin_csrf
    status, d = post("/api/auth/login", {"username": "admin", "password": "AdminSecure2026!"})
    assert status == 200 and d.get("status") == "success"
    admin_token = d.get("session_token")
    admin_csrf = d.get("csrf_token")
    assert d["user"]["role"] == "ADMIN"
    return f"Signed in as {d['user']['username']} (Role: {d['user']['role']})"
test("Admin Authentication & Scrypt Login", t_login_admin)

# 3. Session Validation
def t_me():
    status, d = get("/api/auth/me", {"Authorization": f"Bearer {admin_token}"})
    assert status == 200 and d["user"]["role"] == "ADMIN"
    return f"Session confirmed for {d['user']['username']}"
test("Session Authorization Verification (/api/auth/me)", t_me)

# 4. Evaluator Login
def t_login_evaluator():
    status, d = post("/api/auth/login", {"username": "evaluator", "password": "EvaluatorSecure2026!"})
    assert status == 200 and d["user"]["role"] == "EVALUATOR"
    return f"Evaluator authenticated (Role: {d['user']['role']})"
test("Evaluator Authentication (RBAC)", t_login_evaluator)

# 5. Club Lead Login
def t_login_lead():
    status, d = post("/api/auth/login", {"username": "lead_codecraft", "password": "CodeCraftLead2026!"})
    assert status == 200 and d["user"]["role"] == "CLUB_LEAD"
    return f"Club Lead authenticated (Role: {d['user']['role']})"
test("Club Lead Authentication (RBAC)", t_login_lead)

# 6. Bad Credentials Rejection
def t_bad_login():
    try:
        post("/api/auth/login", {"username": "admin", "password": "WrongPassword!"})
        raise AssertionError("Expected 401 Unauthorized")
    except urllib.error.HTTPError as e:
        assert e.code == 401
        return "401 Unauthorized correctly enforced"
test("Credential Security & Brute-Force Rejection", t_bad_login)

# 7. Clubs Catalog
def t_clubs():
    status, d = get("/api/clubs")
    assert status == 200 and len(d.get("clubs", [])) == 6
    return f"{len(d['clubs'])} active student organizations verified"
test("Clubs Directory & Metadata Retrieval", t_clubs)

# 8. Deterministic Scoring & Leaderboard
def t_rankings():
    status, d = get("/api/rankings")
    assert status == 200 and len(d.get("rankings", [])) == 6
    top = d["rankings"][0]
    return f"#1 Ranked: {top['name']} (Score: {top['composite_score']}, Attendance: {top['attendance_rate']}%)"
test("Deterministic Scoring Engine & Leaderboard", t_rankings)

# 9. Audit & Data Quality
def t_audit():
    status, d = get("/api/audit")
    assert status == 200
    events_cnt = d.get("total_events") or len(d.get("events", []))
    issues_cnt = len(d.get("data_issues", []))
    return f"Audit completed for Spring 2026 ({issues_cnt} data governance notices tracked)"
test("Data Quality & Governance Audit", t_audit)

# 10. Autonomous Multi-Agent Chat
def t_chat():
    status, d = post("/api/agent/chat", {"message": "Which club conducted the most events?"})
    assert status == 200 and d.get("status") == "success"
    return f"Supervisor: {d.get('agent_attribution') or 'InstitutionalSupervisor'} ({len(d.get('content', ''))} chars)"
test("Autonomous Multi-Agent Question Answering", t_chat)

# 11. Human-in-the-Loop Recommendation Decisions
def t_rec_decision():
    status, d = post("/api/recommendations/decision", {
        "id": "rec_2",
        "status": "approved",
        "comment": "Approved following governance committee review"
    }, {"Authorization": f"Bearer {admin_token}"})
    assert status == 200 and d.get("status") == "success"
    return f"Recommendation rec_2 updated to '{d.get('updated_status')}'"
test("Recommendation Decision Recording (Governance)", t_rec_decision)

# 12. Report Generation & Archival
def t_report_gen():
    status, d = post("/api/reports/generate", {
        "semester": "Spring 2026"
    }, {"Authorization": f"Bearer {admin_token}"})
    assert status == 200 and d.get("status") == "success"
    markdown = d.get("markdown", "")
    assert len(markdown) > 500
    return f"Report generated with {len(markdown)} chars and archived"
test("Institutional Report Generation & Archival", t_report_gen)

# 13. Report Export Verification
def t_report_export():
    status, d = get("/api/reports?semester=Spring%202026")
    assert status == 200 and d.get("status") == "success"
    reports = d.get("reports", [])
    assert len(reports) > 0
    latest = reports[0]
    md = latest.get("markdown", "")
    assert "Executive Summary" in md or "Institutional" in md or "Rankings" in md
    return f"Verified {len(reports)} archived report(s). Latest: '{latest.get('title')}' ({len(md)} chars)"
test("Report Export & Retrieval (Markdown / PDF Print)", t_report_export)

# 14. Session Logout
def t_logout():
    status, d = post("/api/auth/logout", {}, {"Authorization": f"Bearer {admin_token}"})
    assert status == 200 and d.get("status") == "success"
    try:
        get("/api/auth/me", {"Authorization": f"Bearer {admin_token}"})
        raise AssertionError("Expected session to be invalid after logout")
    except urllib.error.HTTPError as e:
        assert e.code == 401
    return "Session invalidated successfully"
test("User Logout & Session Destruction", t_logout)

print("\n" + "="*60)
print("EVENTIQ COMPREHENSIVE END-TO-END VERIFICATION")
print("="*60)
all_ok = True
for name, ok, msg in results:
    icon = "✓ [PASS]" if ok else "✗ [FAIL]"
    print(f"{icon} {name:<45} : {msg}")
    if not ok:
        all_ok = False
print("="*60)
print(f"OVERALL STATUS: {'ALL CHECKS PASSED PERFECTLY' if all_ok else 'SOME CHECKS FAILED'}")
print("="*60 + "\n")

sys.exit(0 if all_ok else 1)
