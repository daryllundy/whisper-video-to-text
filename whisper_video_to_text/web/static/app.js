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

// ---------------------------------------------------------------------------
// Queue model: client-side, one job in flight at a time.
// ---------------------------------------------------------------------------

const queue = [];
let queueActive = null;
let queuePaused = false;
const TERMINAL_ITEM_STATUSES = new Set(['complete', 'error', 'cancelled']);

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function enqueueFiles(files) {
  const rejected = [];
  let added = 0;
  for (const file of files) {
    if (!isSupportedMediaFile(file)) {
      rejected.push(`${file.name || 'file'} (${getFileExtension(file.name || '') || 'no ext'})`);
      continue;
    }
    queue.push({
      id: (crypto.randomUUID ? crypto.randomUUID() : `q-${Date.now()}-${Math.random()}`),
      file,
      status: 'waiting',
      jobId: null,
      formats: null,
      error: null,
    });
    added += 1;
  }
  if (rejected.length > 0) {
    showError(`Skipped ${rejected.length} unsupported file(s): ${rejected.join(', ')}`);
  }
  renderQueue();
  resetDropZoneState();
  return added;
}

function removeQueueItem(id) {
  const idx = queue.findIndex(x => x.id === id);
  if (idx < 0) return;
  if (queue[idx].status !== 'waiting') return;
  queue.splice(idx, 1);
  renderQueue();
  resetDropZoneState();
}

function restartQueueItem(id) {
  const item = queue.find(x => x.id === id);
  if (!item) return;
  if (item.status !== 'cancelled' && item.status !== 'error') return;
  item.status = 'waiting';
  item.jobId = null;
  item.formats = null;
  item.sourceName = null;
  item.error = null;
  renderQueue();
  processNext();
}

function clearCompleted() {
  for (let i = queue.length - 1; i >= 0; i--) {
    if (TERMINAL_ITEM_STATUSES.has(queue[i].status)) queue.splice(i, 1);
  }
  renderQueue();
  resetDropZoneState();
}

function pauseQueue() {
  queuePaused = true;
  renderQueueControls();
}

function resumeQueue() {
  queuePaused = false;
  renderQueueControls();
  processNext();
}

function startQueue() {
  queuePaused = false;
  renderQueueControls();
  processNext();
}

function renderQueueControls() {
  const pauseBtn = document.getElementById('queue-pause');
  const resumeBtn = document.getElementById('queue-resume');
  const startBtn = document.getElementById('queue-start');
  const summary = document.getElementById('queue-summary');
  if (pauseBtn) pauseBtn.hidden = !(queueActive && !queuePaused);
  if (resumeBtn) resumeBtn.hidden = !queuePaused;
  if (startBtn) {
    const hasWaiting = queue.some(x => x.status === 'waiting');
    startBtn.hidden = queueActive !== null || !hasWaiting;
  }
  if (summary) {
    const total = queue.length;
    const waiting = queue.filter(x => x.status === 'waiting').length;
    const done = queue.filter(x => x.status === 'complete').length;
    summary.textContent = `${total} item${total === 1 ? '' : 's'} · ${waiting} waiting · ${done} done`;
  }
}

function renderQueue() {
  const list = document.getElementById('queue-list');
  const empty = document.getElementById('queue-empty');
  if (!list) return;
  list.replaceChildren();
  if (queue.length === 0) {
    if (empty) empty.hidden = false;
    renderQueueControls();
    return;
  }
  if (empty) empty.hidden = true;
  for (const item of queue) list.appendChild(renderQueueRow(item));
  renderQueueControls();
}

