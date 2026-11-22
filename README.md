# EventIQ Agent — Smart Event Analytics Agent

> **EventIQ Agent — A Memory-Enabled, Tool-Using Multi-Agent System for Club Performance Analysis**  
> **Official Project Topic:** Smart Event Analytics Agent

---

## 🌟 Executive Overview

**EventIQ Agent** is an academic AI decision-support platform that transforms raw technical event data into transparent, evidence-backed club performance audits.

The application features:
- **Deterministic Analytics Engine:** Implements the official 5-metric composite scoring algorithm (Attendance, Feedback, Speaker Rating, Consistency, and Event Frequency).
- **Statistical Data Imputation:** Audits missing student turnouts and surveys, imputing missing attendance using historical club ratios with full disclosure.
- **Persistent Storage:** Backed by an embedded SQLite database storing clubs, events, chat histories, report archives, and recommendations.
- **Short-Term & Long-Term Memory:** Supports conversational follow-ups and persists generated semester reports across server restarts.
- **Retrieval-Augmented Generation (RAG):** Ingests and retrieves institutional evaluation frameworks and policy rubrics.
- **Collaborative Multi-Agent Architecture:** A Supervisor oversees four specialized agents (**Data Analyst**, **Research & Insight**, **Recommendation**, and **Reviewer**) with bounded execution and claims verification.
- **Human-in-the-Loop Decision Panel:** Allows administrators to approve, reject, or request revisions on generated recommendations.
- **Security & Accessibility:** Complete XSS sanitization, DOCTYPE correction, ARIA chart labeling, and keyboard navigation.

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** (Python 3.11 tested)
- Modern web browser (Chrome, Edge, Firefox, Safari)

### 1. Start the Unified Application Server
From the project root, launch the integrated backend and static server:

```bash
python server.py
```
*(Alternatively, run `npm run server`)*

Open your browser to:
**http://localhost:3000**

---

## 🧪 Running Automated Unit Tests

Run the complete 10-test test suite:

```bash
python -m unittest discover tests
```
*(Or run `npm test`)*

### Test Coverage Highlights:
- ✅ Composite score weights sum strictly to 1.0 (`WEIGHTS` in `backend/tools.py`).
- ✅ Ranking determinism and top performer ground-truth validation.
- ✅ Missing data imputation and data quality gap auditing.
- ✅ Transparent abstention when querying unrecorded historical semesters (Fall 2025).
- ✅ Normalization bounds and standard deviation edge-case guards.
- ✅ Session-isolated short-term conversational memory.
- ✅ RAG document retrieval for institutional evaluation rubrics.
- ✅ Multi-agent semester audit execution and Reviewer Agent claim verification.

---

## 🧠 AI, RAG & Tool Calling Implementation Reality

To ensure complete academic transparency for evaluation juries:

1. **Deterministic Analytics Tools Layer (`backend/tools.py`):**
   - Implements genuine Python calculations matching the official scoring framework.
   - When a user asks for rankings, comparisons, or data audits, the system executes real SQLite queries and Python mathematical functions rather than relying on generative LLM arithmetic.
2. **Lexical RAG Retrieval (`backend/memory.py`):**
   - The RAG engine performs length-normalized term-frequency retrieval over institutional policy and rubric documents stored in SQLite (`documents` table).
   - It retrieves verified rubric weights and campus verification standards to ground the multi-agent findings. (External vector embedding API calls are intentionally avoided to allow 100% offline, zero-cost, zero-latency execution).
3. **Multi-Agent Orchestration (`backend/multi_agent.py`):**
   - Implements four structured agents coordinated by a Supervisor: **Data Analyst Agent**, **Research & Insight Agent**, **Recommendation Agent**, and **Reviewer Agent**.
   - Each agent executes distinct responsibilities with strict data provenance. The Reviewer Agent audits claims against database ground truth and flags unlinked evidence.
