const qs = (s) => document.querySelector(s);

function setTheme(isLight) {
  if (isLight) document.documentElement.classList.add('light');
  else document.documentElement.classList.remove('light');
  localStorage.setItem('kd_theme', isLight ? 'light' : 'dark');
}
const stored = localStorage.getItem('kd_theme') || 'dark';
setTheme(stored === 'light');

qs('#theme-toggle').addEventListener('click', () => {
  const light = document.documentElement.classList.toggle('light');
  setTheme(light);
});

async function api(path, opts={}) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error('API error');
  return res.json();
}

async function loadStatus() {
  try {
    const data = await api('/api/status');
    const progress = data.progress || {};
    const streamers = data.streamers || [];
    const farmer = data.farmer || {};
    renderCampaigns(progress);
    renderStreamers(streamers);
    renderLogs(farmer.logs || []);
    qs('#farmer-state').textContent = farmer.status || 'UNKNOWN';
    qs('#farmer-toggle').textContent = farmer.status === 'RUNNING' ? 'Stop' : 'Start';
    const selectedGameEl = qs('#game-select');
    if (selectedGameEl) qs('#selected-game').textContent = selectedGameEl.options[selectedGameEl.selectedIndex].text;
    qs('#selected-mode').textContent = qs('#mode-select').value;
  } catch (e) {
    console.error(e);
    qs('#campaigns-list').innerHTML = '<div class="muted small">Error loading campaigns</div>';
  }
}

function renderCampaigns(progress) {
  const container = qs('#campaigns-list');
  container.innerHTML = '';
  if (!progress || !progress.data || !progress.data.length) {
    container.innerHTML = '<div class="muted small">No campaign progress available</div>';
    return;
  }
  progress.data.slice(0,12).forEach(c => {
    const card = document.createElement('div');
    card.className = 'campaign-card';

    const imageUrl = c.image || c.icon || (c.category && c.category.icon) || null;
    if (imageUrl) {
      const imgWrap = document.createElement('div');
      imgWrap.className = 'campaign-thumb';
      const img = document.createElement('img');
      img.src = imageUrl;
      img.alt = c.title || c.name || `Campaign ${c.id}`;
      img.loading = 'lazy';
      imgWrap.appendChild(img);
      card.appendChild(imgWrap);
    }

    const title = document.createElement('div');
    title.className = 'campaign-title';
    title.textContent = c.title || c.name || `Campaign ${c.id}`;

    const rewards = c.rewards || [];
    const total = rewards.length || 1;
    const progressSum = rewards.reduce((acc, r) => acc + (typeof r.progress === "number" ? r.progress : (r.claimed ? 1 : 0)), 0);
    const percent = Math.round(100 * progressSum / total);

    const progressWrap = document.createElement('div');
    progressWrap.className = 'progress-wrap';
    const bar = document.createElement('div');
    bar.className = 'progress-bar';
    bar.style.width = `${percent}%`;
    progressWrap.appendChild(bar);

    const meta = document.createElement('div');
    meta.className = 'progress-meta';
    meta.innerHTML = `<div class="small muted">${progressSum.toFixed(1)} / ${total} complete</div><div class="small muted">${percent}%</div>`;

    card.appendChild(title);
    card.appendChild(progressWrap);
    card.appendChild(meta);
    container.appendChild(card);
  });
}