function renderQueueRow(item) {
  const card = document.createElement('div');
  card.className = 'card queue-item';
  card.dataset.itemId = item.id;
  card.dataset.status = item.status;
  card.setAttribute('role', 'listitem');

  const row = document.createElement('div');
  row.className = 'queue-item__row';

  const info = document.createElement('div');
  const name = document.createElement('div');
  name.className = 'queue-item__name';
  name.textContent = item.file.name;
  const meta = document.createElement('div');
  meta.className = 'meta';
  const parts = [formatBytes(item.file.size)];
  meta.textContent = parts.filter(Boolean).join(' · ');
  const statusBadge = document.createElement('span');
  statusBadge.className = 'queue-item__status';
  statusBadge.textContent = item.status;
  info.append(name, meta, statusBadge);

  const actions = document.createElement('div');
  actions.className = 'queue-item__actions';

  if (item.status === 'waiting') {
    const rm = document.createElement('button');
    rm.type = 'button';
    rm.className = 'btn btn-compact';
    rm.textContent = 'REMOVE';
    rm.addEventListener('click', () => removeQueueItem(item.id));
    actions.appendChild(rm);
  } else if (item.status === 'complete' && item.formats && item.jobId) {
    const baseName = item.sourceName || item.file.name;
    Object.keys(item.formats).forEach(ext => {
      actions.appendChild(createDownloadLink(item.jobId, ext, {
        compact: true,
        downloadName: friendlyDownloadName(baseName, ext),
      }));
    });
  } else if (item.status === 'error' || item.status === 'cancelled') {
    if (item.error) {
      const err = document.createElement('span');
      err.className = 'meta error-text';
      err.textContent = item.error;
      actions.appendChild(err);
    }
    const restart = document.createElement('button');
    restart.type = 'button';
    restart.className = 'btn btn-compact';
    restart.textContent = 'RESTART';
    restart.addEventListener('click', () => restartQueueItem(item.id));
    actions.appendChild(restart);
  }

  row.append(info, actions);
  card.appendChild(row);
  return card;
}

function collectFormSettings() {
  const fd = new FormData();
  const model = document.getElementById('model');
  const language = document.getElementById('language');
  const timestamps = document.getElementById('timestamps');
  if (model) fd.set('model', model.value);
  if (language && language.value) fd.set('language', language.value);
  fd.set('timestamps', timestamps && timestamps.checked ? 'true' : 'false');
  return fd;
}

async function processNext() {
  if (queuePaused) return;
  if (queueActive) return;
  const next = queue.find(x => x.status === 'waiting');
  if (!next) {
    renderQueueControls();
    return;
  }

  queueActive = next;
  next.status = 'starting';
  renderQueue();

  const data = collectFormSettings();
  data.set('file', next.file);

  try {
    const res = await fetch('/api/transcribe', { method: 'POST', body: data });
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    const { job_id: jobId } = await res.json();
    next.jobId = jobId;
    showActiveJobUI(next);
    showStopButton(jobId);
    listen(jobId, next);
  } catch (err) {
    next.status = 'error';
    next.error = err.message;
    queueActive = null;
    renderQueue();
    processNext();
  }
}

