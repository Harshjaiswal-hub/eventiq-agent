# EventIQ Agent — REST API Reference Manual

**Base URL:** `http://localhost:3000` (or configured host/port)  
**API Version:** `2.0.0`  
**Authentication Modes:**
- `Cookie: session_token=<token>` (Standard SPA browser session, HttpOnly, SameSite=Lax)
- `Authorization: Bearer <session_token>` (Programmatic / API client token)
- Mutating state changes via cookies require `X-CSRF-Token: <csrf_token>` header.

---

## 1. Authentication & Session Endpoints

### `POST /api/auth/login`
Authenticates user with username and password using scrypt verification. Rate-limited to 5 attempts per 15 minutes per IP + username.

- **Request Body:**
  ```json
  {
    "username": "admin",
    "password": "AdminSecure2026!"
  }
  ```
- **Response Headers:**
  `Set-Cookie: session_token=<hex32>; Path=/; HttpOnly; SameSite=Lax; Max-Age=28800`
- **Response Body (200 OK):**
  ```json
  {
    "status": "success",
    "user": {
      "id": "user_admin",
      "username": "admin",
      "role": "ADMIN",
      "club_id": null
    },
    "csrf_token": "a1b2c3d4...",
    "session_token": "e5f6g7h8..."
  }
  ```
- **Error Codes:**
  - `400 Bad Request`: Missing username or password.
  - `401 Unauthorized`: Invalid credentials.
  - `403 Forbidden`: Account deactivated.
  - `429 Too Many Requests`: Login brute-force threshold reached.

### `GET /api/auth/me`
Returns current authenticated session profile and permissions.

- **Headers:** `Cookie` or `Authorization: Bearer <token>`
- **Response (200 OK):**
  ```json
  {
    "status": "authenticated",
    "user": {
      "id": "user_admin",
      "username": "admin",
      "role": "ADMIN",
      "club_id": null
    },
    "permissions": {
      "manage_users": true,
      "manage_clubs": true,
      "approve_recommendations": true,
      "run_audit": true,
      "generate_reports": true,
      "view_all_reports": true,
      "view_execution_logs": true,
      "view_security_logs": true,
      "view_all_rankings": true
    },
    "csrf_token": "a1b2c3d4..."
  }
  ```
- **Response (401 Unauthorized):**
  ```json
  { "status": "unauthenticated", "user": null }
  ```

### `POST /api/auth/logout`
Terminates user session, deletes session record in SQLite, and clears cookie.

- **Response (200 OK):**
  ```json
  { "status": "success", "message": "Logged out successfully." }
  ```

---

## 2. Institutional Analytics & Scoring Endpoints

### `GET /api/health`
Public health status, runtime environment, and operational telemetry.

- **Response (200 OK):**
  ```json
  {
    "status": "online",
    "app": "EventIQ Agent",
    "version": "2.0.0",
    "backend": "Python 3.11 Threaded / SQLite (WAL mode active)",
    "auth_system": "Scrypt / RBAC / Rate-Limited"
  }
  ```

### `GET /api/clubs`
Lists registered clubs and their event histories for a semester.

- **Query Parameters:**
  - `semester` (string, optional, default: `"Spring 2026"`)
- **Response (200 OK):**
  ```json
  {
    "status": "success",
    "clubs": [
      {
        "id": "codecraft",
        "name": "CodeCraft",
        "tagline": "Competitive Programming & DSA",
        "color": "#7c3aed",
        "icon": "⚡",
        "events": [...]
      }
    ]
  }
  ```

### `GET /api/rankings`
Computes canonical 5-metric composite scores and rankings. Single source of truth.

- **Query Parameters:**
  - `semester` (string, optional, default: `"Spring 2026"`)
