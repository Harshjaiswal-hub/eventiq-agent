# EventIQ Agent — User Experience & Evaluation Guide

## 1. Navigating the Dashboard

EventIQ Agent provides a dark enterprise analytics experience inspired by modern institutional products.

### Primary Navigation Views
- **📊 Overview / Dashboard:** Primary institutional scoreboard displaying KPI summary cards, the dynamic Club Leaderboard, composite score bar chart, and 5-axis metric radar chart.
- **💬 Ask Agent:** Interactive conversational query view with session memory. Ask natural language questions like *"Why is CodeCraft ranked #1?"* or *"Compare CodeCraft and DesignLab"*.
- **📅 Event Timeline:** Filterable timeline of all 24 semester events with search filtering, type tags, and data quality badges (Observed vs. Imputed).
- **📑 Full Report:** Comprehensive markdown performance audit reports with methodology, provenance disclosure, and LaTeX equations.
- **⚖️ Approvals & Review:** Human-in-the-loop decision console where administrators review, approve, or reject multi-agent recommendations.

---

## 2. Interactive Features

### Club Detail Modal
Click any club in the Leaderboard to open the dedicated **Club Performance Deep-Dive Modal**:
- Executive summary & rank.
- 5 normalized scores broken down by weight.
- Historical attendance & feedback trajectory.
- Complete event roster for the club.

### Radar Chart Interaction
The 5-axis radar chart displays normalized metrics:
1. Attendance Rate (30%)
2. Participant Feedback (30%)
3. Speaker Rating (15%)
4. Turnout Consistency (15%)
5. Event Frequency (10%)

Toggle individual clubs on and off by clicking their names in the chart legend.

### Timeline Search & Data Quality Filter
- Use the search bar in the Event Timeline to search by event name or club.
- Click **"Flagged Only"** to view events with missing turnout records that required statistical imputation.

---

## 3. Conversational Queries Cheat Sheet

| Question | What the Agent Does |
| :--- | :--- |
| *"Who is winning this semester?"* | Queries `/api/rankings` and returns current top performer with score breakdown. |
| *"Why did they win?"* | Uses conversational memory to recall the top performer and explains their attendance and feedback metrics. |
| *"Compare CodeCraft and RoboTech"* | Runs deterministic delta comparison across all 5 evaluation dimensions. |
| *"Show me missing data"* | Audits the semester database and lists unrecorded events and imputation rationale. |
| *"How did they do in Fall 2025?"* | Transparently abstains, informing the user that historical records prior to Spring 2026 are not yet digitized. |