function showActiveJobUI(item) {
  const statusContainer = document.getElementById('status-container');
  const status = document.getElementById('status');
  const message = document.getElementById('message');
  statusContainer.hidden = false;
  status.textContent = 'STARTING';
  status.dataset.state = 'queued';
  document.getElementById('downloads').hidden = true;
  document.getElementById('downloads').replaceChildren();
  if (message) message.textContent = `Processing: ${item.file.name}`;
  renderPhaseLadder(-1, {});
  startTimer();
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

function getFileExtension(filename) {
  const dot = filename.lastIndexOf('.');
  return dot >= 0 ? filename.slice(dot).toLowerCase() : '';
}

function supportedMediaExtensions() {
  const dropZone = document.getElementById('drop-zone');
  const raw = dropZone ? dropZone.dataset.mediaExtensions || '' : '';
  return new Set(raw.split(',').map(ext => ext.trim().toLowerCase()).filter(Boolean));
}

function isSupportedMediaFile(file) {
  const extension = getFileExtension(file.name || '');
  return extension.length > 0 && supportedMediaExtensions().has(extension);
}

function setDropZoneState(state, message) {
  const dropZone = document.getElementById('drop-zone');
  const status = document.getElementById('drop-zone-status');
  if (dropZone) {
    if (state) dropZone.dataset.state = state;
    else delete dropZone.dataset.state;
  }
  if (status && message) status.textContent = message;
}

function resetDropZoneState() {
  const waiting = queue.filter(x => x.status === 'waiting').length;
  if (waiting > 0) setDropZoneState('selected', `${waiting} IN QUEUE`);
  else setDropZoneState('', 'OR CHOOSE FILES');
}

function clearFileInput() {
  const fileInput = document.getElementById('file');
  if (!fileInput) return;
  fileInput.value = '';
  resetDropZoneState();
}

function hasFileDrag(event) {
  const types = event.dataTransfer ? Array.from(event.dataTransfer.types) : [];
  return types.includes('Files');
}

let dragDepth = 0;

function showDropOverlay() {
  const overlay = document.getElementById('drop-overlay');
  if (overlay) overlay.hidden = false;
}

function hideDropOverlay() {
  const overlay = document.getElementById('drop-overlay');
  if (overlay) overlay.hidden = true;
}

function handleDragEnter(event) {
  if (!hasFileDrag(event)) return;
  event.preventDefault();
  dragDepth += 1;
  showDropOverlay();
  setDropZoneState('active', 'DROP TO SELECT');
}

function handleDragOver(event) {
  if (!hasFileDrag(event)) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = 'copy';
  setDropZoneState('active', 'DROP TO SELECT');
}

function handleDragLeave(event) {
  if (!hasFileDrag(event)) return;
  dragDepth = Math.max(0, dragDepth - 1);
  if (dragDepth === 0) {
    hideDropOverlay();
    resetDropZoneState();
  }
}

function handleDrop(event) {
  if (!hasFileDrag(event)) return;
  event.preventDefault();
  dragDepth = 0;
  hideDropOverlay();
  clearError();

  const files = Array.from(event.dataTransfer.files || []);
  if (files.length === 0) {
    resetDropZoneState();
    return;
  }
  enqueueFiles(files);
}

function handleFileInputChange(event) {
  clearError();
  const files = Array.from(event.target.files || []);
  if (files.length === 0) {
    resetDropZoneState();
    return;
  }
  enqueueFiles(files);
  event.target.value = '';
}

function bindDragAndDrop() {
  const fileInput = document.getElementById('file');
  if (fileInput) fileInput.addEventListener('change', handleFileInputChange);

  document.addEventListener('dragenter', handleDragEnter);
  document.addEventListener('dragover', handleDragOver);
  document.addEventListener('dragleave', handleDragLeave);
  document.addEventListener('drop', handleDrop);
  resetDropZoneState();
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const target = current === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', target);
  localStorage.setItem('theme', target);
  const btn = document.getElementById('theme-btn');
  if (btn) btn.textContent = target === 'light' ? 'NIGHT MODE' : 'DAY MODE';
}

function friendlyDownloadName(sourceName, ext) {
  if (!sourceName) return null;
  const dot = sourceName.lastIndexOf('.');
  const stem = dot > 0 ? sourceName.slice(0, dot) : sourceName;
  const slug = stem
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
  if (!slug) return null;
  return `${slug}-transcript.${ext}`;
}

function createDownloadLink(jobId, ext, { compact = false, downloadName = null } = {}) {
  const link = document.createElement('a');
  link.href = `/download/${encodeURIComponent(jobId)}/${encodeURIComponent(ext)}`;
  link.className = compact ? 'btn btn-download btn-download--compact' : 'btn btn-download';
  link.textContent = compact ? ext.toUpperCase() : `DOWNLOAD .${ext.toUpperCase()}`;
  link.target = '_blank';
  link.rel = 'noopener';
  if (downloadName) link.download = downloadName;
  return link;
}

let activeJobId = null;

function showStopButton(jobId) {
  const btn = document.getElementById('stop-btn');
  if (!btn) return;
  activeJobId = jobId;
  btn.hidden = false;
  btn.disabled = false;
  btn.textContent = 'STOP JOB';
}

function hideStopButton() {
  const btn = document.getElementById('stop-btn');
  if (btn) btn.hidden = true;
  activeJobId = null;
}

async function handleStopClick() {
  if (!activeJobId) return;
  const btn = document.getElementById('stop-btn');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'STOPPING...';
  }
  try {
    await fetch(`/api/jobs/${encodeURIComponent(activeJobId)}/cancel`, { method: 'POST' });
  } catch (err) {
    showError(`Stop request failed: ${err.message}`);
  }
}

async function startJob(e) {
  e.preventDefault();
  clearError();

  const urlInput = document.getElementById('url');
  const url = urlInput ? urlInput.value.trim() : '';
  const hasQueuedFiles = queue.some(x => x.status === 'waiting');

  if (url && hasQueuedFiles) {
    showError('Submit either a URL OR queued files, not both.');
    return;
  }

  if (hasQueuedFiles) {
    startQueue();
    return;
  }

  if (!url) {
    showError('Drop files into the queue or paste a URL to begin.');
    return;
  }

  const data = collectFormSettings();
  data.set('url', url);
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
    showStopButton(jobId);
    listen(jobId);
  } catch (err) {
    btn.textContent = originalText;
    btn.disabled = false;
    hideStopButton();
    showError(`Error starting transcription: ${err.message}`);
    stopTimer();
  }
}

