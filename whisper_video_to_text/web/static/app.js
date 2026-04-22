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

async function openHistory() {
  const modal = document.getElementById('history-modal');
  const list = document.getElementById('history-list');

  if (typeof modal.showModal === 'function') modal.showModal();
  else modal.setAttribute('open', '');

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
}

function closeHistory() {
  const modal = document.getElementById('history-modal');
  if (typeof modal.close === 'function') modal.close();
  else modal.removeAttribute('open');
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

function formatSize(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let n = bytes;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(n >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
}

function showFilePreview(file) {
  const zone = document.getElementById('file-zone');
  const drop = document.getElementById('file-zone-drop');
  const preview = document.getElementById('file-preview');
  const name = document.getElementById('file-preview-name');
  const size = document.getElementById('file-preview-size');
  if (!file) {
    drop.hidden = false;
    preview.hidden = true;
    zone.classList.remove('file-zone--filled');
    return;
  }
  name.textContent = file.name;
  size.textContent = formatSize(file.size);
  drop.hidden = true;
  preview.hidden = false;
  zone.classList.add('file-zone--filled');
}

function clearFile() {
  const input = document.getElementById('file');
  input.value = '';
  showFilePreview(null);
}

const ACCEPTED_EXTENSIONS = ['.mp3', '.wav', '.aif', '.aiff', '.mp4', '.mov'];
const ACCEPTED_MIMES = new Set([
  'audio/mpeg', 'audio/mp3',
  'audio/wav', 'audio/wave', 'audio/x-wav',
  'audio/aiff', 'audio/x-aiff',
  'video/mp4',
  'video/quicktime', 'video/x-quicktime',
]);

function verdictForMime(type) {
  if (!type) return 'unknown';
  return ACCEPTED_MIMES.has(type) ? 'accept' : 'reject';
}

function verdictForDragEvent(e) {
  const items = e.dataTransfer && e.dataTransfer.items;
  if (!items || items.length === 0) return 'unknown';
  const fileItems = Array.from(items).filter(i => i.kind === 'file');
  if (fileItems.length === 0) return 'reject';
  if (fileItems.length > 1) return 'reject';
  return verdictForMime(fileItems[0].type);
}

function isAcceptedFile(file) {
  if (!file) return false;
  if (file.type && ACCEPTED_MIMES.has(file.type)) return true;
  const name = (file.name || '').toLowerCase();
  return ACCEPTED_EXTENSIONS.some(ext => name.endsWith(ext));
}

function applyDropVerdict(drop, verdict) {
  drop.classList.toggle('file-zone__drop--over', verdict === 'accept' || verdict === 'unknown');
  drop.classList.toggle('file-zone__drop--reject', verdict === 'reject');
  const glyph = drop.querySelector('.file-zone__glyph');
  if (glyph) glyph.textContent = verdict === 'reject' ? '✕' : '↓';
}

function clearDropVerdict(drop) {
  drop.classList.remove('file-zone__drop--over', 'file-zone__drop--reject');
  const glyph = drop.querySelector('.file-zone__glyph');
  if (glyph) glyph.textContent = '↓';
}

function wireFileZone() {
  const input = document.getElementById('file');
  const drop = document.getElementById('file-zone-drop');
  const remove = document.getElementById('file-remove');

  input.addEventListener('change', () => {
    const file = input.files && input.files[0];
    showFilePreview(file || null);
    if (file) clearError();
  });

  remove.addEventListener('click', clearFile);

  ['dragenter', 'dragover'].forEach(evt => {
    drop.addEventListener(evt, e => {
      e.preventDefault();
      const verdict = verdictForDragEvent(e);
      if (e.dataTransfer) {
        e.dataTransfer.dropEffect = verdict === 'reject' ? 'none' : 'copy';
      }
      applyDropVerdict(drop, verdict);
    });
  });

  ['dragleave', 'dragend'].forEach(evt => {
    drop.addEventListener(evt, () => clearDropVerdict(drop));
  });

  drop.addEventListener('drop', e => {
    e.preventDefault();
    clearDropVerdict(drop);
    const files = e.dataTransfer && e.dataTransfer.files;
    if (!files || files.length === 0) return;
    if (files.length > 1) {
      showError('Drop one file at a time.');
      return;
    }
    const file = files[0];
    if (!isAcceptedFile(file)) {
      showError(`Unsupported file: ${file.name || file.type || 'unknown type'}. Accepted: ${ACCEPTED_EXTENSIONS.join(', ')}`);
      return;
    }
    try {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
    } catch {
      input.files = files;
    }
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
}

async function copyTranscript() {
  const output = document.getElementById('output');
  const btn = document.getElementById('copy-btn');
  const text = output.textContent || '';
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    const orig = btn.textContent;
    btn.textContent = 'COPIED';
    btn.classList.add('copy-btn--confirmed');
    setTimeout(() => {
      btn.textContent = orig;
      btn.classList.remove('copy-btn--confirmed');
    }, 1200);
  } catch {
    btn.textContent = 'COPY FAILED';
    setTimeout(() => { btn.textContent = 'COPY'; }, 1500);
  }
}

function updateCopyButtonState() {
  const btn = document.getElementById('copy-btn');
  const output = document.getElementById('output');
  const hasText = output.textContent && output.textContent.trim() !== '' && output.textContent !== 'Waiting for data stream...';
  btn.disabled = !hasText;
}

document.addEventListener('DOMContentLoaded', () => {
  const current = document.documentElement.getAttribute('data-theme');
  const themeBtn = document.getElementById('theme-btn');
  if (themeBtn) themeBtn.textContent = current === 'light' ? 'NIGHT MODE' : 'DAY MODE';

  document.getElementById('form').addEventListener('submit', startJob);
  themeBtn.addEventListener('click', toggleTheme);
  document.getElementById('history-btn').addEventListener('click', openHistory);
  document.getElementById('history-close').addEventListener('click', closeHistory);
  document.getElementById('copy-btn').addEventListener('click', copyTranscript);

  wireFileZone();

  const output = document.getElementById('output');
  new MutationObserver(updateCopyButtonState).observe(output, { characterData: true, childList: true, subtree: true });
  updateCopyButtonState();
});
