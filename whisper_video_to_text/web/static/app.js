'use strict';

const PHASES = [
  { key: 'fetch',      name: 'FETCH',      statuses: ['uploading', 'downloading'] },
  { key: 'extract',    name: 'EXTRACT',    statuses: ['converting'] },
  { key: 'transcribe', name: 'TRANSCRIBE', statuses: ['transcribing'] },
  { key: 'render',     name: 'RENDER',     statuses: ['saving'] },
];

const PHASE_BOUNDARIES = [10, 30, 60, 90, 100];

function phaseIndexForStatus(status) {
  for (let i = 0; i < PHASES.length; i++) {
    if (PHASES[i].statuses.includes(status)) return i;
  }
  return -1;
}

function renderPhaseLadder(activeIndex, { progress = 0, complete = false, errored = false } = {}) {
  const container = document.getElementById('phase-ladder');
  if (!container) return;
  container.replaceChildren();

  PHASES.forEach((phase, i) => {
    let state = 'queued';
    if (complete) state = 'complete';
    else if (errored && i === activeIndex) state = 'error';
    else if (errored && i < activeIndex) state = 'complete';
    else if (i < activeIndex) state = 'complete';
    else if (i === activeIndex) state = 'active';

    const fill = state === 'complete' ? 100 : state === 'active' ? progress : 0;

    const row = document.createElement('div');
    row.className = `phase phase--${state}`;

    const num = document.createElement('span');
    num.className = 'phase-num';
    num.textContent = `[${String(i + 1).padStart(2, '0')}]`;

    const name = document.createElement('span');
    name.className = 'phase-name';
    name.textContent = phase.name;

    const track = document.createElement('span');
    track.className = 'phase-track';
    const bar = document.createElement('span');
    bar.className = 'phase-track__fill';
    bar.style.width = `${fill}%`;
    track.appendChild(bar);

    const label = document.createElement('span');
    label.className = 'phase-label';
    label.textContent = state;

    row.append(num, name, track, label);
    container.appendChild(row);
  });
}

let timerInterval = null;
let timerStart = 0;

function startTimer() {
  if (timerInterval) return;
  timerStart = Date.now();
  const el = document.getElementById('elapsed');
  if (el) el.textContent = '0:00';
  timerInterval = setInterval(() => {
    const node = document.getElementById('elapsed');
    if (!node) return;
    const s = Math.floor((Date.now() - timerStart) / 1000);
    node.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  }, 250);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

function showError(msg) {
  const el = document.getElementById('form-error');
  if (!el) return;
  el.textContent = msg;
  el.hidden = false;
}

function clearError() {
  const el = document.getElementById('form-error');
  if (!el) return;
  el.textContent = '';
  el.hidden = true;
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const target = current === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', target);
  localStorage.setItem('theme', target);
  const btn = document.getElementById('theme-btn');
  if (btn) btn.textContent = target === 'light' ? 'NIGHT MODE' : 'DAY MODE';
}

function createDownloadLink(jobId, ext, { compact = false } = {}) {
  const link = document.createElement('a');
  link.href = `/download/${encodeURIComponent(jobId)}/${encodeURIComponent(ext)}`;
  link.className = compact ? 'btn btn-download btn-download--compact' : 'btn btn-download';
  link.textContent = compact ? ext.toUpperCase() : `DOWNLOAD .${ext.toUpperCase()}`;
  link.target = '_blank';
  link.rel = 'noopener';
  return link;
}

async function startJob(e) {
  e.preventDefault();
  clearError();

  const fileInput = document.getElementById('file');
  const urlInput = document.getElementById('url');
  const hasFile = fileInput.files && fileInput.files.length > 0;
  const hasUrl = urlInput.value.trim().length > 0;

  if (!hasFile && !hasUrl) {
    showError('Choose a file or paste a URL to begin.');
    return;
  }

  const form = document.getElementById('form');
  const data = new FormData(form);
  const btn = document.getElementById('submit-btn');
  const originalText = btn.textContent;
  btn.textContent = 'INITIALIZING...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/transcribe', { method: 'POST', body: data });
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    const { job_id: jobId } = await res.json();

    btn.textContent = 'PROCESSING...';
    const statusContainer = document.getElementById('status-container');
    const status = document.getElementById('status');
    statusContainer.hidden = false;
    status.textContent = 'QUEUED';
    status.dataset.state = 'queued';
    document.getElementById('downloads').hidden = true;
    document.getElementById('downloads').replaceChildren();
    renderPhaseLadder(-1, {});
    startTimer();
    listen(jobId);
  } catch (err) {
    btn.textContent = originalText;
    btn.disabled = false;
    showError(`Error starting transcription: ${err.message}`);
    stopTimer();
  }
}

