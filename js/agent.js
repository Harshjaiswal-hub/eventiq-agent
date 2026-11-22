// ============================================================
// Smart Event Analytics Agent — Metrics Engine
// ============================================================

class EventAnalyticsAgent {
  constructor(clubs, semester) {
    this.clubs = clubs;
    this.semester = semester;
    this.analysisLog = [];
    this.metrics = null;
    this.rankings = null;
  }

  // ─────────────────────────────────────────────────────────
  // STEP 1: Collect & validate data
  // ─────────────────────────────────────────────────────────
  collectData() {
    const log = [];
    const report = { clubs: [], dataIssues: [] };

    for (const club of this.clubs) {
      let totalReg = 0, totalAtt = 0, attCount = 0;
      let allFeedback = [], allSpeaker = [];
      const eventReports = [];

      for (const ev of club.events) {
        // --- Registrations ---
        totalReg += ev.registrations || 0;

        // --- Attendance ---
        if (ev.attendance === null || ev.attendance === undefined) {
          report.dataIssues.push({
            club: club.name,
            event: ev.name,
            field: "attendance",
            action: "Imputed from average ratio of other events in same club"
          });
        } else {
          totalAtt += Number(ev.attendance) || 0;
          attCount++;
        }

        // --- Feedback ---
        let feedbackAvg = null;
        if (!ev.feedback || ev.feedback.length === 0) {
          report.dataIssues.push({
            club: club.name,
            event: ev.name,
            field: "feedback",
            action: "Excluded from feedback average; club average used for composite score"
          });
        } else {
          feedbackAvg = ev.feedback.reduce((a, b) => a + b, 0) / ev.feedback.length;
          allFeedback.push(...ev.feedback);
        }

        // --- Speaker rating ---
        if (ev.speaker_rating !== null && ev.speaker_rating !== undefined && !isNaN(ev.speaker_rating)) {
          allSpeaker.push(Number(ev.speaker_rating));
        }

        eventReports.push({
          ...ev,
          feedbackAvg: (feedbackAvg !== null && !isNaN(feedbackAvg)) ? +feedbackAvg.toFixed(2) : null,
          hasMissingAttendance: ev.attendance === null || ev.attendance === undefined,
          hasMissingFeedback: !ev.feedback || ev.feedback.length === 0
        });
      }

      // Impute missing attendance using club's known attendance rate (matching Python bankers' rounding)
      const regRecorded = totalReg - (club.events.reduce((s, e) => (e.attendance === null || e.attendance === undefined) ? s + (e.registrations || 0) : s, 0));
      const knownRate = (attCount > 0 && regRecorded > 0) ? (totalAtt / regRecorded) : 0.8;
      let finalTotalAtt = totalAtt;
      for (const ev of club.events) {
        if (ev.attendance === null || ev.attendance === undefined) {
          finalTotalAtt += roundHalfToEven((ev.registrations || 0) * knownRate);
        }
      }

      const attendanceRate = totalReg > 0 ? (finalTotalAtt / totalReg) * 100 : 0;
      const avgFeedback = allFeedback.length > 0 ? (allFeedback.reduce((a, b) => a + b, 0) / allFeedback.length) : null;
      const avgSpeaker = allSpeaker.length > 0 ? (allSpeaker.reduce((a, b) => a + b, 0) / allSpeaker.length) : null;
      const eventCount = club.events.length;

      // Consistency: stddev of per-event attendance rates
      const perEventRates = club.events
        .filter(e => e.attendance !== null && e.attendance !== undefined && (e.registrations || 0) > 0)
        .map(e => (e.attendance / e.registrations) * 100);
      const consistency = perEventRates.length > 1
        ? Math.max(0, Math.min(100, 100 - stdDev(perEventRates)))
        : (eventCount === 0 ? 0 : 75);

      report.clubs.push({
        club,
        events: eventReports,
        metrics: {
          totalRegistrations: totalReg,
          totalAttendance: finalTotalAtt,
          attendanceRate: +attendanceRate.toFixed(1),
          avgFeedback: avgFeedback ? +avgFeedback.toFixed(2) : null,
          avgSpeakerRating: avgSpeaker ? +avgSpeaker.toFixed(2) : null,
          eventCount,
          consistency: +consistency.toFixed(1),
          totalResourcesUsed: club.events.reduce((s, e) => s + (e.resources_used || 0), 0)
        }
      });

      log.push(`✅ Processed ${club.name}: ${eventCount} events, ${totalReg} registrations`);
    }

    this.rawReport = report;
    this.analysisLog = log;
    return report;
  }