4. **Historical Absence Transparency:**
   - Spring 2026 is the active digitized baseline. When asked about Fall 2025, the system abstains and states that past records have not been digitized.

---

## 🔄 Resetting Local Demo & Test Data
To reset the SQLite database back to its pristine seed state (6 clubs, 24 events, 3 pending recommendations) without affecting code:
```bash
python -c "import os; os.remove('eventiq.db') if os.path.exists('eventiq.db') else None; from backend.database import seed_db_if_empty; seed_db_if_empty(); print('Database reset successfully!')"
```

---

## 📁 Repository Structure

```
agentic_ai/
├── backend/
│   ├── database.py         # SQLite connection, schema tables, idempotent seeding
│   ├── tools.py            # 6 deterministic analytics tools (rankings, compare, audit)
│   ├── memory.py           # Short-term chat memory, long-term report archive, RAG retrieval
│   └── multi_agent.py      # Supervisor + 4 specialized agents (Analyst, Research, Rec, Reviewer)
├── css/
│   └── style.css           # Preserved dark-mode design system & animations
├── docs/
│   ├── ARCHITECTURE.md     # System architecture diagrams and multi-agent workflows
│   ├── DATABASE_SCHEMA.md  # Relational schema specification & provenance tracking
│   └── EVALUATION.md       # Comparative ablation experiments & measured metrics
├── js/
│   ├── agent.js            # Hardened client-side analytics engine
│   ├── app.js              # UI controller, Canvas charts, API bridge, Human Review view
│   └── data.js             # Canonical semester data definitions
├── tests/
│   └── test_analytics.py   # Comprehensive automated unit tests
├── index.html              # Fixed DOCTYPE shell, AI Audit trigger, Approvals view
├── server.py               # Unified REST API & static server on port 3000
├── PROJECT_TECHNICAL_STATUS.md # Verified technical status & master knowledge doc
├── .env.example            # Environment variables configuration template
└── package.json            # NPM project scripts
```

---

## 🎓 Academic Jury Demonstration Script (5-Minute Walkthrough)

1. **Dashboard & Ground-Truth Rankings (Minute 1):**
   - Open `http://localhost:3000`. Show the KPI cards (24 events, 2,430 registrations).
   - Point out the Club Leaderboard: **CodeCraft** ranks #1 with a composite score of 94.2/100.
   - Show the dynamic Canvas bar chart and 5-axis radar chart showing relative club strengths.

2. **Flagship Multi-Agent Semester Audit (Minute 2):**
   - Click the topbar **"✨ Run AI Audit"** button.
   - Observe the agent collaboration trace in the chat feed:
     - `Supervisor` coordinates the audit.
     - `Data Analyst Agent` calculates rankings and identifies 3 unrecorded attendance events.
     - `Research Agent` retrieves institutional policy weights from the RAG store.
     - `Recommendation Agent` generates concrete action plans.
     - `Reviewer Agent` audits all claims and signs off with an `APPROVED` verdict.

3. **Memory & RAG Follow-Up (Minute 3):**
   - In the chat, type: *"Why did they win?"*
   - Observe how the agent uses **conversational memory** to recognize the subject is CodeCraft and breaks down their attendance (91.1%) and feedback (4.65/5.0).
   - Type: *"Compare CodeCraft and DesignLab"* to see real-time numerical delta analysis.

4. **Historical Absence Transparency (Minute 4):**
   - Type: *"How did CodeCraft perform in Fall 2025?"*
   - Demonstrate that the agent **does not hallucinate**: it transparently reports that digital records prior to Spring 2026 are not yet present in the SQLite database.

5. **Human-in-the-Loop Review Panel (Minute 5):**
   - Click the **"⚖️ Approvals & Human Review"** tab on the sidebar.
   - Demonstrate administrative governance over generated recommendations.
   - Click **"Approve"** on a pending recommendation; show that the decision is immediately persisted in the database.