function renderStreamers(list) {
  const container = qs('#streamers-list');
  container.innerHTML = '';
  if (!list || !list.length) {
    container.innerHTML = '<div class="muted small">No targeted streamers configured</div>';
    return;
  }
  list.forEach(s => {
    const row = document.createElement('div');
    row.className = 'streamer-row';
    const left = document.createElement('div');
    left.className = 'streamer-left';
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = (s.username || '?').slice(0,2).toUpperCase();
    const meta = document.createElement('div');
    meta.className = 'streamer-meta';
    const name = document.createElement('div');
    name.textContent = s.username || 'unknown';
    const small = document.createElement('div');
    small.className = 'small muted';
    if (s.claim === 1) small.textContent = 'Claimed';
    else if (s.progress === 1 || s.required_seconds === 0) small.textContent = 'Ready to claim';
    else if (typeof s.progress === "number") small.textContent = `Progress: ${(s.progress*100).toFixed(1)}%`;
    else if (s.required_seconds) small.textContent = `Needs ${s.required_seconds}s`;
    else small.textContent = 'Pending';
    meta.appendChild(name);
    meta.appendChild(small);
    left.appendChild(avatar);
    left.appendChild(meta);

    const right = document.createElement('div');
    if (s.claim !== 1 && (s.progress === 1 || s.required_seconds === 0)) {
      const btn = document.createElement('button');
      btn.className = 'btn primary';
      btn.textContent = 'Claim';
      btn.onclick = async () => {
        btn.disabled = true;
        const payload = { reward_id: s.reward_id || s.id || null, campaign_id: s.campaign_id || s.campaign_id || null };
        try {
          await api('/api/claim', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
          await loadStatus();
        } catch (e) {
          btn.disabled = false;
          alert('Claim failed');
        }
      };
      right.appendChild(btn);
    } else if (s.claim === 1) {
      const label = document.createElement('div');
      label.className = 'small muted';
      label.textContent = 'Claimed';
      right.appendChild(label);
    }

    row.appendChild(left);
    row.appendChild(right);
    container.appendChild(row);
  });
}

function parseYearFromLine(line) {
  if (!line) return null;
  const m = line.match(/20\d{2}/);
  if (!m) return null;
  return parseInt(m[0], 10);
}

function renderLogs(lines) {
  const el = qs('#logs');

  if (!el) return;

  const atBottomThreshold = 40;
  const wasAtBottom = (el.scrollHeight - el.scrollTop - el.clientHeight) <= atBottomThreshold;

  el.innerHTML = '';

  if (!lines || !lines.length) {
    el.textContent = 'No logs';
    return;
  }

  let renderLines = Array.from(lines);
  const y0 = parseYearFromLine(renderLines[0]);
  const yN = parseYearFromLine(renderLines[renderLines.length - 1]);
  if (y0 !== null && yN !== null && y0 > yN) {
    renderLines = renderLines.reverse();
  }

  renderLines.forEach(l => {
    const div = document.createElement('div');
    div.className = 'line';
    div.textContent = l;
    el.appendChild(div);
  });

  if (wasAtBottom) {
    el.scrollTop = el.scrollHeight;
  }
}

qs('#refresh').addEventListener('click', loadStatus);

qs('#apply-btn').addEventListener('click', async () => {
  const gameId = qs('#game-select').value;
  const mode = qs('#mode-select').value;
  try {
    await api('/api/select', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ game_id: gameId, drop_type: mode }) });
    await loadStatus();
  } catch (e) {
    alert('Apply failed');
  }
});

qs('#farmer-toggle').addEventListener('click', async () => {
  const state = qs('#farmer-toggle').textContent.trim();
  if (state === 'Stop') {
    await api('/api/stop_farmer', { method: 'POST' });
    qs('#farmer-toggle').textContent = 'Start';
    qs('#farmer-state').textContent = 'STOPPED';
  } else {
    await api('/api/select', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ game_id: qs('#game-select').value, drop_type: qs('#mode-select').value }) });
    qs('#farmer-toggle').textContent = 'Stop';
    qs('#farmer-state').textContent = 'RUNNING';
  }
  await loadStatus();
});

qs('#clear-logs').addEventListener('click', () => { qs('#logs').textContent = ''; });

qs('#download-logs').addEventListener('click', () => {
  const text = Array.from(qs('#logs').children).map(n => n.textContent).join('\n');
  const blob = new Blob([text], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'farmer.log';
  a.click();
  URL.revokeObjectURL(url);
});

loadStatus();
setInterval(loadStatus, 30000);