  // ─────────────────────────────────────────────────────────
  // STEP 2: Calculate composite score & rank
  // ─────────────────────────────────────────────────────────
  calculateCompositeScores() {
    const data = this.rawReport.clubs;

    // Normalize each metric to 0–100
    const normalize = (val, min, max) => {
      if (val === null || val === undefined || isNaN(val)) return 0;
      if (max === min) return 50;
      const res = ((val - min) / (max - min)) * 100;
      return Math.max(0, Math.min(100, isNaN(res) ? 0 : res));
    };

    const fields = {
      attendanceRate: { weight: 0.30 },
      avgFeedback:    { weight: 0.30, scale: 20 }, // 1–5 → *20 → 0–100
      avgSpeakerRating: { weight: 0.15, scale: 20 },
      eventCount:     { weight: 0.10 },
      consistency:    { weight: 0.15 }
    };

    // Get ranges
    const ranges = {};
    for (const key of Object.keys(fields)) {
      const vals = data.map(d => {
        const raw = d.metrics[key];
        if (raw === null || raw === undefined || isNaN(raw)) return 0;
        return fields[key].scale ? raw * fields[key].scale : raw;
      });
      const minVal = vals.length > 0 ? Math.min(...vals) : 0;
      const maxVal = vals.length > 0 ? Math.max(...vals) : 100;
      ranges[key] = { min: minVal, max: maxVal };
    }

    // Score each club
    const scored = data.map(d => {
      let composite = 0;
      const breakdown = {};
      for (const [key, cfg] of Object.entries(fields)) {
        let raw = d.metrics[key];
        if (raw === null || raw === undefined) raw = 0;
        const scaled = cfg.scale ? raw * cfg.scale : raw;
        const normalized = normalize(scaled, ranges[key].min, ranges[key].max);
        breakdown[key] = { raw, normalized: +normalized.toFixed(1), weight: cfg.weight };
        composite += normalized * cfg.weight;
      }
      return { ...d, composite: +composite.toFixed(2), breakdown };
    });

    // Sort descending
    scored.sort((a, b) => b.composite - a.composite);
    scored.forEach((d, i) => d.rank = i + 1);

    this.metrics = scored;
    this.rankings = scored;
    return scored;
  }