function listen(jobId) {
  const events = new EventSource(`/events/${jobId}`);
  const status = document.getElementById('status');
  const message = document.getElementById('message');
  const output = document.getElementById('output');
  const downloads = document.getElementById('downloads');
  const btn = document.getElementById('submit-btn');
  let lastPhaseIdx = -1;

  events.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    const isComplete = data.status === 'complete';
    const isError = data.status === 'error';
    const mapped = phaseIndexForStatus(data.status);
    if (mapped >= 0) lastPhaseIdx = mapped;
    const phaseIdx = mapped >= 0 ? mapped : lastPhaseIdx;

    let intraProgress = 0;
    if (mapped >= 0 && !isComplete && !isError) {
      const start = PHASE_BOUNDARIES[mapped];
      const end = PHASE_BOUNDARIES[mapped + 1];
      const clamped = Math.max(start, Math.min(end, data.progress || start));
      intraProgress = ((clamped - start) / (end - start)) * 100;
    }

    renderPhaseLadder(phaseIdx, { progress: intraProgress, complete: isComplete, errored: isError });

    if (data.status) {
      status.textContent = data.status.toUpperCase();
      status.dataset.state = data.status;
    }
    message.textContent = data.message || '';

    if (data.result && data.result.text) {
      output.textContent = data.result.text;
    }

    if (isComplete || isError) {
      events.close();
      stopTimer();
      btn.textContent = 'START TRANSCRIPTION';
      btn.disabled = false;
    }

    if (isComplete && data.result && data.result.formats) {
      downloads.replaceChildren();
      Object.keys(data.result.formats).forEach(ext => {
        downloads.appendChild(createDownloadLink(jobId, ext));
      });
      downloads.hidden = false;
      document.body.classList.add('flash-success');
      setTimeout(() => document.body.classList.remove('flash-success'), 900);
    }
  };

  events.onerror = () => {
    events.close();
    stopTimer();
    btn.textContent = 'START TRANSCRIPTION';
    btn.disabled = false;
  };
}

async function toggleHistory() {
  const modal = document.getElementById('history-modal');
  const list = document.getElementById('history-list');

  if (modal.hidden) {
    modal.hidden = false;
    list.replaceChildren();
    const loading = document.createElement('div');
    loading.className = 'meta';
    loading.textContent = 'Loading...';
    list.appendChild(loading);

    try {
      const res = await fetch('/api/history');
      const history = await res.json();
      list.replaceChildren();

      if (history.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'meta';
        empty.textContent = 'No transcripts found.';
        list.appendChild(empty);
        return;
      }

      history.forEach(item => list.appendChild(buildHistoryItem(item)));
    } catch (err) {
      list.replaceChildren();
      const errEl = document.createElement('div');
      errEl.className = 'meta error-text';
      errEl.textContent = `Error loading history: ${err.message}`;
      list.appendChild(errEl);
    }
  } else {
    modal.hidden = true;
  }
}

function buildHistoryItem(item) {
  const card = document.createElement('div');
  card.className = 'card history-item';

  const row = document.createElement('div');
  row.className = 'history-item__row';

  const info = document.createElement('div');
  const id = document.createElement('div');
  id.className = 'history-item__id';
  id.textContent = `Job ID: ${item.job_id}`;
  const date = document.createElement('div');
  date.className = 'meta';
  date.textContent = new Date(item.date).toLocaleString();
  info.append(id, date);

  const links = document.createElement('div');
  links.className = 'history-item__links';
  item.formats.forEach(fmt => links.appendChild(createDownloadLink(item.job_id, fmt, { compact: true })));

  row.append(info, links);
  card.appendChild(row);
  return card;
}

document.addEventListener('DOMContentLoaded', () => {
  const current = document.documentElement.getAttribute('data-theme');
  const themeBtn = document.getElementById('theme-btn');
  if (themeBtn) themeBtn.textContent = current === 'light' ? 'NIGHT MODE' : 'DAY MODE';

  document.getElementById('form').addEventListener('submit', startJob);
  themeBtn.addEventListener('click', toggleTheme);
  document.getElementById('history-btn').addEventListener('click', toggleHistory);
  document.getElementById('history-close').addEventListener('click', toggleHistory);
});