- **Response (200 OK):**
  ```json
  {
    "semester": "Spring 2026",
    "rankings": [
      {
        "rank": 1,
        "club_id": "codecraft",
        "name": "CodeCraft",
        "composite_score": 90.47,
        "metrics": {
          "attendance_rate": 91.13,
          "feedback_score": 4.65,
          "speaker_rating": 4.62,
          "consistency_score": 96.55,
          "event_count": 4
        },
        "score": 90.5
      }
    ]
  }
  ```

### `GET /api/audit`
Scans semester events for missing check-in logs, missing survey feedback, and imputation flags.

- **Query Parameters:**
  - `semester` (string, optional, default: `"Spring 2026"`)
- **Response (200 OK):**
  ```json
  {
    "semester": "Spring 2026",
    "total_events_audited": 24,
    "missing_attendance_events": 3,
    "missing_feedback_events": 2,
    "data_health_score": 89.6,
    "issues": [...]
  }
  ```

### `POST /api/analytics/compare`
Calculates side-by-side metric deltas between two student clubs.

- **Request Body:**
  ```json
  {
    "club_a": "CodeCraft",
    "club_b": "DesignLab",
    "semester": "Spring 2026"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "comparison": {
      "club_a": "CodeCraft",
      "club_b": "DesignLab",
      "score_diff": 3.85,
      "metrics_diff": { ... }
    }
  }
  ```

### `POST /api/analytics/compare-semesters`
Compares cross-semester trajectory or club momentum. Gracefully abstains on missing historical data.

- **Request Body:**
  ```json
  {
    "semester_a": "Spring 2026",
    "semester_b": "Fall 2025",
    "club_name": "CodeCraft"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "status": "partial_data",
    "message": "Fall 2025 records are not yet digitized into SQLite."
  }
  ```

### `GET /api/analytics/trends`
Provides chronological event-by-event progression and momentum analysis.

- **Query Parameters:**
  - `club` (string, required): e.g. `CodeCraft`
  - `semester` (string, optional, default: `"Spring 2026"`)

---

## 3. Multi-Agent & RAG Endpoints

### `POST /api/agent/chat`
Conversational endpoint routing user intents with short-term session memory.

- **Request Body:**
  ```json
  {
    "message": "Why did CodeCraft win?",
    "session_id": "session_user1",
    "semester": "Spring 2026"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "status": "success",
    "session_id": "session_user1",
    "content": "CodeCraft achieved #1 with composite score 90.47...",
    "tool_calls": [...]
  }
  ```

### `POST /api/agent/audit`
Flagship multi-agent semester evaluation audit. Coordinates Analyst, Research, Recommendation, and Reviewer agents.
- **Authorization:** `ADMIN` or `EVALUATOR` required.
- **Rate Limit:** 10 audits per minute per user.
- **Request Body:**
  ```json
  {
    "semester": "Spring 2026",
    "session_id": "audit_session_1"
  }
  ```

---

## 4. Governance & Human-in-the-Loop Endpoints

### `GET /api/recommendations`
Returns generated institutional recommendations. Scoped to assigned club if user is `CLUB_LEAD`.

### `POST /api/recommendations/decision`
Applies human governance decision on recommendations.
- **Authorization:**
  - `approved`, `rejected`, `revision_requested`: `ADMIN` only.
  - `completed`: `ADMIN` or assigned `CLUB_LEAD`.
- **Request Body:**
  ```json
  {
    "id": "rec_1",
    "status": "approved",
    "comment": "Confirmed by evaluation board",
    "completion_notes": "Implemented digital sign-in form"
  }
  ```

---

## 5. Reports & Security Logs

### `GET /api/reports`
Lists or retrieves archived markdown evaluation reports.

### `POST /api/reports/generate`
Generates and archives formal semester audit report.
- **Authorization:** `ADMIN` only.

### `GET /api/logs/security`
Inspects real-time security events (failed logins, rate limit violations, access denials).
- **Authorization:** `ADMIN` only.

### `GET /api/logs/execution`
Multi-agent execution traces filtered by session.
