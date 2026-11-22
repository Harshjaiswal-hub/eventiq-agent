// ============================================================
// Smart Event Analytics Agent — UI Controller
// ============================================================

// ── Agent instance ──────────────────────────────────────────
const agent = new EventAnalyticsAgent(CLUBS, SEMESTER);
let agentReady = false;
window.agentReady = false; // expose globally for headless capture scripts
let currentView = 'dashboard';

// ── Authentication & Security State (Phase 2) ───────────────
let currentUser = null;
let currentCsrfToken = null;
let currentDetailClubName = null;
let pendingDecisionData = null;

async function checkAuthStatus() {
  try {
    const res = await fetch('/api/auth/me');
    if (res.ok) {
      const data = await res.json();
      if (data && data.user) {
        currentUser = data.user;
        currentCsrfToken = data.csrf_token;
        updateAuthUI();
        return;
      }
    }
  } catch (e) {}
  currentUser = null;
  currentCsrfToken = null;
  updateAuthUI();
}

function updateAuthUI() {
  const label = document.getElementById('auth-btn-label');
  const icon = document.getElementById('auth-user-icon');
  const btn = document.getElementById('auth-btn');
  if (!label || !btn) return;
  if (currentUser) {
    label.textContent = `${currentUser.username} (${currentUser.role})`;
    if (icon) {
      icon.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`;
    }
    btn.title = `Signed in as ${currentUser.username} (${currentUser.role}). Click to Logout.`;
  } else {
    label.textContent = 'Login';
    if (icon) {
      icon.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;
    }
    btn.title = 'Sign In to EventIQ';
  }
}

function openLoginModal() {
  const m = document.getElementById('login-modal');
  if (m) {
    m.style.display = 'flex';
    document.getElementById('login-username')?.focus();
  }
}

function closeLoginModal() {
  const m = document.getElementById('login-modal');
  if (m) m.style.display = 'none';
  const err = document.getElementById('login-error');
  if (err) err.style.display = 'none';
}

async function handleLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch (e) {}
  currentUser = null;
  currentCsrfToken = null;
  updateAuthUI();
  showToast('Signed out successfully.');
  refreshApprovalsBadge();
  if (currentView === 'approvals') renderApprovalsView();
}

// ── Tab Session Management (Short-Term Memory Isolation) ─────
function getSessionId() {
  let sid = sessionStorage.getItem('eventiq_session_id');
  if (!sid) {
    sid = (typeof crypto !== 'undefined' && crypto.randomUUID) 
      ? 'sess_' + crypto.randomUUID() 
      : 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
    sessionStorage.setItem('eventiq_session_id', sid);
  }
  return sid;
}

// ── Boot sequence ────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  bootAgent();
});

async function bootAgent() {
  updateStatus('Initializing agent…');
  await delay(200);

  // Check institutional auth state
  await checkAuthStatus();

  updateStatus('Connecting to backend analytics engine…');
  let loadedFromBackend = false;
  try {
    const [clubsRes, rankingsRes] = await Promise.all([
      fetch(`/api/clubs?semester=${encodeURIComponent(SEMESTER.name)}`),
      fetch(`/api/rankings?semester=${encodeURIComponent(SEMESTER.name)}`)
    ]);

    if (clubsRes.ok) {
      const clubsData = await clubsRes.json();
      if (clubsData && clubsData.clubs && clubsData.clubs.length > 0) {
        agent.clubs = clubsData.clubs;
      }
    }

    if (rankingsRes.ok) {
      const data = await rankingsRes.json();
      if (data && data.rankings && data.rankings.length > 0) {
        agent.rankings = data.rankings;
        agent.metrics = data.rankings;
        loadedFromBackend = true;
      }
    }
  } catch (err) {
    console.warn("Backend /api/rankings unavailable; falling back to client engine.", err);
  }

  // Ensure local event reports are available for timeline & data quality scanning
  agent.collectData();

  if (!loadedFromBackend) {
    updateStatus('Calculating client-side fallback metrics…');
    agent.calculateCompositeScores();
  }

  await delay(200);
  updateStatus('Building dashboard…');
  renderDashboard();
  refreshApprovalsBadge();
  refreshSavedReportsDropdown();
  updateTimelineCounts();
  await delay(200);

  updateStatus('Ready');
  agentReady = true;
  window.agentReady = true; // signal to headless capture scripts
  showToast(loadedFromBackend ? 'Connected to Python analytics engine (Single Source of Truth).' : 'Agent ready (offline mode).');

  // Welcome message in chat
  appendMessage('agent', `Hello! 👋 I've finished analyzing **${SEMESTER.name}** technical events.\n\nI've processed **${agent.clubs.length} clubs** and **${agent.clubs.reduce((s,c)=>(s+(c.events?c.events.length:0)),0)} events**, including handling missing attendance and feedback data.\n\nAsk me: *"Which club performed best?"* or try a suggested prompt below.`);
}

function updateTimelineCounts() {
  const allEvents = agent.getAllEvents();
  const gapEvents = allEvents.filter(ev => ev.hasMissingAttendance || ev.hasMissingFeedback);
  const countAll = document.getElementById('count-all-events');
  const countGaps = document.getElementById('count-gap-events');
  if (countAll) countAll.textContent = allEvents.length;
  if (countGaps) countGaps.textContent = gapEvents.length;
}

// ── Navigation & Global Actions ──────────────────────────────
document.addEventListener('click', (e) => {
  const navBtn = e.target.closest('[data-nav]');
  if (navBtn) switchView(navBtn.dataset.nav);

  // Club Leaderboard Detail View Interaction
  const clubCard = e.target.closest('[data-club-detail]');
  if (clubCard) {
    openClubDetail(clubCard.dataset.clubDetail);
    return;
  }

  // Club Modal Action Buttons
  if (e.target.closest('#close-club-modal-btn') || e.target.closest('#club-modal-close-action-btn')) {
    closeClubDetail();
    return;
  }
  if (e.target.closest('#club-modal-ask-btn')) {
    const clubName = currentDetailClubName;
    closeClubDetail();
    switchView('chat');
    submitPrompt(`Explain composite score and performance metrics for ${clubName}`);
    return;
  }

  // Password Visibility Toggle
  if (e.target.closest('#toggle-password-btn')) {
    togglePasswordVisibility();
    return;
  }

  // Confirmation Dialog Actions
  if (e.target.closest('#close-confirm-modal-btn') || e.target.closest('#confirm-cancel-btn')) {
    closeConfirmModal();
    return;
  }
  if (e.target.closest('#confirm-proceed-btn')) {
    proceedWithConfirmedDecision();
    return;
  }

  const promptBtn = e.target.closest('[data-prompt]');
  if (promptBtn) submitPrompt(promptBtn.dataset.prompt);
  const sendBtn = e.target.closest('#send-btn');
  if (sendBtn) handleUserSend();
  const exportBtn = e.target.closest('#export-btn');
  if (exportBtn) exportReport();
  const printPdfBtn = e.target.closest('#print-pdf-btn');
  if (printPdfBtn) {
    switchView('report');
    window.print();
  }
  const auditBtn = e.target.closest('#audit-btn');
  if (auditBtn) triggerAiSemesterAudit();
  const decisionBtn = e.target.closest('[data-decision]');
  if (decisionBtn) requestDecisionConfirmation(decisionBtn.dataset.id, decisionBtn.dataset.decision);

  // Timeline Filter Chips & Issues Card
  const filterChip = e.target.closest('.filter-chip');
  if (filterChip && filterChip.dataset.filter) {
    currentTimelineFilter = filterChip.dataset.filter;
    renderEventTimeline();
  }
  const issuesCard = e.target.closest('#sidebar-issues-card');
  if (issuesCard) {
    switchView('events');
    currentTimelineFilter = 'gaps';
    renderEventTimeline();
  }

  // Recommendation Status Filter Buttons (Phase 4)
  const recFilterBtn = e.target.closest('.rec-filter-btn');
  if (recFilterBtn && recFilterBtn.dataset.recFilter) {
    currentRecFilter = recFilterBtn.dataset.recFilter;
    renderApprovalsView();
  }

  // Execution Trace Viewer Toggle
  const traceToggle = e.target.closest('#toggle-trace-btn');
  if (traceToggle) {
    toggleExecutionTrace();
  }

  // Saved Reports Generate Button
  const genReportBtn = e.target.closest('#generate-save-report-btn');
  if (genReportBtn) generateAndSaveReport();

  // Authentication UI triggers
  const authBtn = e.target.closest('#auth-btn');
  if (authBtn) {
    if (currentUser) {
      if (confirm(`Sign out from EventIQ (${currentUser.username})?`)) handleLogout();
    } else {
      openLoginModal();
    }
  }
  const closeLogin = e.target.closest('#close-login-btn');
  if (closeLogin) closeLoginModal();
});

document.addEventListener('change', (e) => {
  if (e.target.id === 'saved-reports-select') {
    renderFullReport();
  }
  if (e.target.id === 'semester-select') {
    handleSemesterChange(e.target.value);
  }
});

document.addEventListener('input', (e) => {
  if (e.target.id === 'timeline-search-input') {
    renderEventTimeline();
  }
});

document.addEventListener('submit', async (e) => {
  if (e.target.id === 'login-form') {
    e.preventDefault();
    const u = document.getElementById('login-username').value.trim();
    const p = document.getElementById('login-password').value;
    const errEl = document.getElementById('login-error');
    if (errEl) errEl.style.display = 'none';

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        currentUser = data.user;
        currentCsrfToken = data.csrf_token;
        closeLoginModal();
        updateAuthUI();
        showToast(`Signed in as ${currentUser.username} (${currentUser.role})`);
        refreshApprovalsBadge();
        if (currentView === 'approvals') renderApprovalsView();
      } else {
        if (errEl) {
          errEl.textContent = data.message || 'Invalid username or password';
          errEl.style.display = 'block';
        }
      }
    } catch (err) {
      if (errEl) {
        errEl.textContent = 'Server connection failed';
        errEl.style.display = 'block';
      }
    }
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.target.id === 'chat-input') handleUserSend();
  if ((e.key === 'Enter' || e.key === ' ') && e.target.hasAttribute('data-prompt')) {
    e.preventDefault();
    submitPrompt(e.target.dataset.prompt);
  }
  // Escape closes any open modal
  if (e.key === 'Escape') {
    const clubModal = document.getElementById('club-detail-modal');
    if (clubModal && clubModal.style.display !== 'none') { closeClubDetail(); return; }
    const confirmModal = document.getElementById('decision-confirm-modal');
    if (confirmModal && confirmModal.style.display !== 'none') { closeConfirmModal(); return; }
    const loginModal = document.getElementById('login-modal');
    if (loginModal && loginModal.style.display !== 'none') { closeLoginModal(); return; }
  }
});

function switchView(view) {
  currentView = view;
  document.querySelectorAll('[data-nav]').forEach(b => b.classList.remove('active'));
  document.querySelector(`[data-nav="${view}"]`)?.classList.add('active');
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById(`view-${view}`)?.classList.add('active');
  if (view === 'dashboard') renderDashboard();
  if (view === 'events') renderEventTimeline();
  if (view === 'report') renderFullReport();
  if (view === 'approvals') renderApprovalsView();
}

// ── Flagship Multi-Agent Semester Audit Trigger ───────────────
async function triggerAiSemesterAudit() {
  switchView('chat');
  await submitPrompt("Analyze all technical clubs for Spring 2026, compare them with the previous semester if data exists, identify the lowest-performing club, and prepare an evidence-based improvement plan.");
}

// ── Chat & Backend Agent Orchestration ────────────────────────
async function handleUserSend() {
  const input = document.getElementById('chat-input');
  const q = input.value.trim();
  if (!q) return;
  input.value = '';
  await submitPrompt(q);
}

async function submitPrompt(query) {
  if (!agentReady) { showToast('Agent is still initializing…'); return; }
  switchView('chat');
  appendMessage('user', query);
  const thinking = appendThinking();

  // Simulate thinking steps
  const steps = getThinkingSteps(query);
  for (const step of steps) {
    thinking.querySelector('.thinking-step').textContent = step;
    await delay(320);
  }

  // Attempt backend API call first for genuine multi-agent execution
  let responseContent = null;
  const sessionId = getSessionId();
  try {
    const res = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: query, session_id: sessionId, semester: SEMESTER.name })
    });
    if (res.ok) {
      const data = await res.json();
      if (data && data.content) {
        responseContent = data.content;
      }
    }
  } catch (err) {
    console.warn("Backend API not reachable; falling back to local engine.", err);
  }

  // Fallback to local rule engine if backend is offline or during pure static preview
  if (!responseContent) {
    const localRes = agent.respond(query);
    responseContent = localRes.content || localRes;
  }

  thinking.remove();
  appendMessage('agent', responseContent);

  // Fetch updated execution trace after agent activity
  await fetchExecutionTrace(sessionId);
}

// ── Agent Execution Trace Viewer (Phase 3) ───────────────────
let isTraceOpen = false;

function toggleExecutionTrace() {
  const drawer = document.getElementById('trace-viewer-drawer');
  if (!drawer) return;
  isTraceOpen = !isTraceOpen;
  drawer.style.display = isTraceOpen ? 'block' : 'none';
  if (isTraceOpen) {
    fetchExecutionTrace(getSessionId());
  }
}

async function fetchExecutionTrace(sessionId) {
  if (!sessionId) sessionId = getSessionId();
  const listEl = document.getElementById('trace-logs-list');
  const countEl = document.getElementById('trace-step-count');
  if (!listEl) return;

  try {
    const res = await fetch(`/api/logs/execution?session_id=${encodeURIComponent(sessionId)}`);
    if (res.ok) {
      const data = await res.json();
      const logs = data.logs || [];
      if (countEl) countEl.textContent = `${logs.length} Steps`;

      if (logs.length === 0) {
        listEl.innerHTML = '<div style="color:var(--text-mute); padding:4px 0;">No multi-agent trace events recorded for this session yet. Run an audit or submit a prompt to view agent interactions.</div>';
        return;
      }

      const agentColors = {
        supervisor: '#6366f1',
        data_analyst: '#0ea5e9',
        research_insight: '#10b981',
        recommendation_agent: '#f59e0b',
        reviewer_agent: '#ec4899'
      };

      listEl.innerHTML = logs.map(log => {
        const color = agentColors[log.agent_name] || '#8b5cf6';
        let detailStr = '';
        if (log.tool_called) {
          detailStr += `<strong>Tool:</strong> <code>${escapeHtml(log.tool_called)}</code> `;
        }
        if (log.execution_time_ms) {
          detailStr += `(${log.execution_time_ms.toFixed(1)}ms) `;
        }
        if (log.error_message) {
          detailStr += `<span style="color:#ef4444;">Error: ${escapeHtml(log.error_message)}</span>`;
        } else if (log.tool_output_summary) {
          detailStr += `<span style="color:var(--text-dim);">${escapeHtml(log.tool_output_summary)}</span>`;
        }

        return `
          <div style="background:rgba(255,255,255,0.03); border-left:3px solid ${color}; padding:6px 10px; border-radius:4px; display:flex; flex-direction:column; gap:2px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span style="font-weight:600; color:${color}; font-size:11px;">${escapeHtml(log.agent_name ? log.agent_name.toUpperCase() : 'AGENT')} · ${escapeHtml(log.step_description || '')}</span>
              <span style="color:var(--text-mute); font-size:10px;">${escapeHtml(log.created_at || '')}</span>
            </div>
            ${detailStr ? `<div style="font-size:10.5px; color:var(--text-dim);">${detailStr}</div>` : ''}
          </div>
        `;
      }).join('');
    }
  } catch (err) {
    console.warn("Could not fetch execution trace:", err);
  }
}

function getThinkingSteps(query) {
  const q = query.toLowerCase();
  const base = ['🤖 Supervisor: Routing query…', '📊 Data Analyst: Computing verified metrics…', '🧮 Reviewer: Auditing claims…'];
  if (q.match(/predict|forecast|expected to attend|how many students|turnout/)) return [
    '🔮 Predictive Intelligence: Fetching club historical event logs…',
    '📈 Trend Analysis: Calculating registration momentum and turnout rates…',
    '🎯 Statistical Baseline: Computing confidence bounds & variance…',
    '📜 Provenance Audit: Identifying benchmark influencing events…',
    '📝 Finalizing predictive forecast…'
  ];
  if (q.match(/plan|budget|budget optimizer|plan a technical event/)) return [
    '💡 Planning Optimizer: Analyzing club historical event performance…',
    '💰 Budget Allocation: Calculating prize, catering, and infrastructure items…',
    '🎤 Speaker Strategy: Auditing past guest speaker ratings…',
    '🛡️ Risk Assessment: Generating mitigation & contingency matrix…',
    '📋 Finalizing event execution proposal…'
  ];
  if (q.match(/audit|flagship|multi-agent/)) return [
    '🤖 Supervisor: Initializing 4-Agent Team…',
    '📊 Data Analyst: Calculating 5-metric composite scores…',
    '🔎 Research Agent: Retrieving institutional rubrics…',
    '💡 Recommendation Agent: Formulating evidence-backed actions…',
    '⚖️ Reviewer Agent: Auditing numerical consistency…',
    '✅ Supervisor: Compiling final audit report…'
  ];
  if (q.match(/best|top|winner/)) return [...base, '🏆 Identifying top performer…', '📝 Composing explanation…'];
  if (q.match(/rank|compare/)) return [...base, '📊 Sorting by composite score…', '📝 Generating ranking table…'];
  if (q.match(/attend/)) return [...base, '📍 Aggregating attendance data…', '⚠️ Handling missing records…', '📝 Computing rates…'];
  if (q.match(/feedback|rating/)) return [...base, '⭐ Averaging feedback scores…', '⚠️ Flagging incomplete responses…'];
  if (q.match(/missing|gap/)) return ['🔎 Scanning for null values…', '📋 Cataloguing data gaps…', '🔧 Reporting imputation decisions…'];
  if (q.match(/report|summary|analyze/)) return ['📦 Collecting all data…', '🧮 Computing metrics…', '📊 Ranking clubs…', '📝 Writing report…', '✅ Finalizing…'];
  return [...base, '📝 Generating response…'];
}

function appendMessage(role, content) {
  const feed = document.getElementById('chat-feed');
  const div = document.createElement('div');
  div.className = `msg msg-${role}`;
  div.innerHTML = `
    <div class="msg-avatar">${role === 'agent' ? '🤖' : '👤'}</div>
    <div class="msg-bubble">${renderMarkdown(content)}</div>
  `;
  feed.appendChild(div);
  feed.scrollTop = feed.scrollHeight;
  return div;
}

function appendThinking() {
  const feed = document.getElementById('chat-feed');
  const div = document.createElement('div');
  div.className = 'msg msg-agent msg-thinking';
  div.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble thinking-bubble">
      <div class="thinking-dots"><span></span><span></span><span></span></div>
      <div class="thinking-step">Analyzing…</div>
    </div>
  `;
  feed.appendChild(div);
  feed.scrollTop = feed.scrollHeight;
  return div;
}

// ── HTML Sanitizer & Markdown renderer ──────────────────────
function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderMarkdown(md) {
  if (!md) return '';
  // Step 1: Escape all raw HTML entities first to prevent XSS
  const safe = escapeHtml(md);

  // Step 2: Convert standard markdown elements safely
  return safe
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/^(#{1,3})\s+(.*)/gm, (_, h, t) => `<h${h.length+1}>${t}</h${h.length+1}>`)
    .replace(/^&gt;\s*(.+)/gm, '<blockquote>$1</blockquote>')
    .replace(/^\| (.+) \|$/gm, (line) => {
      const cells = line.split('|').filter(c => c.trim()).map(c => `<td>${c.trim()}</td>`).join('');
      return `<tr>${cells}</tr>`;
    })
    .replace(/(<tr>.*<\/tr>\n?)+/g, m => `<table>${m}</table>`)
    .replace(/^-{3,}$/gm, '<hr>')
    .replace(/^- (.+)/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>')
    .replace(/^([^<])/gm, (m) => m);
}

// ── Dashboard ─────────────────────────────────────────────────
function renderDashboard() {
  if (!agent.rankings) return;
  const r = agent.rankings;

  // KPI cards
  const totalEvents = CLUBS.reduce((s, c) => s + c.events.length, 0);
  const totalReg = r.reduce((s, d) => s + d.metrics.totalRegistrations, 0);
  const totalAtt = r.reduce((s, d) => s + d.metrics.totalAttendance, 0);
  const fbClubs = r.filter(d => d.metrics.avgFeedback !== null && !isNaN(d.metrics.avgFeedback));
  const avgFb = fbClubs.length > 0 
    ? +(fbClubs.reduce((s, d) => s + d.metrics.avgFeedback, 0) / fbClubs.length).toFixed(2)
    : 0;

  document.getElementById('kpi-events').textContent = totalEvents;
  document.getElementById('kpi-registrations').textContent = totalReg.toLocaleString();
  document.getElementById('kpi-attendance').textContent = totalReg > 0 ? (Math.round(totalAtt / totalReg * 100) + '%') : '0%';
  document.getElementById('kpi-feedback').textContent = avgFb + '/5';

  // Leaderboard
  renderLeaderboard();

  // Bar chart
  drawBarChart();

  // Radar chart
  drawRadarChart();

  // Data issues badge
  const issues = agent.rawReport?.dataIssues?.length || 0;
  const badge = document.getElementById('data-issues-badge');
  if (badge) badge.textContent = issues + ' gaps handled';
}

function renderLeaderboard() {
  const el = document.getElementById('leaderboard');
  if (!el) return;
  el.innerHTML = agent.rankings.map((d, i) => {
    let rankBadgeClass = 'rank-badge-other';
    if (d.rank === 1) rankBadgeClass = 'rank-badge-1';
    else if (d.rank === 2) rankBadgeClass = 'rank-badge-2';
    else if (d.rank === 3) rankBadgeClass = 'rank-badge-3';
    
    const rankBadge = `<span class="rank-badge ${rankBadgeClass}">#${d.rank}</span>`;
    const width = Math.round(d.composite);
    const xai = d.xai_attribution;
    const xaiBadge = xai ? `
      <div class="lb-xai-row">
        <span class="xai-driver">▲ <strong>Driver:</strong> ${escapeHtml(xai.primary_driver)}</span>
        <span class="xai-detractor">▼ <strong>Detractor:</strong> ${escapeHtml(xai.primary_detractor)}</span>
      </div>
    ` : '';

    return `
    <div class="lb-card" role="button" tabindex="0" aria-label="${escapeHtml(d.club.name)} rank ${d.rank} score ${d.composite}" style="--club-color: ${d.club.color}; cursor: pointer;" data-club-detail="${escapeHtml(d.club.name)}">
      <div class="lb-card-main">
        <div class="lb-rank">${rankBadge}</div>
        <div class="lb-icon">${d.club.icon}</div>
        <div class="lb-info">
          <div class="lb-title-row">
            <span class="lb-name">${escapeHtml(d.club.name)}</span>
          </div>
          <div class="lb-tagline">${escapeHtml(d.club.tagline)}</div>
          <div class="lb-bar-wrap">
            <div class="lb-bar" style="width: ${width}%; background: ${d.club.color}"></div>
          </div>
        </div>
        <div class="lb-score-pill">
          <div class="lb-score">${d.composite.toFixed(1)}</div>
          <span>/100</span>
        </div>
      </div>
      ${xaiBadge}
    </div>`;
  }).join('');
}

// ── Bar Chart (Canvas) ────────────────────────────────────────
function drawBarChart() {
  const canvas = document.getElementById('bar-chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.parentElement.clientWidth || canvas.offsetWidth || 500;
  const h = canvas.parentElement.clientHeight || canvas.offsetHeight || 260;
  canvas.width = w * dpr; canvas.height = h * dpr;
  ctx.scale(dpr, dpr);

  const data = agent.rankings;
  if (!data || data.length === 0) return;

  const pad = { top: 28, right: 20, bottom: 44, left: 40 };
  const cw = Math.max(10, w - pad.left - pad.right);
  const ch = Math.max(10, h - pad.top - pad.bottom);
  const barW = Math.min(36, Math.max(16, (cw / data.length) * 0.48));
  const gap = cw / data.length;

  ctx.clearRect(0, 0, w, h);

  // Subtle Grid lines
  ctx.strokeStyle = 'rgba(148, 163, 184, 0.09)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const y = pad.top + ch - (ch * i / 5);
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(w - pad.right, y);
    ctx.stroke();
    
    ctx.fillStyle = '#64748B';
    ctx.font = '500 10px JetBrains Mono, monospace';
    ctx.textAlign = 'right';
    ctx.fillText((i * 20).toString(), pad.left - 8, y + 3.5);
  }

  // Bars
  data.forEach((d, i) => {
    const x = pad.left + i * gap + (gap - barW) / 2;
    const barH = Math.max(4, (d.composite / 100) * ch);
    const y = pad.top + ch - barH;

    // Gradient bar fill with enterprise contrast
    const grad = ctx.createLinearGradient(0, y, 0, y + barH);
    grad.addColorStop(0, d.club.color);
    grad.addColorStop(1, d.club.color + '33');
    ctx.fillStyle = grad;
    
    // Rounded top corners
    const r2 = Math.min(4, barW / 2, barH / 2);
    ctx.beginPath();
    ctx.moveTo(x + r2, y);
    ctx.lineTo(x + barW - r2, y);
    ctx.quadraticCurveTo(x + barW, y, x + barW, y + r2);
    ctx.lineTo(x + barW, y + barH);
    ctx.lineTo(x, y + barH);
    ctx.lineTo(x, y + r2);
    ctx.quadraticCurveTo(x, y, x + r2, y);
    ctx.closePath();
    ctx.fill();

    // Subtle crisp border
    ctx.strokeStyle = d.club.color;
    ctx.lineWidth = 1.2;
    ctx.stroke();

    // Score label on top of bar
    ctx.fillStyle = '#F8FAFC';
    ctx.font = '600 11px JetBrains Mono, monospace';
    ctx.textAlign = 'center';
    ctx.fillText(d.composite.toFixed(1), x + barW / 2, y - 6);

    // Club name label below axis
    ctx.fillStyle = '#CBD5E1';
    ctx.font = '500 11px Inter, sans-serif';
    ctx.fillText(d.club.name, x + barW / 2, pad.top + ch + 18);
    
    // Club icon below name
    ctx.font = '12px Inter, sans-serif';
    ctx.fillText(d.club.icon, x + barW / 2, pad.top + ch + 33);
  });
}

// ── Radar Chart ───────────────────────────────────────────────
function updateRadarLegend() {
  const container = document.getElementById('radar-legend-container');
  if (!container || !agent.rankings) return;
  const topClubs = agent.rankings.slice(0, 3);
  container.innerHTML = topClubs.map(d => `
    <span class="radar-legend-item">
      <span class="radar-dot" style="background:${d.club.color};"></span>
      #${d.rank} ${escapeHtml(d.club.name)}
    </span>
  `).join('');
}

function drawRadarChart() {
  const canvas = document.getElementById('radar-chart');
  if (!canvas || !agent.rankings || agent.rankings.length === 0) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  
  // Sync the legend dynamically with verified rankings
  updateRadarLegend();

  // Responsive dimensions from container with generous padding to prevent label clipping
  const wrap = canvas.parentElement;
  const availableWidth = wrap ? wrap.clientWidth : canvas.offsetWidth;
  const availableHeight = wrap ? wrap.clientHeight : canvas.offsetHeight;
  const size = Math.max(180, Math.min(availableWidth || 300, availableHeight || 240));

  canvas.width = size * dpr;
  canvas.height = size * dpr;
  canvas.style.width = size + 'px';
  canvas.style.height = size + 'px';
  ctx.scale(dpr, dpr);

  const cx = size / 2;
  const cy = size / 2;
  // Radius carefully bounded at size * 0.29 so outer labels with offset +18px stay well within bounds
  const r = size * 0.285;
  const axes = ['Attendance', 'Feedback', 'Speaker', 'Events', 'Consistency'];
  const keys = ['attendanceRate', 'avgFeedback', 'avgSpeakerRating', 'eventCount', 'consistency'];
  const maxEvents = Math.max(4, ...agent.rankings.map(d => d.metrics.eventCount || 0));
  const maxes = [100, 5, 5, maxEvents, 100];
  const n = axes.length;

  ctx.clearRect(0, 0, size, size);

  // Concentric polygon web
  for (let ring = 1; ring <= 5; ring++) {
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
      const x = cx + Math.cos(angle) * r * ring / 5;
      const y = cy + Math.sin(angle) * r * ring / 5;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = ring === 5 ? 'rgba(148, 163, 184, 0.22)' : 'rgba(148, 163, 184, 0.10)';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  // Radial Axis lines + readable labels (with bounds protection)
  for (let i = 0; i < n; i++) {
    const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r;
    
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(x, y);
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.16)';
    ctx.stroke();

    // Smart label offset and alignment to prevent clipped or overlapping text
    const labelDist = r + 18;
    const lx = cx + Math.cos(angle) * labelDist;
    const ly = cy + Math.sin(angle) * labelDist;
    
    ctx.fillStyle = '#CBD5E1';
    ctx.font = '600 10.5px Inter, sans-serif';
    
    // Compute textAlign and textBaseline relative to position to prevent clipping
    const cosVal = Math.cos(angle);
    if (Math.abs(cosVal) < 0.15) {
      ctx.textAlign = 'center';
    } else if (cosVal > 0) {
      ctx.textAlign = 'left';
    } else {
      ctx.textAlign = 'right';
    }

    const sinVal = Math.sin(angle);
    if (sinVal < -0.6) {
      ctx.textBaseline = 'bottom';
    } else if (sinVal > 0.6) {
      ctx.textBaseline = 'top';
    } else {
      ctx.textBaseline = 'middle';
    }

    ctx.fillText(axes[i], lx, ly);
  }

  // Draw top 3 clubs with clear contrasting stroke/fill from single-source rankings
  agent.rankings.slice(0, 3).forEach((d, idx) => {
    ctx.beginPath();
    keys.forEach((k, i) => {
      const val = d.metrics[k] || 0;
      const norm = Math.min(1.0, val / maxes[i]);
      const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
      const x = cx + Math.cos(angle) * r * norm;
      const y = cy + Math.sin(angle) * r * norm;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.fillStyle = d.club.color + (idx === 0 ? '28' : '18');
    ctx.strokeStyle = d.club.color;
    ctx.lineWidth = idx === 0 ? 2.5 : 1.8;
    ctx.fill();
    ctx.stroke();

    // Data points on vertices
    keys.forEach((k, i) => {
      const val = d.metrics[k] || 0;
      const norm = Math.min(1.0, val / maxes[i]);
      const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
      const px = cx + Math.cos(angle) * r * norm;
      const py = cy + Math.sin(angle) * r * norm;
      ctx.beginPath();
      ctx.arc(px, py, 2.5, 0, Math.PI * 2);
      ctx.fillStyle = d.club.color;
      ctx.fill();
    });
  });
}

// ── Event Timeline & Interactive Data-Quality Filtering (Phase 3) ──
let currentTimelineFilter = 'all';

function renderEventTimeline() {
  const el = document.getElementById('timeline-container');
  if (!el) return;
  let allEvents = agent.getAllEvents().sort((a, b) => new Date(a.date) - new Date(b.date));

  // Update counts
  const totalCount = allEvents.length;
  const gapCount = allEvents.filter(ev => ev.hasMissingAttendance || ev.hasMissingFeedback).length;
  const countAll = document.getElementById('count-all-events');
  const countGaps = document.getElementById('count-gap-events');
  if (countAll) countAll.textContent = totalCount;
  if (countGaps) countGaps.textContent = gapCount;

  // Filter based on active selection
  if (currentTimelineFilter === 'gaps') {
    allEvents = allEvents.filter(ev => ev.hasMissingAttendance || ev.hasMissingFeedback);
  } else if (currentTimelineFilter && currentTimelineFilter !== 'all') {
    allEvents = allEvents.filter(ev => ev.type === currentTimelineFilter);
  }

  // Filter based on interactive search input
  const searchInput = document.getElementById('timeline-search-input');
  const sq = searchInput ? searchInput.value.toLowerCase().trim() : '';
  if (sq) {
    allEvents = allEvents.filter(ev => 
      (ev.name && ev.name.toLowerCase().includes(sq)) ||
      (ev.club && ev.club.name && ev.club.name.toLowerCase().includes(sq)) ||
      (ev.type && ev.type.toLowerCase().includes(sq))
    );
  }

  // Update filter chip UI active states
  document.querySelectorAll('.filter-chip').forEach(btn => {
    if (btn.dataset.filter === currentTimelineFilter) {
      btn.classList.add('active');
      btn.style.background = currentTimelineFilter === 'gaps' ? 'var(--amber)' : 'var(--primary)';
      btn.style.color = '#fff';
      btn.style.borderColor = 'transparent';
    } else {
      btn.classList.remove('active');
      btn.style.background = 'var(--surface2)';
      btn.style.color = btn.dataset.filter === 'gaps' ? 'var(--amber)' : 'var(--text-dim)';
      btn.style.borderColor = btn.dataset.filter === 'gaps' ? 'var(--amber)' : 'var(--border)';
    }
  });

  if (allEvents.length === 0) {
    el.innerHTML = '<div style="color:var(--text-mute); padding:24px 0; text-align:center;">No events match the selected filter.</div>';
    return;
  }

  // Group by month
  const byMonth = {};
  for (const ev of allEvents) {
    const m = new Date(ev.date).toLocaleString('default', { month: 'long', year: 'numeric' });
    if (!byMonth[m]) byMonth[m] = [];
    byMonth[m].push(ev);
  }

  el.innerHTML = Object.entries(byMonth).map(([month, events]) => `
    <div class="timeline-month">
      <div class="timeline-month-label">${month}</div>
      <div class="timeline-events">
        ${events.map(ev => `
          <div class="timeline-event" style="--club-color: ${ev.club.color}" data-prompt="Tell me about ${ev.club.name}">
            <div class="te-icon">${ev.club.icon}</div>
            <div class="te-info">
              <div class="te-name">${escapeHtml(ev.name)}</div>
              <div class="te-meta">${escapeHtml(ev.club.name)} · ${escapeHtml(ev.type)} · ${escapeHtml(ev.date)}</div>
              <div class="te-stats">
                <span>${ev.registrations} registered</span>
                ${ev.attendance !== null && ev.attendance !== undefined ? `<span>${ev.attendance} attended</span>` : '<span class="warn">⚠️ Attendance missing</span>'}
                ${ev.feedbackAvg ? `<span>⭐ ${ev.feedbackAvg}/5</span>` : '<span class="warn">⚠️ Feedback missing</span>'}
              </div>
            </div>
            <div class="te-type-badge">${escapeHtml(ev.type)}</div>
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');
}

// ── Saved Reports Archive & Generator (Phase 3) ────────────────
let currentReportMarkdown = null;

async function refreshSavedReportsDropdown() {
  const select = document.getElementById('saved-reports-select');
  if (!select) return;

  try {
    const res = await fetch(`/api/reports?semester=${encodeURIComponent(SEMESTER.name)}`);
    if (res.ok) {
      const data = await res.json();
      const reports = data.reports || [];
      const currentVal = select.value;

      select.innerHTML = '<option value="live">Current Session Report (Live)</option>' +
        reports.map(r => `<option value="${escapeHtml(r.id)}">${escapeHtml(r.title)} (${r.created_at})</option>`).join('');

      if (currentVal && Array.from(select.options).some(o => o.value === currentVal)) {
        select.value = currentVal;
      }
    }
  } catch (err) {
    console.warn("Could not refresh saved reports:", err);
  }
}

async function renderFullReport() {
  const el = document.getElementById('report-content');
  if (!el) return;

  const select = document.getElementById('saved-reports-select');
  const selectedReportId = select ? select.value : 'live';

  if (!selectedReportId || selectedReportId === 'live') {
    currentReportMarkdown = agent.generateReport();
    el.innerHTML = renderMarkdown(currentReportMarkdown);
  } else {
    el.innerHTML = '<div style="color:var(--text-mute);">Loading archived report from database...</div>';
    try {
      const res = await fetch(`/api/reports?id=${encodeURIComponent(selectedReportId)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.reports && data.reports.length > 0 && data.reports[0].markdown) {
          currentReportMarkdown = data.reports[0].markdown;
          el.innerHTML = renderMarkdown(currentReportMarkdown);
        } else {
          currentReportMarkdown = agent.generateReport();
          el.innerHTML = renderMarkdown(currentReportMarkdown);
        }
      }
    } catch (err) {
      console.warn("Could not fetch archived report:", err);
      currentReportMarkdown = agent.generateReport();
      el.innerHTML = renderMarkdown(currentReportMarkdown);
    }
  }

  // Metrics table
  const table = document.getElementById('metrics-table-body');
  if (table) {
    table.innerHTML = agent.rankings.map(d => `
      <tr>
        <td><span class="club-dot" style="background:${d.club.color}"></span>${d.club.icon} ${d.club.name}</td>
        <td class="rank-cell">#${d.rank}</td>
        <td>${d.composite}</td>
        <td>${d.metrics.totalRegistrations}</td>
        <td>${d.metrics.attendanceRate}%</td>
        <td>${d.metrics.avgFeedback ?? '<span class="warn">⚠</span>'}</td>
        <td>${d.metrics.avgSpeakerRating ?? '<span class="warn">⚠</span>'}</td>
        <td>${d.metrics.eventCount}</td>
        <td>${d.metrics.consistency}</td>
      </tr>
    `).join('');
  }
}

async function generateAndSaveReport() {
  if (!currentUser || currentUser.role !== 'ADMIN') {
    showToast('Administrator privileges required to archive official reports.');
    openLoginModal();
    return;
  }

  const btn = document.getElementById('generate-save-report-btn');
  if (btn) btn.disabled = true;
  showToast('Generating institutional report and saving to database...');

  try {
    const res = await fetch('/api/reports/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': currentCsrfToken || ''
      },
      body: JSON.stringify({ semester: SEMESTER.name })
    });
    const data = await res.json();
    if (res.ok && data.status === 'success') {
      showToast('Report generated and saved to archive!');
      await refreshSavedReportsDropdown();
      const select = document.getElementById('saved-reports-select');
      if (select && select.options.length > 1) {
        select.selectedIndex = 1; // Select the newly created report
      }
      await renderFullReport();
    } else {
      showToast(data.message || 'Failed to generate report');
    }
  } catch (err) {
    showToast('Error generating report: Server connection failed');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── Export ────────────────────────────────────────────────────
function exportReport() {
  const report = currentReportMarkdown || agent.generateReport();
  // Derive filename from active semester; sanitize filesystem-unsafe chars
  const semesterSlug = (SEMESTER.name || 'Report')
    .replace(/[\\/:*?"<>|]/g, '')   // strip Windows/Unix illegal chars
    .replace(/\s+/g, '_')           // spaces → underscores
    .replace(/_+/g, '_')            // collapse runs of underscores
    .replace(/^_|_$/g, '');         // trim leading/trailing underscores
  const filename = `EventIQ_${semesterSlug}_Report.md`;
  const blob = new Blob([report], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  showToast(`Report exported as ${filename}`);
}

// ── Approvals & Human Review View (Phase 4 Tracking) ──────────
let currentRecFilter = 'all';

async function refreshApprovalsBadge() {
  const badge = document.getElementById('approvals-badge');
  if (!badge) return;
  try {
    const res = await fetch('/api/recommendations');
    if (res.ok) {
      const data = await res.json();
      const recs = data.recommendations || [];
      const pendingCount = recs.filter(r => r.status === 'pending').length;
      if (pendingCount > 0) {
        badge.textContent = pendingCount;
        badge.style.display = 'inline-block';
      } else {
        badge.style.display = 'none';
      }
    }
  } catch (err) {
    // Offline
  }
}

async function renderApprovalsView() {
  const container = document.getElementById('recommendations-container');
  if (!container) return;

  container.innerHTML = '<div style="color:var(--text-mute);">Fetching recommendation queue from database...</div>';

  let recs = [];
  try {
    const res = await fetch('/api/recommendations');
    if (res.ok) {
      const data = await res.json();
      recs = data.recommendations || [];
    }
  } catch (err) {
    console.warn("Backend API offline; showing local baseline recommendations.");
  }

  // Update badge whenever recommendations are loaded
  const pendingCount = recs.filter(r => r.status === 'pending').length;
  const badge = document.getElementById('approvals-badge');
  if (badge) {
    if (pendingCount > 0) {
      badge.textContent = pendingCount;
      badge.style.display = 'inline-block';
    } else {
      badge.style.display = 'none';
    }
  }

  // Fallback if backend offline
  if (recs.length === 0) {
    recs = [
      { id: 'rec_1', semester: 'Spring 2026', club_id: 'cloudnine', recommendation_text: 'Implement compulsory pre-event RSVP reminders to increase attendance rate from 68.3% to over 80%.', evidence_metric: 'attendance_rate = 68.3%', status: 'pending' },
      { id: 'rec_2', semester: 'Spring 2026', club_id: 'all', recommendation_text: 'Standardize digital check-in across all technical clubs using QR verification to eradicate missing attendance logs.', evidence_metric: 'missing_attendance = 3 events', status: 'pending' },
      { id: 'rec_3', semester: 'Spring 2026', club_id: 'codecraft', recommendation_text: 'Organize peer-led technical workshops where CodeCraft mentors other clubs on hackathon engagement.', evidence_metric: 'rank = 1, composite = 94.2', status: 'approved' }
    ];
  }

  // Update filter buttons styling
  document.querySelectorAll('.rec-filter-btn').forEach(btn => {
    if (btn.dataset.recFilter === currentRecFilter) {
      btn.classList.add('active');
      btn.style.background = 'var(--primary)';
      btn.style.color = '#fff';
      btn.style.borderColor = 'transparent';
    } else {
      btn.classList.remove('active');
      btn.style.background = 'var(--surface2)';
      btn.style.color = 'var(--text-dim)';
      btn.style.borderColor = 'var(--border)';
    }
  });

  const filteredRecs = (currentRecFilter === 'all') 
    ? recs 
    : recs.filter(r => r.status === currentRecFilter);

  if (filteredRecs.length === 0) {
    container.innerHTML = `<div style="color:var(--text-mute); padding:16px 0; text-align:center;">No recommendations with status '${escapeHtml(currentRecFilter)}'.</div>`;
    return;
  }

  container.innerHTML = filteredRecs.map(r => {
    const statusBadges = {
      pending: '<span class="status-badge" style="background:rgba(245,158,11,0.12); color:#f59e0b; border:1px solid rgba(245,158,11,0.3); font-size:11px; padding:3px 8px; border-radius:4px; font-weight:600; display:inline-flex; align-items:center; gap:4px;"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> PENDING</span>',
      approved: '<span class="status-badge" style="background:rgba(16,185,129,0.12); color:#10b981; border:1px solid rgba(16,185,129,0.3); font-size:11px; padding:3px 8px; border-radius:4px; font-weight:600; display:inline-flex; align-items:center; gap:4px;"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> APPROVED</span>',
      completed: '<span class="status-badge" style="background:rgba(14,165,233,0.12); color:#0ea5e9; border:1px solid rgba(14,165,233,0.3); font-size:11px; padding:3px 8px; border-radius:4px; font-weight:600; display:inline-flex; align-items:center; gap:4px;"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg> COMPLETED</span>',
      rejected: '<span class="status-badge" style="background:rgba(239,68,68,0.12); color:#ef4444; border:1px solid rgba(239,68,68,0.3); font-size:11px; padding:3px 8px; border-radius:4px; font-weight:600; display:inline-flex; align-items:center; gap:4px;"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg> REJECTED</span>',
      revision_requested: '<span class="status-badge" style="background:rgba(168,85,247,0.12); color:#a855f7; border:1px solid rgba(168,85,247,0.3); font-size:11px; padding:3px 8px; border-radius:4px; font-weight:600; display:inline-flex; align-items:center; gap:4px;"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg> REVISION REQ.</span>'
    };
    const b = statusBadges[r.status] || r.status;

    let actionsHtml = '';
    if (r.status === 'pending') {
      actionsHtml = `
        <div style="display:flex; gap:8px; margin-top:10px;">
          <button class="btn btn-secondary" data-id="${escapeHtml(r.id)}" data-decision="approved" style="background:rgba(16,185,129,0.12); color:#10b981; border:1px solid rgba(16,185,129,0.3); font-size:12px; padding:6px 14px;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            <span>Approve</span>
          </button>
          <button class="btn btn-secondary" data-id="${escapeHtml(r.id)}" data-decision="rejected" style="background:rgba(239,68,68,0.12); color:#ef4444; border:1px solid rgba(239,68,68,0.3); font-size:12px; padding:6px 14px;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            <span>Reject</span>
          </button>
          <button class="btn btn-secondary" data-id="${escapeHtml(r.id)}" data-decision="revision_requested" style="background:var(--surface3); color:var(--text-dim); border:1px solid var(--border); font-size:12px; padding:6px 14px;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
            <span>Request Revision</span>
          </button>
        </div>
      `;
    } else if (r.status === 'approved') {
      actionsHtml = `
        <div style="display:flex; gap:8px; margin-top:10px;">
          <button class="btn btn-secondary" data-id="${escapeHtml(r.id)}" data-decision="completed" style="background:rgba(14,165,233,0.12); color:#0ea5e9; border:1px solid rgba(14,165,233,0.3); font-size:12px; padding:6px 14px;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
            <span>Mark Completed</span>
          </button>
        </div>
      `;
    }

    const borderColor = r.status === 'completed' ? '#0ea5e9' : (r.status === 'approved' ? '#10b981' : (r.status === 'rejected' ? '#ef4444' : 'var(--primary)'));

    return `
      <div class="panel" style="display:flex; flex-direction:column; gap:8px; border-left: 3px solid ${borderColor}; padding:14px 16px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div style="font-weight:600; font-size:14px; color:var(--text);">${escapeHtml(r.club_id ? r.club_id.toUpperCase() : 'ALL')} — ${escapeHtml(r.semester)}</div>
          <div>${b}</div>
        </div>
        <div style="font-size:13px; color:var(--text); line-height:1.5;">${escapeHtml(r.recommendation_text)}</div>
        <div style="font-size:11px; color:var(--text-mute);"><strong>Evidence Metric:</strong> <code style="font-family:'JetBrains Mono',monospace; color:var(--text-dim);">${escapeHtml(r.evidence_metric)}</code></div>
        ${r.reviewer_comment ? `<div style="font-size:11.5px; color:var(--text-dim); background:rgba(255,255,255,0.03); border:1px solid var(--border); padding:6px 10px; border-radius:4px; margin-top:2px;"><em>Audit Record: ${escapeHtml(r.reviewer_comment)}</em></div>` : ''}
        ${actionsHtml}
      </div>
    `;
  }).join('');
}

// ── Governance Confirmation & Consequential Action Guard ─────
function requestDecisionConfirmation(id, decision) {
  if (!currentUser) {
    showToast('Authentication required. Please sign in.');
    openLoginModal();
    return;
  }

  if (decision !== 'completed' && currentUser.role !== 'ADMIN') {
    showToast('Administrator privileges required to approve or reject recommendations.');
    openLoginModal();
    return;
  }

  pendingDecisionData = { id, decision };
  const titleEl = document.getElementById('confirm-modal-title');
  const bodyEl = document.getElementById('confirm-modal-body');
  const modal = document.getElementById('decision-confirm-modal');

  const actionName = decision === 'revision_requested' ? 'Request Revision' : decision.toUpperCase();
  if (titleEl) titleEl.textContent = `Confirm Governance Action: ${actionName}`;
  if (bodyEl) {
    bodyEl.innerHTML = `Are you sure you want to mark recommendation <code>${escapeHtml(id)}</code> as <strong>${escapeHtml(actionName)}</strong>?<br><br>This consequential decision will be recorded with your administrator identity in the institutional audit log.`;
  }
  if (modal) modal.style.display = 'flex';
}

function closeConfirmModal() {
  const modal = document.getElementById('decision-confirm-modal');
  if (modal) modal.style.display = 'none';
  pendingDecisionData = null;
}

async function proceedWithConfirmedDecision() {
  if (!pendingDecisionData) return;
  const { id, decision } = pendingDecisionData;
  closeConfirmModal();
  await executeRecommendationDecision(id, decision);
}

async function executeRecommendationDecision(id, decision) {
  let completionNotes = '';
  if (decision === 'completed') {
    const promptNotes = prompt("Enter completion summary / implementation evidence notes for this action plan:");
    if (promptNotes === null) return; // User canceled
    completionNotes = promptNotes.trim() || "Action plan implemented and verified.";
  }

  try {
    const res = await fetch('/api/recommendations/decision', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': currentCsrfToken || ''
      },
      body: JSON.stringify({
        id,
        status: decision,
        comment: `Decision recorded by ${currentUser ? currentUser.username : 'Administrator'}`,
        completion_notes: completionNotes
      })
    });
    if (res.ok) {
      showToast(`Action updated: ${decision.toUpperCase()}`);
      await renderApprovalsView();
      await refreshApprovalsBadge();
      return;
    } else if (res.status === 401) {
      showToast('Session expired. Please sign in again.');
      currentUser = null;
      updateAuthUI();
      openLoginModal();
      return;
    } else if (res.status === 403) {
      showToast('Forbidden: Insufficient privileges for this operation.');
      return;
    }
  } catch (err) {
    console.warn("Could not persist to backend; updating local view.");
  }
  showToast(`Action recorded: ${decision.toUpperCase()}`);
  renderApprovalsView();
}

// ── Club Detail Modal (Phase 3 Interactive Inspection) ────────
function openClubDetail(clubName) {
  if (!clubName || !agent.rankings) return;
  const d = agent.rankings.find(r => r.club.name.toLowerCase() === clubName.toLowerCase());
  if (!d) return;

  currentDetailClubName = d.club.name;
  const modal = document.getElementById('club-detail-modal');
  if (!modal) return;

  // Title group
  const badge = document.getElementById('club-modal-badge');
  if (badge) {
    badge.textContent = `#${d.rank}`;
    badge.className = `club-modal-badge ${d.rank <= 3 ? 'rank-badge-' + d.rank : 'rank-badge-other'}`;
  }
  const nameEl = document.getElementById('club-modal-name');
  if (nameEl) nameEl.textContent = d.club.name;
  const taglineEl = document.getElementById('club-modal-tagline');
  if (taglineEl) taglineEl.textContent = d.club.tagline || 'Technical Student Organization';

  // Score Banner
  const compEl = document.getElementById('club-modal-composite');
  if (compEl) compEl.innerHTML = `${d.composite.toFixed(1)}<span>/100</span>`;
  
  const xaiEl = document.getElementById('club-modal-xai');
  if (xaiEl) {
    if (d.xai_attribution) {
      xaiEl.innerHTML = `
        <div class="xai-driver" style="font-size:12px; margin-bottom:4px;">▲ <strong>Driver:</strong> ${escapeHtml(d.xai_attribution.primary_driver)}</div>
        <div class="xai-detractor" style="font-size:12px;">▼ <strong>Detractor:</strong> ${escapeHtml(d.xai_attribution.primary_detractor)}</div>
      `;
    } else {
      xaiEl.innerHTML = `<span style="font-size:12px; color:var(--text-dim);">Evaluated by Python Scoring Engine (Single Source of Truth)</span>`;
    }
  }

  // 5-Metric Breakdown
  const grid = document.getElementById('club-modal-metrics-grid');
  if (grid) {
    const m = d.metrics;
    grid.innerHTML = `
      <div class="modal-metric-card">
        <span class="modal-metric-label">Attendance Rate (30%)</span>
        <div class="modal-metric-val">${m.attendanceRate}%</div>
        <div style="font-size:10.5px; color:var(--text-mute); margin-top:2px;">${m.totalAttendance} / ${m.totalRegistrations} attendees</div>
      </div>
      <div class="modal-metric-card">
        <span class="modal-metric-label">Avg Feedback (30%)</span>
        <div class="modal-metric-val">${m.avgFeedback !== null ? m.avgFeedback + ' / 5.0' : '<span style="color:var(--amber);">Gap Handled</span>'}</div>
        <div style="font-size:10.5px; color:var(--text-mute); margin-top:2px;">Participant rating</div>
      </div>
      <div class="modal-metric-card">
        <span class="modal-metric-label">Speaker Rating (15%)</span>
        <div class="modal-metric-val">${m.avgSpeakerRating !== null ? m.avgSpeakerRating + ' / 5.0' : '<span style="color:var(--text-mute);">N/A</span>'}</div>
        <div style="font-size:10.5px; color:var(--text-mute); margin-top:2px;">External guest evaluation</div>
      </div>
      <div class="modal-metric-card">
        <span class="modal-metric-label">Event Count (10%)</span>
        <div class="modal-metric-val">${m.eventCount}</div>
        <div style="font-size:10.5px; color:var(--text-mute); margin-top:2px;">Organized this semester</div>
      </div>
      <div class="modal-metric-card" style="grid-column: span 2;">
        <span class="modal-metric-label">Consistency Index (15%)</span>
        <div class="modal-metric-val">${m.consistency} / 100</div>
        <div style="font-size:10.5px; color:var(--text-mute); margin-top:2px;">Turnout variance and regularity metric</div>
      </div>
    `;
  }

  // Semester Events
  const eventsList = document.getElementById('club-modal-events-list');
  if (eventsList) {
    const allClubEvents = agent.getAllEvents()
      .filter(ev => ev.club.name.toLowerCase() === d.club.name.toLowerCase())
      .sort((a, b) => new Date(a.date) - new Date(b.date));

    if (allClubEvents.length === 0) {
      eventsList.innerHTML = `<div style="color:var(--text-mute); font-size:12px; padding:8px 0;">No events recorded for this semester.</div>`;
    } else {
      eventsList.innerHTML = allClubEvents.map(ev => `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 12px; background:var(--surface2); border:1px solid var(--border); border-radius:6px; font-size:12px;">
          <div>
            <div style="font-weight:600; color:var(--text);">${escapeHtml(ev.name)}</div>
            <div style="color:var(--text-mute); font-size:11px;">${escapeHtml(ev.date)} · ${escapeHtml(ev.type)}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-family:'JetBrains Mono',monospace; color:var(--text-dim);">${ev.attendance !== null ? ev.attendance : '⚠️ Missing'} / ${ev.registrations}</div>
            <div style="color:var(--accent); font-size:11px;">${ev.feedbackAvg ? '★ ' + ev.feedbackAvg : '⚠️ No feedback'}</div>
          </div>
        </div>
      `).join('');
    }
  }

  modal.style.display = 'flex';
}

function closeClubDetail() {
  const modal = document.getElementById('club-detail-modal');
  if (modal) modal.style.display = 'none';
  currentDetailClubName = null;
}

// ── Password Visibility Toggle ───────────────────────────────
function togglePasswordVisibility() {
  const input = document.getElementById('login-password');
  const btn = document.getElementById('toggle-password-btn');
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    if (btn) btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
  } else {
    input.type = 'password';
    if (btn) btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
  }
}

// ── Semester Switching (Phase 4 Multi-Semester Support) ───────
async function handleSemesterChange(val) {
  if (!val) return;
  SEMESTER.name = val;
  showToast(`Loading analytics for ${val}…`);
  await bootAgent();
  if (currentView === 'events') renderEventTimeline();
  if (currentView === 'report') renderFullReport();
  if (currentView === 'approvals') renderApprovalsView();
}

// ── Utilities ─────────────────────────────────────────────────
function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

function updateStatus(text) {
  const el = document.getElementById('agent-status');
  if (el) el.textContent = text;
}

function showToast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// Expose key functions globally for capture scripts and external callers
window.switchView = switchView;
window.openClubDetail = openClubDetail;
window.closeClubDetail = closeClubDetail;

// Re-draw charts on resize and setup ResizeObserver for robust layout adaptation
let resizeTimeout = null;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => {
    if (currentView === 'dashboard') {
      drawBarChart();
      drawRadarChart();
    }
  }, 100);
});

// Use ResizeObserver on chart wrappers so any flexbox or container dimension change redraws canvas
if (typeof ResizeObserver !== 'undefined') {
  const chartObserver = new ResizeObserver(() => {
    if (currentView === 'dashboard') {
      drawBarChart();
      drawRadarChart();
    }
  });
  window.addEventListener('DOMContentLoaded', () => {
    const barWrap = document.getElementById('bar-chart')?.parentElement;
    const radarWrap = document.getElementById('radar-chart')?.parentElement;
    if (barWrap) chartObserver.observe(barWrap);
    if (radarWrap) chartObserver.observe(radarWrap);
  });
}
