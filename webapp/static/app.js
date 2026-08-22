(function () {
  'use strict';

  // ---------- State ----------
  let optionsData = null;
  let currentRunId = null;
  let eventSource = null;
  const agentStates = {};
  const reportContents = {};

  // ---------- DOM refs ----------
  const el = (id) => document.getElementById(id);
  const tickerEl = el('ticker');
  const dateEl = el('analysis-date');
  const analystsGroupEl = el('analysts-group');
  const depthEl = el('research-depth');
  const providerEl = el('llm-provider');
  const backendUrlEl = el('backend-url');
  const shallowEl = el('shallow-thinker');
  const deepEl = el('deep-thinker');
  const langEl = el('output-language');
  const btnStart = el('btn-start');
  const btnStop = el('btn-stop');
  const errorBanner = el('error-banner');
  const agentGrid = el('agent-grid');
  const reportTabs = el('report-tabs');
  const reportPanels = el('report-panels');
  const logEl = el('log');
  const statsBar = el('stats-bar');
  const doneBanner = el('done-banner');

  const ALL_AGENTS = [
    'Market Analyst', 'Sentiment Analyst', 'News Analyst', 'Fundamentals Analyst',
    'Bull Researcher', 'Bear Researcher', 'Research Manager',
    'Trader',
    'Aggressive Analyst', 'Neutral Analyst', 'Conservative Analyst',
    'Portfolio Manager',
  ];

  const REPORT_LABELS = {
    market_report: 'Market Analysis',
    sentiment_report: 'Social Sentiment',
    news_report: 'News Analysis',
    fundamentals_report: 'Fundamentals Analysis',
    investment_plan: 'Research Team Decision',
    trader_investment_plan: 'Trading Team Plan',
    final_trade_decision: 'Portfolio Management Decision',
  };

  // ---------- Init ----------
  function init() {
    const today = new Date().toISOString().split('T')[0];
    dateEl.value = today;

    fetchOptions();
    setupListeners();
    resetUI();
  }

  function resetUI() {
    ALL_AGENTS.forEach(a => agentStates[a] = 'pending');
    renderAgentGrid();
    buildReportTabs();
    logEl.innerHTML = '';
    statsBar.innerHTML = '';
    doneBanner.style.display = 'none';
    doneBanner.innerHTML = '';
    hideError();
  }

  // ---------- Options ----------
  async function fetchOptions() {
    try {
      const res = await fetch('/api/options');
      if (!res.ok) throw new Error('Failed to load options');
      optionsData = await res.json();
      populateForm();
      await refreshModels();
    } catch (e) {
      showError(e.message);
    }
  }

  function populateForm() {
    // analysts
    analystsGroupEl.innerHTML = '';
    optionsData.analysts.forEach(a => {
      const label = document.createElement('label');
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.value = a.key;
      cb.checked = true;
      cb.className = 'analyst-cb';
      label.appendChild(cb);
      label.appendChild(document.createTextNode(a.label));
      analystsGroupEl.appendChild(label);
    });

    // research depth
    depthEl.innerHTML = '';
    optionsData.research_depth.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.value;
      opt.textContent = d.label;
      if (d.value === 1) opt.selected = true;
      depthEl.appendChild(opt);
    });

    // providers
    providerEl.innerHTML = '';
    optionsData.providers.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.key;
      opt.textContent = p.name;
      opt.dataset.url = p.default_url || '';
      providerEl.appendChild(opt);
    });

    if (providerEl.options.length > 0) {
      backendUrlEl.value = providerEl.options[0].dataset.url || '';
    }
  }

  async function refreshModels() {
    const provider = providerEl.value;
    if (!provider) return;

    try {
      const [quickRes, deepRes] = await Promise.all([
        fetch(`/api/options/models?provider=${encodeURIComponent(provider)}&mode=quick`),
        fetch(`/api/options/models?provider=${encodeURIComponent(provider)}&mode=deep`),
      ]);

      const quickOpts = quickRes.ok ? await quickRes.json() : [];
      const deepOpts = deepRes.ok ? await deepRes.json() : [];

      fillSelect(shallowEl, quickOpts);
      fillSelect(deepEl, deepOpts);
    } catch (e) {
      // silently ignore
    }
  }

  function fillSelect(selectEl, items) {
    const prev = selectEl.value;
    selectEl.innerHTML = '';
    items.forEach(item => {
      const opt = document.createElement('option');
      opt.value = item.value;
      opt.textContent = item.label;
      selectEl.appendChild(opt);
    });
    if (prev && Array.from(selectEl.options).some(o => o.value === prev)) {
      selectEl.value = prev;
    }
  }

  // ---------- Listeners ----------
  function setupListeners() {
    providerEl.addEventListener('change', () => {
      const opt = providerEl.selectedOptions[0];
      if (opt && opt.dataset.url) backendUrlEl.value = opt.dataset.url;
      refreshModels();
    });

    btnStart.addEventListener('click', startRun);
    btnStop.addEventListener('click', stopRun);
  }

  // ---------- Run lifecycle ----------
  async function startRun() {
    hideError();
    resetUI();

    const analysts = Array.from(document.querySelectorAll('.analyst-cb:checked')).map(cb => cb.value);
    if (analysts.length === 0) {
      showError('Select at least one analyst.');
      return;
    }

    const body = {
      ticker: tickerEl.value.trim(),
      analysis_date: dateEl.value,
      analysts: analysts,
      research_depth: parseInt(depthEl.value, 10),
      llm_provider: providerEl.value,
      backend_url: backendUrlEl.value.trim(),
      shallow_thinker: shallowEl.value,
      deep_thinker: deepEl.value,
      output_language: langEl.value.trim(),
    };

    try {
      const res = await fetch('/api/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await res.json();
      if (!res.ok) {
        showError(data.error || `Error ${res.status}`);
        return;
      }

      currentRunId = data.run_id;
      btnStart.disabled = true;
      btnStop.disabled = false;
      subscribeEvents(currentRunId);
    } catch (e) {
      showError(e.message);
    }
  }

  async function stopRun() {
    if (!currentRunId) return;
    try {
      await fetch(`/api/runs/${currentRunId}/stop`, { method: 'POST' });
    } catch (e) {
      // ignore
    }
  }

  function subscribeEvents(runId) {
    if (eventSource) { eventSource.close(); }
    eventSource = new EventSource(`/api/runs/${runId}/events`);

    eventSource.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch { return; }
      handleEvent(msg);
    };

    eventSource.onerror = () => {
      eventSource.close();
      btnStart.disabled = false;
      btnStop.disabled = true;
    };
  }

  // ---------- Event handlers ----------
  function handleEvent(msg) {
    switch (msg.type) {
      case 'status':
        agentStates[msg.agent] = msg.state;
        renderAgentGrid();
        break;
      case 'message':
        appendLog(msg.kind, msg.text);
        break;
      case 'tool':
        appendLog('Tool', `${msg.name}: ${JSON.stringify(msg.args || {})}`);
        break;
      case 'report':
        reportContents[msg.section] = msg.content;
        updateReportPanel(msg.section);
        break;
      case 'stats':
        updateStats(msg);
        break;
      case 'done':
        showDone(msg);
        if (eventSource) { eventSource.close(); eventSource = null; }
        btnStart.disabled = false;
        btnStop.disabled = true;
        break;
    }
  }

  // ---------- UI updates ----------
  function renderAgentGrid() {
    agentGrid.innerHTML = '';
    ALL_AGENTS.forEach(agent => {
      const state = agentStates[agent] || 'pending';
      const badge = document.createElement('div');
      badge.className = 'agent-badge';
      badge.innerHTML = `<span class="name">${esc(agent)}</span><span class="state state-${state}">${esc(state)}</span>`;
      agentGrid.appendChild(badge);
    });
  }

  function buildReportTabs() {
    reportTabs.innerHTML = '';
    reportPanels.innerHTML = '';
    Object.keys(REPORT_LABELS).forEach((key, idx) => {
      const tab = document.createElement('div');
      tab.className = 'tab' + (idx === 0 ? ' active' : '');
      tab.textContent = REPORT_LABELS[key];
      tab.dataset.section = key;
      tab.addEventListener('click', () => activateTab(key));
      reportTabs.appendChild(tab);

      const panel = document.createElement('div');
      panel.className = 'tab-panel report-content' + (idx === 0 ? ' active' : '');
      panel.id = 'panel-' + key;
      panel.innerHTML = '<em style="color:var(--muted)">Waiting for report...</em>';
      reportPanels.appendChild(panel);
    });
  }

  function activateTab(key) {
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.section === key));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + key));
  }

  function updateReportPanel(section) {
    const content = reportContents[section] || '';
    const panel = el('panel-' + section);
    if (panel) panel.innerHTML = renderMarkdown(content);
  }

  function appendLog(kind, text) {
    const line = document.createElement('div');
    line.className = 'log-entry log-kind-' + kind.toLowerCase().replace(/\s+/g, '-');
    line.textContent = `[${kind}] ${text}`;
    logEl.appendChild(line);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function updateStats(msg) {
    const parts = [];
    if (msg.llm_calls != null) parts.push(`LLM: ${msg.llm_calls}`);
    if (msg.tokens != null) parts.push(`Tokens: ${msg.tokens}`);
    if (msg.elapsed_sec != null) parts.push(`Elapsed: ${msg.elapsed_sec}s`);
    statsBar.innerHTML = parts.map(p => `<span>${esc(p)}</span>`).join('');
  }

  function showDone(msg) {
    let html = '';
    if (msg.decision) {
      const cls = msg.decision === 'BUY' ? 'decision-buy' : msg.decision === 'SELL' ? 'decision-sell' : 'decision-hold';
      html += `<span class="decision-badge ${cls}">${esc(msg.decision)}</span>`;
    }
    if (msg.path) {
      html += `<span style="color:var(--muted-strong); font-size:0.85rem;">${esc(msg.path)}</span>`;
    }
    if (msg.status === 'error' && msg.message) {
      html += `<span style="color:var(--danger); font-size:0.85rem;">${esc(msg.message)}</span>`;
    }
    doneBanner.innerHTML = html;
    doneBanner.style.display = 'flex';
  }

  // ---------- Markdown (minimal) ----------
  function renderMarkdown(text) {
    if (!text) return '';
    const lines = text.split('\n');
    const out = [];
    let inList = false;

    lines.forEach(line => {
      const trimmed = line.trim();
      if (!trimmed) {
        if (inList) { out.push('</ul>'); inList = false; }
        out.push('<br>');
        return;
      }

      // headings
      if (trimmed.startsWith('### ')) {
        if (inList) { out.push('</ul>'); inList = false; }
        out.push(`<h3>${inlineFmt(trimmed.slice(4))}</h3>`);
        return;
      }
      if (trimmed.startsWith('## ')) {
        if (inList) { out.push('</ul>'); inList = false; }
        out.push(`<h2>${inlineFmt(trimmed.slice(3))}</h2>`);
        return;
      }
      if (trimmed.startsWith('# ')) {
        if (inList) { out.push('</ul>'); inList = false; }
        out.push(`<h1>${inlineFmt(trimmed.slice(2))}</h1>`);
        return;
      }

      // list
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        if (!inList) { out.push('<ul>'); inList = true; }
        out.push(`<li>${inlineFmt(trimmed.slice(2))}</li>`);
        return;
      }

      if (inList) { out.push('</ul>'); inList = false; }
      out.push(`<p>${inlineFmt(trimmed)}</p>`);
    });

    if (inList) out.push('</ul>');
    return out.join('');
  }

  function inlineFmt(text) {
    return esc(text)
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>');
  }

  // ---------- Utilities ----------
  function esc(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function showError(msg) {
    errorBanner.textContent = msg;
    errorBanner.style.display = 'block';
  }

  function hideError() {
    errorBanner.style.display = 'none';
    errorBanner.textContent = '';
  }

  // ---------- Boot ----------
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