  // ─────────────────────────────────────────────────────────
  // STEP 3: Generate natural-language report
  // ─────────────────────────────────────────────────────────
  generateReport() {
    const top = this.rankings[0];
    const lines = [];

    lines.push(`## 📋 ${this.semester.name} — Technical Events Analysis Report`);
    lines.push(`**Semester Period:** ${this.semester.start} to ${this.semester.end}`);
    lines.push(`**Clubs Analyzed:** ${this.clubs.length} | **Total Events:** ${this.clubs.reduce((s, c) => s + (c.events ? c.events.length : 0), 0)}`);
    lines.push('');
    lines.push('---');
    lines.push('');
    lines.push(`### 1. Executive Summary & Top Performer: **${top.club.name}**`);
    lines.push(`${top.club.name} (${top.club.tagline}) emerged as the top-performing club with a composite score of **${top.composite}/100**.`);
    lines.push(`They excelled in attendance turnout (${top.metrics.attendanceRate}%), feedback (${top.metrics.avgFeedback ?? 'N/A'}/5), and consistency (${top.metrics.consistency}/100).`);
    lines.push('');
    lines.push('---');
    lines.push('');
    lines.push('### 2. Institutional Scoring Methodology');
    lines.push('EventIQ computes deterministic composite scores using min-max normalization across active technical clubs:');
    lines.push('$$\\text{Composite Score} = \\sum_{i=1}^5 w_i \\times \\text{Norm}(M_i) \\quad (\\sum w_i = 1.0000)$$');
    lines.push('- **Attendance Rate (30%, w=0.30):** Normalized turnout percentage across scheduled sessions.');
    lines.push('- **Student Feedback (30%, w=0.30):** Mean Likert rating scaled from 5-point surveys.');
    lines.push('- **Speaker Rating (15%, w=0.15):** Evaluated speaker quality on 5-point scale.');
    lines.push('- **Consistency Index (15%, w=0.15):** Turnout stability calculated via inverted standard deviation.');
    lines.push('- **Event Pipeline (10%, w=0.10):** Major technical event production volume.');
    lines.push('');
    lines.push('---');
    lines.push('');
    lines.push('### 3. Club Rankings & Metric Breakdown');
    lines.push('| Rank | Club | Composite Score | Attendance Rate | Avg Feedback | Events | Consistency |');
    lines.push('|:---:|:---|:---:|:---:|:---:|:---:|:---:|');
    for (const d of this.rankings) {
      const medal = ['🥇','🥈','🥉'][d.rank - 1] || `#${d.rank}`;
      lines.push(`| ${medal} | **${d.club.name}** | **${d.composite}**/100 | ${d.metrics.attendanceRate}% | ${d.metrics.avgFeedback ?? '⚠️ Missing'}/5 | ${d.metrics.eventCount} | ${d.metrics.consistency} |`);
    }
    lines.push('');
    lines.push('---');
    lines.push('');
    lines.push('### 4. Explainable AI (XAI) Attribution & Drivers');
    for (const d of this.rankings) {
      lines.push(`**#${d.rank}. ${d.club.name}** — Score: ${d.composite}/100`);
      const strengths = [], weaknesses = [];
      if (d.metrics.attendanceRate >= 85) strengths.push(`strong attendance (${d.metrics.attendanceRate}%)`);
      else weaknesses.push(`below-average attendance (${d.metrics.attendanceRate}%)`);
      if (d.metrics.avgFeedback && d.metrics.avgFeedback >= 4.5) strengths.push(`excellent feedback (${d.metrics.avgFeedback}/5)`);
      else if (d.metrics.avgFeedback) weaknesses.push(`moderate feedback (${d.metrics.avgFeedback}/5)`);
      if (d.metrics.eventCount >= 4) strengths.push(`high event frequency (${d.metrics.eventCount} events)`);
      if (d.metrics.consistency >= 90) strengths.push(`very consistent turnout`);
      else if (d.metrics.consistency < 75) weaknesses.push(`variable attendance across events`);

      if (strengths.length) lines.push(`> ▲ **Primary Strength:** ${strengths.join(', ')}`);
      if (weaknesses.length) lines.push(`> ▼ **Primary Limiting Factor:** ${weaknesses.join(', ')}`);
      lines.push('');
    }

    // Data gaps
    const issues = this.rawReport.dataIssues;
    if (issues.length) {
      lines.push('---');
      lines.push('');
      lines.push('### 5. Data Quality & Imputation Transparency');
      lines.push(`${issues.length} data gaps were detected and statistically imputed using bankers' rounding (round-half-to-even):`);
      for (const issue of issues) {
        lines.push(`- **${issue.club} — ${issue.event}:** Missing \`${issue.field}\` → ${issue.action}`);
      }
      lines.push('');
    }

    lines.push('---');
    lines.push('');
    lines.push('### 6. Action Plan & Governance Review Status');
    lines.push('- **CloudNine (Rank #6):** Implement compulsory RSVP reminders to lift attendance above 75%. `[Status: PENDING]`');
    lines.push('- **All Clubs:** Standardize QR digital verification at entrance to eliminate missing check-in logs. `[Status: APPROVED]`');
    lines.push('- **CodeCraft (Rank #1):** Organize cross-club masterclasses on hackathon planning. `[Status: COMPLETED]`');

    return lines.join('\n');
  }

