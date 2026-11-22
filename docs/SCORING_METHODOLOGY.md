# EventIQ Agent — Scoring Methodology & Mathematical Specification

## 1. Overview & Official Weights

The EventIQ Agent scoring engine computes club performance using a 5-metric composite index grounded in institutional data. Calculations are executed strictly in Python (`backend/tools.py`), ensuring deterministic, tamper-proof ranking without generative arithmetic.

| Metric | Weight | Key Indicator | Objective |
| :--- | :---: | :--- | :--- |
| **Attendance Rate** | **30%** | Participant turnout vs. registrations | Measures actual student reach & engagement |
| **Feedback Score** | **30%** | Average participant survey score (1.0–5.0) | Evaluates attendee satisfaction & event quality |
| **Speaker Rating** | **15%** | Average guest speaker rating (1.0–5.0) | Assesses quality of invited industry/academic experts |
| **Attendance Consistency** | **15%** | Low variance across event turnouts | Rewards consistent delivery vs. one-off spikes |
| **Event Frequency** | **10%** | Total completed events in semester | Measures sustained academic presence |

$$\sum_{i=1}^{5} w_i = 0.30 + 0.30 + 0.15 + 0.15 + 0.10 = 1.00$$

---

## 2. Statistical Imputation for Missing Attendance

When check-in logs are unrecorded, omitting events would penalize clubs unfairly, while assuming 100% turnout falsifies records. EventIQ uses club-specific mean ratio imputation with explicit provenance flags:

1. **Calculate Known Turnout Ratio:**
   $$\text{Ratio}_{\text{club}} = \frac{\sum \text{Recorded Attendance}}{\sum \text{Registrations of Events with Recorded Attendance}}$$

2. **Impute Missing Turnout:**
   $$\text{Turnout}_{\text{imputed}} = \text{round}(\text{Registrations}_{\text{target}} \times \text{Ratio}_{\text{club}})$$

3. **Fallback Constraint:** If a club has zero recorded events, default ratio is $0.80$ (80%).
4. **Audit Disclosure:** The `is_attendance_imputed` column is set to `1` in SQLite, and flagged in `/api/audit`.

---

## 3. Metric Computations

### A. Attendance Rate ($M_1$)
$$M_1 = \frac{1}{N} \sum_{j=1}^{N} \frac{\text{Attendance}_j}{\text{Registrations}_j} \times 100$$

### B. Feedback Score ($M_2$)
All individual attendee survey responses (1–5 scale) across all club events are concatenated:
$$M_2 = \frac{1}{K} \sum_{k=1}^{K} \text{Rating}_k$$
Events with missing feedback forms are excluded from survey averaging.

### C. Speaker Rating ($M_3$)
$$M_3 = \frac{1}{E_{\text{speaker}}} \sum_{e=1}^{E_{\text{speaker}}} \text{SpeakerRating}_e$$

### D. Attendance Consistency ($M_4$)
Standard deviation of event turnout rates is computed:
$$\sigma = \sqrt{\frac{1}{N} \sum_{j=1}^{N} (R_j - \bar{R})^2} \quad \text{where } R_j = \frac{\text{Attendance}_j}{\text{Registrations}_j}$$
Consistency score penalizes volatility:
$$M_4 = \max(0, 1.0 - \sigma) \times 100$$

### E. Event Frequency ($M_5$)
$$M_5 = N \quad (\text{Total validated events hosted in the semester})$$

---

## 4. Min-Max Normalization & Composite Formula

To aggregate disparate units (percentages, Likert scores, counts), each metric $M_k$ is min-max normalized across all participating clubs:

$$\text{Norm}(M_{k, c}) = \begin{cases} 
100.0 & \text{if } \max(M_k) = \min(M_k) \\
\frac{M_{k, c} - \min(M_k)}{\max(M_k) - \min(M_k)} \times 100 & \text{otherwise}
\end{cases}$$

### Final Composite Score:
$$\text{Composite Score}_c = \sum_{k=1}^{5} w_k \cdot \text{Norm}(M_{k, c})$$
Final scores range strictly within $[0.0, 100.0]$. Ties are resolved by attendance rate.