function listen(jobId, queueItem = null) {
  const events = new EventSource(`/events/${jobId}`);
  const status = document.getElementById('status');
  const message = document.getElementById('message');
  const output = document.getElementById('output');
  const downloads = document.getElementById('downloads');
  const btn = document.getElementById('submit-btn');
  let lastPhaseIdx = -1;

  const finishActive = () => {
    events.close();
    stopTimer();
    hideStopButton();
    btn.textContent = 'START TRANSCRIPTION';
    btn.disabled = false;
    if (queueItem) {
      queueActive = null;
      renderQueue();
      processNext();
    }
  };

  events.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    const isComplete = data.status === 'complete';
    const isError = data.status === 'error';
    const isCancelled = data.status === 'cancelled';
    const isTerminal = isComplete || isError || isCancelled;
    const mapped = phaseIndexForStatus(data.status);
    if (mapped >= 0) lastPhaseIdx = mapped;
    const phaseIdx = mapped >= 0 ? mapped : lastPhaseIdx;

    let intraProgress = 0;
    if (mapped >= 0 && !isTerminal) {
      const start = PHASE_BOUNDARIES[mapped];
      const end = PHASE_BOUNDARIES[mapped + 1];
      const clamped = Math.max(start, Math.min(end, data.progress || start));
      intraProgress = ((clamped - start) / (end - start)) * 100;
    }

    renderPhaseLadder(phaseIdx, {
      progress: intraProgress,
      complete: isComplete,
      errored: isError || isCancelled,
    });

    if (data.status) {
      status.textContent = data.status.toUpperCase();
      status.dataset.state = data.status;
    }
    message.textContent = data.message || '';

    if (data.result && data.result.text) {
      output.textContent = data.result.text;
    }

    if (queueItem && data.status && !isTerminal) {
      queueItem.status = data.status;
      renderQueue();
    }

    if (isTerminal) {
      if (queueItem) {
        if (isComplete) {
          queueItem.status = 'complete';
          if (data.result) {
            if (data.result.formats) queueItem.formats = data.result.formats;
            if (data.result.source_name) queueItem.sourceName = data.result.source_name;
          }
        } else if (isError) {
          queueItem.status = 'error';
          queueItem.error = data.message || 'Transcription failed';
        } else {
          queueItem.status = 'cancelled';
          queueItem.error = data.message || 'Cancelled';
        }
      }
      finishActive();
    }

    if (isComplete && data.result && data.result.formats) {
      const baseName = (queueItem && (queueItem.sourceName || queueItem.file.name))
        || (data.result && data.result.source_name)
        || null;
      downloads.replaceChildren();
      Object.keys(data.result.formats).forEach(ext => {
        downloads.appendChild(createDownloadLink(jobId, ext, {
          downloadName: friendlyDownloadName(baseName, ext),
        }));
      });
      downloads.hidden = false;
      document.body.classList.add('flash-success');
      setTimeout(() => document.body.classList.remove('flash-success'), 900);
    }
  };

  events.onerror = () => {
    if (queueItem && !TERMINAL_ITEM_STATUSES.has(queueItem.status)) {
      queueItem.status = 'error';
      queueItem.error = 'Connection lost';
    }
    finishActive();
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
  bindDragAndDrop();
  themeBtn.addEventListener('click', toggleTheme);
  document.getElementById('history-btn').addEventListener('click', toggleHistory);
  document.getElementById('history-close').addEventListener('click', toggleHistory);
  const stopBtn = document.getElementById('stop-btn');
  if (stopBtn) stopBtn.addEventListener('click', handleStopClick);

  const startQ = document.getElementById('queue-start');
  const pauseQ = document.getElementById('queue-pause');
  const resumeQ = document.getElementById('queue-resume');
  const clearQ = document.getElementById('queue-clear');
  if (startQ) startQ.addEventListener('click', startQueue);
  if (pauseQ) pauseQ.addEventListener('click', pauseQueue);
  if (resumeQ) resumeQ.addEventListener('click', resumeQueue);
  if (clearQ) clearQ.addEventListener('click', clearCompleted);
  renderQueue();
});
