# EventIQ Agent — Database Schema & Data Provenance

The EventIQ Agent utilizes an embedded, persistent **SQLite** database (`eventiq.db`) to ensure zero-configuration, reliable execution and restart resilience.

---

## 1. Table Definitions

### `semesters`
Stores registered semester windows and evaluation timelines.
- `id` (TEXT, PK): E.g. `'spring_2026'`
- `name` (TEXT): Display name (`'Spring 2026'`)
- `start_date` (TEXT): ISO date (`'2026-01-15'`)
- `end_date` (TEXT): ISO date (`'2026-05-30'`)
- `created_at` (TIMESTAMP): Auto-generated creation timestamp.

### `clubs`
Stores institutional club records and visual tokens.
- `id` (TEXT, PK): Unique club identifier (e.g. `'codecraft'`)
- `name` (TEXT, UNIQUE): Full name (`'CodeCraft'`)
- `tagline` (TEXT): Domain description
- `color` (TEXT): Hex color string (`'#7c3aed'`)
- `icon` (TEXT): Visual symbol (`'⚡'`)
- `created_at` (TIMESTAMP)

### `events`
Detailed event records with provenance tracking for observed vs. imputed attendance.
- `id` (TEXT, PK): Event identifier (e.g. `'cc1'`)
- `club_id` (TEXT, FK -> `clubs.id`): Owning club
- `semester` (TEXT): Semester association (`'Spring 2026'`)
- `name` (TEXT): Event title
- `type` (TEXT): Event category (Workshop, Hackathon, Competition, Seminar)
- `date` (TEXT): ISO date string
- `registrations` (INTEGER): Total registered students
- `attendance` (INTEGER, NULLABLE): Recorded turnout (null if check-in was unrecorded)
- `is_attendance_imputed` (BOOLEAN): `1` if attendance was mathematically imputed, `0` if observed
- `feedback_json` (TEXT, NULLABLE): Serialized JSON array of 1-5 student ratings
- `speaker_rating` (REAL, NULLABLE): Average speaker rating (1.0 - 5.0)
- `duration_hours` (REAL): Duration in hours
- `resources_used` (REAL): Budget spent
- `created_at` (TIMESTAMP)

### `conversations` & `messages` (Short-Term Conversational Memory)
- `conversations.id` (TEXT, PK): Session UUID
- `conversations.title` (TEXT): Session topic
- `conversations.updated_at` (TIMESTAMP)
- `messages.id` (INTEGER, PK AUTOINCREMENT)
- `messages.conversation_id` (TEXT, FK -> `conversations.id`)
- `messages.role` (TEXT): `'user'` or `'assistant'`
- `messages.content` (TEXT): Message text
- `messages.tool_calls_json` (TEXT, NULLABLE): Executed analytics tools and status
- `messages.created_at` (TIMESTAMP)

### `reports` (Long-Term Memory Archive)
- `id` (TEXT, PK): Unique report identifier
- `semester` (TEXT): Semester target
- `title` (TEXT): Report title
- `summary` (TEXT): Brief executive summary
- `markdown_content` (TEXT): Full structured audit report
- `provenance_json` (TEXT): Metadata of tools and multi-agent coordinator that produced the report
- `created_at` (TIMESTAMP)

### `recommendations` (Human-in-the-Loop Governance)
- `id` (TEXT, PK): Recommendation ID
- `semester` (TEXT): Semester target
- `club_id` (TEXT): Target club or `'all'`
- `recommendation_text` (TEXT): Actionable suggested policy or intervention
- `evidence_metric` (TEXT): Ground-truth metric triggering the recommendation
- `status` (TEXT): `'pending'`, `'approved'`, `'rejected'`, `'revision_requested'`
- `reviewer_comment` (TEXT, NULLABLE): Reviewer justification
- `decision_timestamp` (TIMESTAMP, NULLABLE): When human decision was finalized
- `created_at` (TIMESTAMP)

### `documents` (RAG Knowledge Store)
- `id` (TEXT, PK): Document chunk ID
- `doc_type` (TEXT): `'policy'`, `'rubric'`, or `'report'`
- `title` (TEXT): Document title
- `content` (TEXT): Text content used for RAG grounding
- `metadata_json` (TEXT): Serialized attributes
- `embedding_json` (TEXT, NULLABLE): Serialized float vector

### `execution_logs` (Audit Trail)
- `id` (INTEGER, PK AUTOINCREMENT)
- `session_id` (TEXT): Multi-agent execution session
- `agent_name` (TEXT): Agent responsible (`data_analyst`, `reviewer_agent`, etc.)
- `action` (TEXT): Specific step performed
- `details_json` (TEXT): Step input/output payload
- `created_at` (TIMESTAMP)
