# EventIQ Agent — System Architecture & Multi-Agent Specification

**Official Project Topic:** Smart Event Analytics Agent  
**Full System Title:** EventIQ Agent — A Memory-Enabled, Tool-Using Multi-Agent System for Club Performance Analysis

---

## 1. System Overview

EventIQ Agent is an agentic, memory-enabled decision-support system designed to audit technical club operations, calculate composite performance metrics, reconcile missing records via statistical imputation, and coordinate a team of four specialized agents to generate evidence-backed institutional reports.

```mermaid
flowchart TD
    subgraph UI_Layer [Frontend Presentation & Human-in-the-Loop]
        Dash["Dashboard & KPIs"]
        Leaderboard["Interactive Leaderboard"]
        CanvasCharts["HTML5 Canvas Bar & Radar Charts"]
        Chat["Memory-Enabled Chat Interface"]
        Approvals["Human-in-the-Loop Review Panel"]
    end

    subgraph API_Layer [REST Server - server.py]
        Router["HTTP Router (/api/agent, /api/rankings, /api/reports)"]
        CorsSafety["CORS & Input Validation"]
    end

    subgraph Multi_Agent_Core [Multi-Agent Orchestration Layer]
        Supervisor["Multi-Agent Supervisor & Coordinator"]
        
        subgraph Specialized_Agents [Specialized Agent Team]
            A1["Agent 1: Data Analyst Agent<br/>(Calculations, Provenance, Normalization)"]
            A2["Agent 2: Research & Insight Agent<br/>(RAG Policies, Institutional Rubric)"]
            A3["Agent 3: Recommendation Agent<br/>(Actionable Plans, Metric Targets)"]
            A4["Agent 4: Reviewer Agent<br/>(Claim Verification, Consistency Audit)"]
        end
    end

    subgraph Tools_Layer [Deterministic Analytics Tools Layer]
        T1["get_club_rankings()"]
        T2["analyze_club_performance()"]
        T3["compare_clubs()"]
        T4["audit_data_quality()"]
        T5["get_historical_performance()"]
        T6["generate_event_report()"]
    end

    subgraph Memory_Layer [Memory & Retrieval Pipeline]
        ShortTerm["Short-Term Conversational Memory<br/>(Session Message Store)"]
        LongTerm["Long-Term Memory<br/>(Historical Audit Archive)"]
        RAG["RAG Document Store<br/>(Evaluation Rubrics & Policy Documents)"]
    end

    subgraph Persistence [SQLite Storage - eventiq.db]
        DB_Clubs[("clubs & events")]
        DB_Conv[("conversations & messages")]
        DB_Recs[("recommendations & human decisions")]
        DB_Logs[("execution_logs audit trail")]
        DB_Docs[("documents store")]
    end

    UI_Layer -->|"HTTP REST API"| API_Layer
    API_Layer --> Multi_Agent_Core
    Supervisor --> Specialized_Agents
    A1 --> Tools_Layer
    A2 --> Memory_Layer
    A3 --> A1
    A4 -->|"Audits Claims"| A1
    A4 -->|"Verifies Evidence"| A3

    Tools_Layer --> Persistence
    Memory_Layer --> Persistence
    Approvals -->|"Persists Decisions"| Persistence
```

---

## 2. Multi-Agent Collaboration Workflow

```mermaid
sequenceDiagram
    autonumber
    actor User as Campus Administrator
    participant Sup as Supervisor Coordinator
    participant DA as Data Analyst Agent
    participant RA as Research Agent (RAG)
    participant Rec as Recommendation Agent
    participant Rev as Reviewer Agent
    participant DB as SQLite Persistence

    User->>Sup: Trigger Semester Audit / Query
    Sup->>DB: Log Start Event in execution_logs
    
    Sup->>DA: Step 1: Execute calculations & data audit
    DA->>DA: Run get_club_rankings() & audit_data_quality()
    DA-->>Sup: Return normalized metrics, rankings, & data gaps
    
    Sup->>RA: Step 2: Retrieve institutional rubrics & history
    RA->>DB: Query documents via RAG retrieval
    RA-->>Sup: Return evaluation weights & archive status
    
    Sup->>Rec: Step 3: Formulate improvement plan
    Rec-->>Sup: Return evidence-linked recommendations
    
    Sup->>Rev: Step 4: Audit numerical claims & evidence links
    Rev->>Rev: Cross-check claims vs deterministic ground truth
    Rev-->>Sup: Return Verdict: APPROVED (0 unsupported claims)
    
    Sup->>DB: Persist generated report and pending recommendations
    Sup-->>User: Deliver verified, evidence-grounded report
    
    User->>DB: Approve / Reject recommendations via Human Review Panel
```

---

## 3. Specialized Agent Roles & Responsibilities

| Agent | Core Responsibility | Available Tools | Output Schema / Invariant |
| :--- | :--- | :--- | :--- |
| **Supervisor / Coordinator** | User intent routing, step limit enforcement, state assembly. | Internal dispatch | Coordinates maximum 5 bounded steps. Terminates safely. |
| **Data Analyst Agent** | Deterministic calculations, ranking derivations, data gap audit. | `get_club_rankings`, `audit_data_quality`, `analyze_club_performance` | Never hallucinates a number. Every metric traced to database rows. |
| **Research & Insight Agent** | Institutional rubric retrieval, historical comparison checks. | `retrieve_relevant_documents`, `get_historical_performance` | Explicitly states when historical data is absent (e.g. Fall 2025). |
| **Recommendation Agent** | Practical action plans linked directly to measured weaknesses. | `analyze_club_performance` | Every recommendation must have an `evidence_metric` and measurable target. |
| **Reviewer Agent** | Independent claim auditing, contradiction detection. | Verification assertions | Verifies monotonic rank ordering and evidence bindings; issues `APPROVED` verdict. |

---

## 4. Ground-Truth Scoring Engine & Imputation Logic

### Imputation Formula for Unrecorded Turnout
$$\text{knownRate} = \frac{\sum \text{Recorded Attendance}}{\sum \text{Registrations for Events with Known Attendance}}$$
$$\text{Imputed Attendance} = \text{round}(\text{registrations} \times \text{knownRate})$$
*(Documented Fallback: 80% if a club has zero recorded events).*

### Composite Score Formula
$$\text{Composite Score} = 0.30 \cdot \text{AttRate}_{\text{norm}} + 0.30 \cdot \text{Feedback}_{\text{norm}} + 0.15 \cdot \text{Speaker}_{\text{norm}} + 0.15 \cdot \text{Consistency}_{\text{norm}} + 0.10 \cdot \text{Events}_{\text{norm}}$$
All normalized components strictly bounded to $[0, 100]$.