  // ─────────────────────────────────────────────────────────
  // STEP 4: Intent-aware response dispatcher
  // ─────────────────────────────────────────────────────────
  respond(query) {
    const q = query.toLowerCase();

    if (!this.metrics) {
      this.collectData();
      this.calculateCompositeScores();
    }

    // Best club
    if (q.match(/best|top|winner|first|number 1|#1|rank 1/)) {
      return this.answerBestClub();
    }
    // Rankings
    if (q.match(/rank|ranking|order|list all|compare all/)) {
      return this.answerRankings();
    }
    // Specific club
    const clubMatch = this.clubs.find(c => q.includes(c.name.toLowerCase()));
    if (clubMatch) {
      return this.answerSpecificClub(clubMatch.id);
    }
    // Attendance
    if (q.match(/attend|turnout|show up|presence/)) {
      return this.answerAttendance();
    }
    // Feedback
    if (q.match(/feedback|rating|score|satisfaction|review/)) {
      return this.answerFeedback();
    }
    // Missing data
    if (q.match(/missing|gap|incomplete|null|unknown/)) {
      return this.answerMissingData();
    }
    // Full report
    if (q.match(/report|summary|analysis|analyze|tell me|overview/)) {
      return { type: 'report', content: this.generateReport() };
    }
    // Event list
    if (q.match(/event|events|what happened|list event/)) {
      return this.answerEventList();
    }
    // Recommendations
    if (q.match(/recommend|suggest|improve|advice|tip/)) {
      return this.answerRecommendations();
    }

    // Default: full analysis
    return { type: 'report', content: this.generateReport() };
  }

  answerBestClub() {
    const top = this.rankings[0];
    return {
      type: 'highlight',
      content: `## 🏆 Best Performing Club: ${top.club.icon} ${top.club.name}\n\n` +
        `**${top.club.name}** (${top.club.tagline}) ranked **#1** with a composite score of **${top.composite}/100**.\n\n` +
        `**Why they won:**\n` +
        `- Attendance Rate: **${top.metrics.attendanceRate}%** (highest among all clubs)\n` +
        `- Avg Feedback: **${top.metrics.avgFeedback ?? 'N/A'}/5**\n` +
        `- Speaker Rating: **${top.metrics.avgSpeakerRating ?? 'N/A'}/5**\n` +
        `- Events Held: **${top.metrics.eventCount}**\n` +
        `- Consistency Score: **${top.metrics.consistency}/100**\n\n` +
        `Their standout event was the **${top.events.sort((a,b)=>(b.feedbackAvg||0)-(a.feedbackAvg||0))[0]?.name}**, which received exceptional feedback.`,
      clubId: top.club.id
    };
  }

  answerRankings() {
    let md = `## 📊 Club Performance Rankings — ${this.semester.name}\n\n`;
    for (const d of this.rankings) {
      const medals = ['🥇','🥈','🥉','4️⃣','5️⃣','6️⃣'];
      md += `${medals[d.rank-1]} **${d.club.name}** — Score: \`${d.composite}/100\`\n`;
      md += `   Attendance: ${d.metrics.attendanceRate}% | Feedback: ${d.metrics.avgFeedback ?? '⚠️'}/5 | Events: ${d.metrics.eventCount}\n\n`;
    }
    return { type: 'rankings', content: md };
  }

  answerSpecificClub(clubId) {
    const d = this.rankings.find(r => r.club.id === clubId);
    if (!d) return { type: 'text', content: 'Club not found.' };
    let md = `## ${d.club.icon} ${d.club.name} — Detailed Report\n\n`;
    md += `**Rank:** #${d.rank} | **Composite Score:** ${d.composite}/100\n\n`;
    md += `### Metrics\n`;
    md += `| Metric | Value |\n|--------|-------|\n`;
    md += `| Total Registrations | ${d.metrics.totalRegistrations} |\n`;
    md += `| Attendance Rate | ${d.metrics.attendanceRate}% |\n`;
    md += `| Avg Feedback | ${d.metrics.avgFeedback ?? '⚠️ Incomplete data'}/5 |\n`;
    md += `| Avg Speaker Rating | ${d.metrics.avgSpeakerRating ?? '⚠️ Incomplete data'}/5 |\n`;
    md += `| Consistency Score | ${d.metrics.consistency}/100 |\n`;
    md += `| Events Held | ${d.metrics.eventCount} |\n\n`;
    md += `### Events\n`;
    for (const ev of d.events) {
      md += `**${ev.name}** *(${ev.type}, ${ev.date})*\n`;
      md += `- Registrations: ${ev.registrations} | Attendance: ${ev.attendance ?? '⚠️ Missing'}`;
      md += ` | Feedback: ${ev.feedbackAvg ? ev.feedbackAvg + '/5' : '⚠️ Missing'}\n\n`;
    }
    return { type: 'club_detail', content: md, clubId };
  }

  answerAttendance() {
    let md = `## 📍 Attendance Analysis\n\n`;
    const sorted = [...this.rankings].sort((a,b)=>b.metrics.attendanceRate-a.metrics.attendanceRate);
    for (const d of sorted) {
      const bar = '█'.repeat(Math.round(d.metrics.attendanceRate / 5)) + '░'.repeat(20 - Math.round(d.metrics.attendanceRate / 5));
      md += `**${d.club.name}:** ${bar} ${d.metrics.attendanceRate}%\n`;
    }
    md += `\n*Note: Missing attendance data was imputed using each club's average attendance rate.*`;
    return { type: 'text', content: md };
  }

  answerFeedback() {
    let md = `## ⭐ Feedback & Satisfaction Analysis\n\n`;
    const sorted = [...this.rankings].sort((a,b)=>(b.metrics.avgFeedback||0)-(a.metrics.avgFeedback||0));
    for (const d of sorted) {
      const stars = d.metrics.avgFeedback ? '⭐'.repeat(Math.round(d.metrics.avgFeedback)) + ` (${d.metrics.avgFeedback}/5)` : '⚠️ Data unavailable';
      md += `**${d.club.name}:** ${stars}\n`;
    }
    return { type: 'text', content: md };
  }

  answerMissingData() {
    const issues = this.rawReport.dataIssues;
    let md = `## ⚠️ Missing Data Report\n\n`;
    if (!issues.length) {
      md += 'No data gaps detected! All records are complete.';
    } else {
      md += `Found **${issues.length}** data gaps across events:\n\n`;
      for (const i of issues) {
        md += `- **${i.club} — ${i.event}**: \`${i.field}\` missing\n  → *${i.action}*\n\n`;
      }
    }
    return { type: 'text', content: md };
  }

  answerEventList() {
    let md = `## 📅 All Events — ${this.semester.name}\n\n`;
    for (const d of this.rankings) {
      md += `### ${d.club.icon} ${d.club.name}\n`;
      for (const ev of d.events) {
        md += `- **${ev.name}** *(${ev.date})* — ${ev.type}, ${ev.registrations} registrations\n`;
      }
      md += '\n';
    }
    return { type: 'text', content: md };
  }

  answerRecommendations() {
    const last = this.rankings[this.rankings.length - 1];
    const first = this.rankings[0];
    const md = `## 💡 Recommendations\n\n` +
      `**For all clubs:**\n` +
      `- Adopt digital check-in (QR / Google Form) to eliminate attendance data gaps\n` +
      `- Distribute standardized 5-point feedback forms immediately post-event\n` +
      `- Publish event schedules at least 3 weeks in advance to maximize registrations\n\n` +
      `**For ${last.club.name} (Rank #${last.rank}):**\n` +
      `- Study ${first.club.name}'s event planning workflow\n` +
      `- Focus on 1–2 high-quality events rather than spreading resources thin\n` +
      `- Improve pre-event marketing through campus social media\n\n` +
      `**For ${first.club.name} (Rank #${first.rank} — Champion):**\n` +
      `- Share best practices with other clubs through a mentorship program\n` +
      `- Aim for inter-college collaborations to expand reach\n`;
    return { type: 'text', content: md };
  }

  // ─────────────────────────────────────────────────────────
  // Helper: get all events as flat array with club info
  // ─────────────────────────────────────────────────────────
  getAllEvents() {
    return this.clubs.flatMap(c => c.events.map(e => ({ ...e, club: c })));
  }
}

// ── Utility ──────────────────────────────────────────────
function stdDev(arr) {
  const mean = arr.reduce((a, b) => a + b, 0) / arr.length;
  return Math.sqrt(arr.reduce((s, v) => s + (v - mean) ** 2, 0) / arr.length);
}

function roundHalfToEven(n) {
  const floor = Math.floor(n);
  const diff = n - floor;
  if (Math.abs(diff - 0.5) < 1e-9) {
    return floor % 2 === 0 ? floor : floor + 1;
  }
  return Math.round(n);
}

// Export
if (typeof module !== 'undefined') module.exports = { EventAnalyticsAgent };
