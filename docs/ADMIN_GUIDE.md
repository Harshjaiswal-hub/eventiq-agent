# EventIQ Agent — Administrator Operations Guide

## 1. Role-Based Access Control (RBAC) Architecture

EventIQ enforces strict server-side authorization across three distinct institutional roles:

| Capability | ADMIN | EVALUATOR | CLUB_LEAD | Unauthenticated |
| :--- | :---: | :---: | :---: | :---: |
| **View Dashboard & Leaderboard** | ✅ | ✅ | ✅ | ✅ |
| **Inspect Event Timelines** | ✅ | ✅ | ✅ | ✅ |
| **Ask Agent Chat Q&A** | ✅ | ✅ | ✅ | ✅ |
| **Run Flagship AI Audit** | ✅ | ✅ | ❌ | ❌ |
| **Generate Official Reports** | ✅ | ❌ | ❌ | ❌ |
| **Approve / Reject Recommendations** | ✅ | ❌ | ❌ | ❌ |
| **Mark Recommendations Completed** | ✅ | ❌ | ✅ (Own Club) | ❌ |
| **View Security Logs** | ✅ | ❌ | ❌ | ❌ |
| **View Full Execution Traces** | ✅ | ✅ | ❌ | ❌ |

---

## 2. Seed Account Credentials

On first run, the database seeds four initial accounts with secure scrypt password hashes:

| Role | Username | Initial Default Password | Scope / Assignment |
| :--- | :--- | :--- | :--- |
| **ADMIN** | `admin` | Configured via `INITIAL_ADMIN_PASSWORD` (Default: `AdminSecure2026!`) | Global governance |
| **EVALUATOR** | `evaluator` | Configured via `INITIAL_EVALUATOR_PASSWORD` (Default: `EvaluatorSecure2026!`) | Read-only audit & reporting |
| **CLUB_LEAD** | `lead_codecraft` | Configured via `INITIAL_LEAD_CC_PASSWORD` (Default: `CodeCraftLead2026!`) | Scoped to `CodeCraft` |
| **CLUB_LEAD** | `lead_cloudnine` | Configured via `INITIAL_LEAD_CN_PASSWORD` (Default: `CloudNineLead2026!`) | Scoped to `CloudNine` |

> [!IMPORTANT]
> **Changing Passwords:**  
> Use standard scrypt hashing to update credentials in the `users` table:
> ```bash
> python -c "from backend.security import hash_password; from backend.database import get_db_connection; conn=get_db_connection(); conn.execute('UPDATE users SET password_hash=? WHERE username=?', (hash_password('NewSecretPass2026!'), 'admin')); conn.commit(); print('Password updated!')"
> ```

---

## 3. Human-in-the-Loop Governance Workflow

1. **Trigger Audit:** Administrators or evaluators trigger `/api/agent/audit` from the topbar or chat.
2. **Review Generated Recommendations:** Open the **Approvals & Human Review** view.
3. **Decision States:**
   - **Approve:** Recommendation becomes official campus policy.
   - **Reject:** Dismissed with reason logged.
   - **Revision Requested:** Sent back for adjustment.
   - **Completed:** Club lead or admin marks the target intervention delivered.
4. **Audit Trail:** Every transition is recorded with actor username, timestamp, and review comment in SQLite.

---

## 4. Security Auditing & Monitoring

Administrators can inspect security events via `GET /api/logs/security`:
- `login_success` / `login_failed`
- `rate_limit_exceeded`
- `forbidden_access` (RBAC rejections)
- `csrf_violation`
- `recommendation_decision`

Log files are also written to `logs/eventiq.log` with automatic 5MB rotation and 7 historical backups.
