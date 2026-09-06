const pdfInput = document.getElementById('pdfInput');
const fileName = document.getElementById('fileName');
const statusMessage = document.getElementById('statusMessage');
const pdfPreview = document.getElementById('pdfPreview');
const convertBtn = document.getElementById('convertBtn');

const uploadPanel = document.getElementById('uploadPanel');
const previewPanel = document.getElementById('previewPanel');
const loadingPanel = document.getElementById('loadingPanel');
const resultPanel = document.getElementById('resultPanel');
const loadingDetail = document.getElementById('loadingDetail');

const slideImage = document.getElementById('slideImage');
const slideCounter = document.getElementById('slideCounter');
const thumbStrip = document.getElementById('thumbStrip');
const prevSlide = document.getElementById('prevSlide');
const nextSlide = document.getElementById('nextSlide');
const downloadBtn = document.getElementById('downloadBtn');
const restartBtn = document.getElementById('restartBtn');
const deckTitle = document.getElementById('deckTitle');

const notesInput = document.getElementById('notesInput');
const savedIndicator = document.getElementById('savedIndicator');
const evalBtn = document.getElementById('evalBtn');
const evalResult = document.getElementById('evalResult');
const lockModal = document.getElementById('lockModal');
const lockCancel = document.getElementById('lockCancel');
const lockConfirm = document.getElementById('lockConfirm');
const openEvalBtn = document.getElementById('openEvalBtn');

const evaluationPanel = document.getElementById('evaluationPanel');
const yourEvalText = document.getElementById('yourEvalText');
const backToDeckBtn = document.getElementById('backToDeckBtn');
const evalRestartBtn = document.getElementById('evalRestartBtn');
const skillChangeList = document.getElementById('skillChangeList');
const rejectedNote = document.getElementById('rejectedNote');
const applyChangesBtn = document.getElementById('applyChangesBtn');
const evalHistoryBtn = document.getElementById('evalHistoryBtn');
const toast = document.getElementById('toast');
const toastMsg = document.getElementById('toastMsg');
const toastUndo = document.getElementById('toastUndo');
const emptySuggestions = document.getElementById('emptySuggestions');
const evalResetBtn = document.getElementById('evalResetBtn');
const historyResetBtn = document.getElementById('historyResetBtn');

const regenPanel = document.getElementById('regenPanel');
const regenTitle = document.getElementById('regenTitle');
const regenDetail = document.getElementById('regenDetail');
const regenSteps = document.getElementById('regenSteps');

const comparePanel = document.getElementById('comparePanel');
const cmpV1Img = document.getElementById('cmpV1Img');
const cmpV2Img = document.getElementById('cmpV2Img');
const cmpV1Counter = document.getElementById('cmpV1Counter');
const cmpV2Counter = document.getElementById('cmpV2Counter');
const abChoice = document.getElementById('abChoice');
const abReason = document.getElementById('abReason');
const abSubmitBtn = document.getElementById('abSubmitBtn');
const compareHistoryBtn = document.getElementById('compareHistoryBtn');

const outcomePanel = document.getElementById('outcomePanel');
const outcomeTitle = document.getElementById('outcomeTitle');
const outcomeBody = document.getElementById('outcomeBody');
const outcomeHistoryBtn = document.getElementById('outcomeHistoryBtn');
const outcomeDoneBtn = document.getElementById('outcomeDoneBtn');
const outcomeRestartBtn = document.getElementById('outcomeRestartBtn');

const historyPanel = document.getElementById('historyPanel');
const historyList = document.getElementById('historyList');
const activeVersionLine = document.getElementById('activeVersionLine');
const rejectedListBlock = document.getElementById('rejectedListBlock');
const rejectedList = document.getElementById('rejectedList');
const historyBackBtn = document.getElementById('historyBackBtn');

let selectedFile = null;
let slides = [];
let currentSlide = 0;
let currentDeckId = null;
let currentRunId = null;
let currentRoundN = 1;
let lastRound = null;

const DEFAULT_BRIEF =
  'Create an 8-slide medical affairs MSL deck to present to a physician.';

const THEATER_STEPS = [
  { id: 'skill', label: 'Load the PowerPoint skill', tools: 'SKILL.md · name · version · tools', match: ['skill_loaded', 'skill_load'] },
  { id: 'ocr', label: 'Extract the publication', tools: 'pymupdf · Venice text-parser or digital layer', match: ['ocr_started', 'ocr_page', 'ocr_complete', 'pages_parsed'] },
  { id: 'ledger', label: 'Build the claim ledger', tools: 'Venice or heuristic fallback', match: ['claims_extracted', 'figures_extracted'] },
  { id: 'plan', label: 'Plan the slide sequence', tools: 'Venice planner or heuristic plan', match: ['blueprint_slot_filled'] },
  { id: 'write', label: 'Write the PowerPoint', tools: 'python-pptx', match: ['rendering'] },
  { id: 'gates', label: 'Quality gates + thumbnails', tools: 'soffice · Gate 1 / Gate 2', match: ['gate1_complete', 'gate2_complete'] },
  { id: 'judge', label: 'Judge visual fitness', tools: 'Gate 3 rubric', match: ['judging_slide'] },
  { id: 'done', label: 'Deck ready for review', tools: '', match: ['round_complete', 'awaiting_review', 'plateau'] },
];

const SSE_EVENTS = [
  'pages_parsed', 'claims_extracted', 'figures_extracted', 'blueprint_slot_filled',
  'rendering', 'gate1_complete', 'gate2_complete', 'judging_slide', 'round_complete',
  'awaiting_review', 'plateau', 'error', 'heartbeat', 'skill_loaded', 'skill_load',
  'ocr_started', 'ocr_page', 'ocr_complete', 'library_call', 'library_called',
];

function mediaUrl(path) {
  if (!path) return '';
  if (path.startsWith('http') || path.startsWith('data:') || path.startsWith('/api/')) return path;
  return path.startsWith('/') ? `/api${path}` : `/api/${path}`;
}

function formatElapsed(ms) {
  const s = Math.floor((ms || 0) / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

function roundToDeck(runId, round) {
  const raw = round.slide_svgs && round.slide_svgs.length ? round.slide_svgs : (round.slide_images || []);
  return {
    id: runId,
    title: `Round ${round.n} · M2M deck`,
    slides: raw.map(mediaUrl),
    pdfUrl: mediaUrl(round.preview_pdf_url || round.pdf_url || ''),
    pptxUrl: `/api/runs/${runId}/export?round_n=${round.n}`,
    round_n: round.n,
    gate3: round.gate3,
  };
}

function renderTheater(events, activeName) {
  const list = document.getElementById('theaterSteps');
  if (!list) return;
  const seen = new Set(events.map((e) => e.event));
  let activeIdx = THEATER_STEPS.findIndex((s) => s.match.includes(activeName));
  if (activeIdx < 0) {
    activeIdx = THEATER_STEPS.findLastIndex((s) => s.match.some((n) => seen.has(n)));
  }
  list.innerHTML = THEATER_STEPS.map((s, i) => {
    const state = i < activeIdx ? 'done' : i === activeIdx ? 'active' : '';
    return `<li class="${state}"><span class="mark"></span><span>${s.label}${s.tools ? `<small>${s.tools}</small>` : ''}</span></li>`;
  }).join('');
}

const seenTools = new Set();

function resetTheater() {
  seenTools.clear();
  const box = document.getElementById('theaterTools');
  const list = document.getElementById('theaterToolList');
  if (box) box.hidden = true;
  if (list) list.innerHTML = '';
}

function libraryStep(ev) {
  const tool = String(ev.tool || ev.message || '').toLowerCase();
  if (tool.includes('pymupdf') || tool.includes('ocr') || tool.includes('text-parser')) return 'ocr_started';
  if (tool.includes('planner')) return 'blueprint_slot_filled';
  if (tool.includes('pptx')) return 'rendering';
  if (tool.includes('soffice') || tool.includes('libreoffice')) return 'gate2_complete';
  if (tool.includes('claim') || tool.includes('ledger') || tool.includes('extract')) return 'claims_extracted';
  if (tool.includes('venice') || tool.includes('heuristic')) return 'blueprint_slot_filled';
  return ev.event;
}

function liveLine(ev) {
  const name = ev.skill_name || 'sundai-powerpoint';
  const version = ev.skill_version ? ` ${ev.skill_version}` : '';
  if (ev.event === 'skill_loaded') {
    const tools = (ev.tools || []).join(' · ');
    return tools
      ? `Loaded ${name}${version} — ${tools}`
      : ev.message || `Loaded ${name}${version}`.trim();
  }
  if (ev.event === 'ocr_page') {
    const n = ev.slide || '?';
    const total = ev.slide_total || ev.pages || '?';
    if (/digital text only|VENICE_API_KEY/i.test(ev.message || '')) {
      return `Reading page ${n}/${total} from the PDF text layer (Venice OCR on standby)`;
    }
    return ev.message || `OCR page ${n}/${total}`;
  }
  if (ev.event === 'ocr_started' && /VENICE_API_KEY|digital text/i.test(ev.message || '')) {
    return ev.message.replace(/VENICE_API_KEY not set/i, 'Venice on standby — using the digital text layer');
  }
  if (ev.event === 'library_call') {
    const tool = ev.tool || 'library';
    const msg = ev.message || `Calling ${tool}`;
    if (/heuristic/i.test(msg)) {
      return `${msg} — continuing without Venice`;
    }
    return msg;
  }
  return ev.message || ev.event;
}

function paintTheater(ev) {
  const elapsed = document.getElementById('theaterElapsed');
  const tokens = document.getElementById('theaterTokens');
  const cost = document.getElementById('theaterCost');
  const live = document.getElementById('theaterLive');
  const nameEl = document.getElementById('skillName');
  const ver = document.getElementById('skillVersion');
  if (elapsed) elapsed.textContent = formatElapsed(ev.elapsed_ms);
  if (tokens) tokens.textContent = String(ev.token_count ?? 0);
  if (cost) cost.textContent = `$${(ev.cost_usd ?? 0).toFixed(2)}`;
  if (live) live.textContent = liveLine(ev);
  if (ev.skill_name && nameEl) nameEl.textContent = ev.skill_name;
  if (ev.skill_version && ver) ver.textContent = ev.skill_version;
  const tools = [...(ev.tools || []), ev.tool].filter(Boolean);
  if (tools.length) {
    const box = document.getElementById('theaterTools');
    const list = document.getElementById('theaterToolList');
    if (box && list) {
      box.hidden = false;
      tools.forEach((tool) => {
        if (seenTools.has(tool)) return;
        seenTools.add(tool);
        const li = document.createElement('li');
        li.textContent = tool;
        list.appendChild(li);
      });
    }
  }
}

function subscribeRun(runId, onEvent, onDone, onError) {
  const source = new EventSource(`/api/runs/${runId}/events`);
  const handler = (raw) => {
    let ev;
    try {
      ev = JSON.parse(raw.data);
    } catch {
      return;
    }
    if (!ev.event) ev.event = raw.type;
    onEvent(ev);
    if (ev.event === 'awaiting_review' || ev.event === 'round_complete' || ev.event === 'plateau') {
      source.close();
      onDone(ev);
    } else if (ev.event === 'error') {
      source.close();
      onError(ev);
    }
  };
  source.onmessage = handler;
  SSE_EVENTS.forEach((name) => source.addEventListener(name, handler));
  source.onerror = () => {
    /* keep listening until a terminal event; FastAPI may heartbeat */
  };
  return () => source.close();
}

async function waitForRound(runId, roundN) {
  return new Promise((resolve, reject) => {
    const events = [];
    resetTheater();
    renderTheater(events, 'skill_loaded');
    paintTheater({ event: 'skill_loaded', message: 'Loading sundai-powerpoint…', elapsed_ms: 0, token_count: 0, cost_usd: 0 });
    subscribeRun(
      runId,
      (ev) => {
        events.push(ev);
        paintTheater(ev);
        renderTheater(events, ev.event === 'library_call' ? libraryStep(ev) : ev.event);
      },
      async (ev) => {
        try {
          const n = ev.round_n || roundN;
          const round = await fetch(`/api/runs/${runId}/rounds/${n}`).then((r) => {
            if (!r.ok) throw new Error(`Could not load round ${n}`);
            return r.json();
          });
          lastRound = round;
          currentRoundN = round.n;
          resolve(roundToDeck(runId, round));
        } catch (err) {
          reject(err);
        }
      },
      (ev) => reject(new Error(ev.message || 'Generation failed')),
    );
  });
}

/* ---------- persistence (localStorage; no backend session exists yet) ---------- */
const LAST_DECK_KEY = 'madarwin:lastDeck';
const notesKey = (id) => `madarwin:notes:${id}`;

function readJson(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || 'null');
  } catch {
    return null;
  }
}
function writeJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable — notes just won't persist */
  }
}

/* ---------- view switching ---------- */
function showView(view) {
  const isUpload = view === 'upload';
  const isLoading = view === 'loading';
  const isResult = view === 'result';
  const isEvaluation = view === 'evaluation';

  uploadPanel.hidden = !isUpload;
  previewPanel.hidden = !isUpload;
  loadingPanel.hidden = !isLoading;
  resultPanel.hidden = !isResult;
  evaluationPanel.hidden = !isEvaluation;
  regenPanel.hidden = view !== 'regenerating';
  comparePanel.hidden = view !== 'compare';
  outcomePanel.hidden = view !== 'outcome';
  historyPanel.hidden = view !== 'history';
  window.scrollTo(0, 0);
}

let historyReturnView = 'evaluation';

/* ---------- upload + preview ---------- */
pdfInput.addEventListener('change', (event) => {
  const file = event.target.files[0];
  selectedFile = null;
  convertBtn.hidden = true;

  if (!file) {
    return;
  }

  const isPdf =
    file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');

  if (!isPdf) {
    statusMessage.textContent = 'Please select a valid PDF file.';
    fileName.textContent = 'None';
    pdfPreview.src = 'about:blank';
    return;
  }

  const objectUrl = URL.createObjectURL(file);
  fileName.textContent = file.name;
  pdfPreview.src = objectUrl;
  statusMessage.textContent = 'PDF loaded successfully.';

  selectedFile = file;
  convertBtn.hidden = false;
});

/* ---------- convert ---------- */
convertBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  showView('loading');
  loadingDetail.textContent = 'Uploading the PDF and starting the skill…';
  resetTheater();
  renderTheater([], 'skill_loaded');

  const formData = new FormData();
  formData.append('pdf', selectedFile);
  formData.append('brief', DEFAULT_BRIEF);
  formData.append('blueprint_id', 'msl_physician_8');
  formData.append('skill_version', 'v1');

  try {
    const createdRes = await fetch('/api/runs', { method: 'POST', body: formData });
    if (!createdRes.ok) throw new Error(`Create run failed (${createdRes.status})`);
    const created = await createdRes.json();
    currentRunId = created.id;
    currentDeckId = created.id;
    const startedRes = await fetch(`/api/runs/${created.id}/start`, { method: 'POST' });
    if (!startedRes.ok) throw new Error(`Start failed (${startedRes.status})`);
    const started = await startedRes.json();
    currentRoundN = started.round_n || 1;
    loadingDetail.textContent = 'Skill is running. Events stream in as each step finishes.';
    const data = await waitForRound(created.id, currentRoundN);
    loadDeck(data);
    writeJson(LAST_DECK_KEY, data);
    showView('result');
  } catch (err) {
    loadingDetail.textContent = `Conversion failed: ${err.message}`;
    const live = document.getElementById('theaterLive');
    if (live) live.textContent = err.message;
    setTimeout(() => showView('upload'), 2800);
  }
});

/* ---------- deck load / restore ---------- */
function loadDeck(data) {
  slides = data.slides || [];
  currentSlide = 0;
  currentDeckId = data.id || 'unknown';
  if (data.id) currentRunId = data.id;
  if (data.round_n) currentRoundN = data.round_n;
  lastRound = data.gate3 ? { gate3: data.gate3, n: data.round_n } : lastRound;
  deckTitle.textContent = data.title || 'Deck preview';
  downloadBtn.dataset.url = data.pptxUrl || '';
  const downloadNote = document.getElementById('downloadNote');
  if (downloadNote) {
    downloadNote.hidden = true;
    downloadNote.textContent = '';
  }
  showPdfOrSlides(data.pdfUrl, document.getElementById('deckPdf'), slideImage, document.querySelector('.slide-stage'), document.getElementById('slideCarousel'));

  renderThumbs();
  renderSlide();
  restoreNotes();
}

function showPdfOrSlides(pdfUrl, iframe, img, stage, carousel) {
  if (!iframe) return;
  if (pdfUrl) {
    iframe.hidden = false;
    iframe.src = pdfUrl;
    if (stage) stage.classList.add('has-pdf');
    if (carousel) carousel.classList.add('has-pdf');
    if (img) img.removeAttribute('src');
  } else {
    iframe.hidden = true;
    iframe.removeAttribute('src');
    if (stage) stage.classList.remove('has-pdf');
    if (carousel) carousel.classList.remove('has-pdf');
  }
}

function filenameFromDisposition(header, fallback) {
  if (!header) return fallback;
  const star = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (star) return decodeURIComponent(star[1]);
  const quoted = /filename="([^"]+)"/i.exec(header);
  if (quoted) return quoted[1];
  const plain = /filename=([^;]+)/i.exec(header);
  return plain ? plain[1].trim() : fallback;
}

downloadBtn.addEventListener('click', async (e) => {
  e.preventDefault();
  const url = downloadBtn.dataset.url;
  const note = document.getElementById('downloadNote');
  if (!url) {
    if (note) {
      note.hidden = false;
      note.textContent = 'No generated deck is ready to download yet.';
    }
    return;
  }
  try {
    const res = await fetch(url);
    const type = (res.headers.get('content-type') || '').toLowerCase();
    if (!res.ok) {
      let detail = `Download failed (${res.status})`;
      if (type.includes('json')) {
        const body = await res.json().catch(() => ({}));
        if (body.detail) detail = body.detail;
      }
      throw new Error(detail);
    }
    if (type.includes('json')) {
      throw new Error('Server returned JSON instead of a PowerPoint. Try again or start over.');
    }
    const blob = await res.blob();
    const name = filenameFromDisposition(
      res.headers.get('content-disposition'),
      `Round_${currentRoundN || 1}_M2M.pptx`,
    );
    if (/\.json$/i.test(name)) {
      throw new Error('Refusing to save export.json — the deck file was not returned.');
    }
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objectUrl;
    a.download = name.endsWith('.pptx') ? name : `${name}.pptx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objectUrl);
    if (note) {
      const reason = res.headers.get('x-darwin-export-reason') || '';
      const kind = res.headers.get('x-darwin-export') || '';
      if (kind === 'draft' && reason) {
        note.hidden = false;
        note.textContent = `Draft download — ${reason}`;
      } else {
        note.hidden = true;
        note.textContent = '';
      }
    }
  } catch (err) {
    if (note) {
      note.hidden = false;
      note.textContent = err.message;
    }
  }
});

function clearStoredDeck() {
  try {
    localStorage.removeItem(LAST_DECK_KEY);
  } catch {
    /* ignore */
  }
  try {
    sessionStorage.removeItem(LAST_DECK_KEY);
  } catch {
    /* ignore */
  }
  currentRunId = null;
  currentDeckId = null;
  currentRoundN = 1;
  lastRound = null;
  slides = [];
}

function isMissingRun(res, body) {
  if (res.status === 404) return true;
  const detail = typeof body?.detail === 'string' ? body.detail : JSON.stringify(body?.detail || '');
  return /run not found/i.test(detail);
}

async function restoreLastDeck() {
  showView('upload');
  const data = readJson(LAST_DECK_KEY);
  const runId = data && (data.id || data.run_id);
  if (!runId) {
    if (data) clearStoredDeck();
    return;
  }
  try {
    const res = await fetch(`/api/runs/${runId}`);
    let body = null;
    try {
      body = await res.json();
    } catch {
      body = null;
    }
    if (!res.ok || isMissingRun(res, body)) {
      clearStoredDeck();
      showView('upload');
      return;
    }
    if (selectedFile || (currentRunId && currentRunId !== runId)) return;
    const roundN =
      data.round_n ||
      body.best_round_n ||
      (Array.isArray(body.rounds) && body.rounds.length ? body.rounds[body.rounds.length - 1].n : 1);
    const roundRes = await fetch(`/api/runs/${runId}/rounds/${roundN}`);
    if (!roundRes.ok) {
      clearStoredDeck();
      showView('upload');
      return;
    }
    if (selectedFile || (currentRunId && currentRunId !== runId)) return;
    const live = roundToDeck(runId, await roundRes.json());
    loadDeck(live);
    writeJson(LAST_DECK_KEY, live);
    showView('result');
  } catch {
    clearStoredDeck();
    showView('upload');
  }
}

/* ---------- carousel ---------- */
function renderSlide() {
  const pdf = document.getElementById('deckPdf');
  if (pdf && !pdf.hidden) {
    slideCounter.textContent = slides.length ? `PDF · ${slides.length} slides` : 'PDF preview';
    return;
  }
  if (!slides.length) return;
  slideImage.src = slides[currentSlide];
  slideImage.alt = `Slide ${currentSlide + 1}`;
  slideCounter.textContent = `Slide ${currentSlide + 1} / ${slides.length}`;
  [...thumbStrip.children].forEach((t, i) =>
    t.classList.toggle('active', i === currentSlide)
  );
}

function renderThumbs() {
  thumbStrip.innerHTML = '';
  slides.forEach((src, i) => {
    const thumb = document.createElement('img');
    thumb.src = src;
    thumb.alt = `Go to slide ${i + 1}`;
    thumb.addEventListener('click', () => {
      currentSlide = i;
      renderSlide();
    });
    thumbStrip.appendChild(thumb);
  });
}

function step(delta) {
  if (!slides.length) return;
  currentSlide = (currentSlide + delta + slides.length) % slides.length;
  renderSlide();
}

prevSlide.addEventListener('click', () => step(-1));
nextSlide.addEventListener('click', () => step(1));
document.addEventListener('keydown', (e) => {
  if (resultPanel.hidden) return;
  if (e.target === notesInput) return; // let arrows move the caret in the textarea
  if (!lockModal.hidden) return;
  if (e.key === 'ArrowLeft') step(-1);
  if (e.key === 'ArrowRight') step(1);
});

function restartJourney() {
  slides = [];
  currentSlide = 0;
  selectedFile = null;
  pdfInput.value = '';
  fileName.textContent = 'None';
  statusMessage.textContent = 'Waiting for a PDF file...';
  pdfPreview.src = 'about:blank';
  convertBtn.hidden = true;
  clearStoredDeck();
  showView('upload');
}

restartBtn.addEventListener('click', restartJourney);
evalRestartBtn.addEventListener('click', restartJourney);

/* ---------- notes: autosave + lock flow ---------- */
let saveTimer = null;
let savedFlashTimer = null;

function currentNotes() {
  return readJson(notesKey(currentDeckId)) || { text: '', locked: false };
}

function persistNotes(patch) {
  if (!currentDeckId) return;
  const next = { ...currentNotes(), ...patch, updatedAt: Date.now() };
  writeJson(notesKey(currentDeckId), next);
  return next;
}

function flashSaved() {
  savedIndicator.hidden = false;
  savedIndicator.classList.add('show');
  clearTimeout(savedFlashTimer);
  savedFlashTimer = setTimeout(() => {
    savedIndicator.classList.remove('show');
  }, 1600);
}

function setLockedUI(locked) {
  notesInput.readOnly = locked;
  if (locked) {
    evalBtn.hidden = true;
    evalResult.hidden = false;
  } else {
    evalBtn.hidden = false;
    evalResult.hidden = true;
  }
  refreshEvalButton();
}

function refreshEvalButton() {
  evalBtn.disabled = notesInput.readOnly || notesInput.value.trim().length === 0;
}

function restoreNotes() {
  const saved = currentNotes();
  notesInput.value = saved.text || '';
  savedIndicator.classList.remove('show');
  savedIndicator.hidden = true;
  setLockedUI(Boolean(saved.locked));
}

notesInput.addEventListener('input', () => {
  refreshEvalButton();
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    if (notesInput.readOnly) return;
    persistNotes({ text: notesInput.value });
    flashSaved();
  }, 700);
});

/* ---------- lock confirmation modal ---------- */
function openModal() {
  lockModal.hidden = false;
  lockConfirm.focus();
}
function closeModal() {
  lockModal.hidden = true;
  evalBtn.focus();
}

evalBtn.addEventListener('click', () => {
  if (evalBtn.disabled) return;
  openModal();
});

lockCancel.addEventListener('click', closeModal);
lockModal.addEventListener('click', (e) => {
  if (e.target === lockModal) closeModal(); // click on backdrop
});
document.addEventListener('keydown', (e) => {
  if (!lockModal.hidden && e.key === 'Escape') closeModal();
});

lockConfirm.addEventListener('click', async () => {
  clearTimeout(saveTimer);
  persistNotes({ text: notesInput.value, locked: true });
  setLockedUI(true);
  lockModal.hidden = true;
  if (currentRunId && currentRoundN) {
    try {
      if (notesInput.value.trim()) {
        await fetch(`/api/runs/${currentRunId}/rounds/${currentRoundN}/comments`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            comments: [{
              id: `hc_${crypto.randomUUID().slice(0, 8)}`,
              slide: currentSlide + 1,
              x: 0.5,
              y: 0.5,
              text: notesInput.value.trim(),
              severity: 'must-fix',
              criterion_tag: 'information_density',
              scope: 'always',
            }],
          }),
        });
      }
      await fetch(`/api/runs/${currentRunId}/rounds/${currentRoundN}/lock-evaluation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ locked: true }),
      });
      const sugRes = await fetch(`/api/runs/${currentRunId}/rounds/${currentRoundN}/suggest-skill`, {
        method: 'POST',
      });
      if (sugRes.ok) {
        const sug = await sugRes.json();
        if (Array.isArray(sug.suggestions) && sug.suggestions.length) {
          roundSuggestions = sug.suggestions.map((s, i) => ({
            id: s.id || `s${i + 1}`,
            tag: 'skill',
            title: s.text,
            detail: s.rationale || '',
          }));
        }
      }
    } catch {
      /* keep the on-screen evaluation even if a lock call fails */
    }
  }
  openEvaluation();
});

/* ==========================================================================
   Skill improvement loop (all mock — no real skill editing or API calls)
   ========================================================================== */

/* Full catalogue of suggestions the mock "analysis" can propose. The visible
   list is this set minus anything already in the rejected list for the skill. */
const ALL_SUGGESTIONS = [
  {
    id: 'exec-summary',
    tag: 'structure',
    title: 'Add an executive-summary slide as slide 2',
    detail:
      'Insert a synthesis slide (3–4 bullets: population, key finding with effect size, key safety signal, open question) immediately after the title. Renumber the 8-slide outline to 9.',
  },
  {
    id: 'body-cap',
    tag: 'density',
    title: 'Cap body copy at ~40 words / 5 bullets per slide',
    detail:
      'When source content for a slide exceeds the cap, split into two slides rather than shrinking type. Prefer bullet points over multi-sentence paragraphs on slides 2–4.',
  },
  {
    id: 'split-evidence',
    tag: 'evidence',
    title: 'Split the evidence slide into "design" and "results"',
    detail:
      'One slide for study design + N + population; a second for outcomes. Require a confidence interval on every reported estimate, primary and secondary.',
  },
  {
    id: 'safety-table',
    tag: 'safety',
    title: 'Render safety data as a table, not a paragraph',
    detail:
      'Columns: adverse event, arm, rate, between-arm difference. Keep the oxblood accent reserved for the safety slide only.',
  },
  {
    id: 'unknowns-expand',
    tag: 'completeness',
    title: 'Expand "what remains unknown" to 3+ points',
    detail:
      'Require at least three distinct evidence gaps (e.g. long-term data, subgroup effects, comparator scope) rather than a single summary sentence.',
  },
  {
    id: 'finding-titles',
    tag: 'narrative',
    title: 'Lead each slide title with the finding, not the topic',
    detail:
      'Convert topic labels ("Safety profile") into claim-style titles ("No new safety signals at 12 months") so a skim of titles tells the story.',
  },
  {
    id: 'endpoint-callout',
    tag: 'citations',
    title: 'Add a callout box for the primary endpoint on the results slide',
    detail:
      'Pull the primary effect size + CI + p-value into a boxed callout with the citation directly beneath it.',
  },
  {
    id: 'backup-questions',
    tag: 'backup',
    title: 'Populate the backup slide with 3 anticipated physician questions',
    detail:
      'Replace leftover content with three likely HCP questions and evidence-based responses, each with a source identifier.',
  },
];

const HISTORY_KEY = 'madarwin:skillHistory';
const REJECTED_KEY = 'madarwin:rejectedSuggestions';
const ACTIVE_VERSION_KEY = 'madarwin:activeVersion';

const getHistory = () => readJson(HISTORY_KEY) || [];
const getRejected = () => readJson(REJECTED_KEY) || [];
const getActiveVersion = () => readJson(ACTIVE_VERSION_KEY) || 1;

// Distinct category tags, used for the edit-mode dropdown.
const CATEGORIES = [...new Set(ALL_SUGGESTIONS.map((s) => s.tag))];

// Working copy of this round's suggestions — mutated by inline edit / delete.
// Whatever is in here when "Apply changes & regenerate" is clicked is what
// gets applied and (on a later revert) recorded as rejected.
let roundSuggestions = [];
let editingId = null;
let pendingUndo = null; // { item, index, timer }

// v1 / v2 deck payloads for the compare view.
let v1Deck = null;
let v2Deck = null;
let cmpIdx = { v1: 0, v2: 0 };

/* ---------- AI evaluation view ---------- */
function openEvaluation() {
  const text = (currentNotes().text || '').trim();
  yourEvalText.textContent = text || '(No feedback was entered.)';
  if (!roundSuggestions.length) buildRoundSuggestions();
  const ai = document.getElementById('aiEvalBody');
  if (ai && lastRound && lastRound.gate3) {
    const g = lastRound.gate3;
    const items = (g.criteria || []).slice(0, 8).map((c) => (
      `<h4>${esc(c.criterion)}</h4><p>${esc(c.rationale || '—')} · ${c.score ?? '—'}</p>`
    )).join('');
    ai.innerHTML = `<p>Deck score: <strong>${g.deck_score ?? '—'}</strong></p>${items}`;
  }
  renderSuggestionList();
  showView('evaluation');
}

function buildRoundSuggestions() {
  const rejectedIds = new Set(getRejected().map((r) => r.id));
  // Each analysis round proposes a focused set (max 4), drawn from the
  // catalogue minus anything the evaluator has already rejected for this skill.
  const MAX_PER_ROUND = 4;
  roundSuggestions = ALL_SUGGESTIONS.filter((s) => !rejectedIds.has(s.id))
    .slice(0, MAX_PER_ROUND)
    .map((s) => ({ ...s })); // clone so edits don't touch the catalogue
  editingId = null;
  clearPendingUndo();
}

function esc(str) {
  return String(str).replace(
    /[&<>"']/g,
    (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
  );
}

function renderSuggestionList() {
  skillChangeList.innerHTML = '';

  roundSuggestions.forEach((s, idx) => {
    const li = document.createElement('li');
    li.className = 'skill-change';
    li.dataset.id = s.id;

    if (editingId === s.id) {
      const opts = CATEGORIES.map(
        (c) =>
          `<option value="${c}"${c === s.tag ? ' selected' : ''}>${c}</option>`
      ).join('');
      li.classList.add('editing');
      li.innerHTML = `
        <span class="skill-change-num">${idx + 1}.</span>
        <div class="skill-change-edit">
          <select class="edit-tag">${opts}</select>
          <input class="edit-title notes-input" type="text" value="${esc(s.title)}" />
          <textarea class="edit-detail notes-input" rows="3">${esc(s.detail)}</textarea>
          <div class="edit-actions">
            <button class="convert-btn edit-save" type="button">Save</button>
            <button class="btn-secondary edit-cancel" type="button">Cancel</button>
          </div>
        </div>`;
    } else {
      li.innerHTML = `
        <span class="skill-change-num">${idx + 1}.</span>
        <span class="skill-change-tag">${esc(s.tag)}</span>
        <div class="skill-change-main">
          <p class="skill-change-title">${esc(s.title)}</p>
          <p class="skill-change-detail">${esc(s.detail)}</p>
        </div>
        <div class="skill-change-actions">
          <button class="icon-btn sc-edit" type="button" title="Edit" aria-label="Edit suggestion">✎</button>
          <button class="icon-btn sc-delete" type="button" title="Delete" aria-label="Delete suggestion">🗑</button>
        </div>`;
    }

    skillChangeList.appendChild(li);
  });

  renderRejectedNote();
  refreshApplyButton();
}

function renderRejectedNote() {
  const rejected = getRejected();
  if (rejected.length) {
    const lines = rejected
      .map((r) => `“${esc(r.title)}” — rejected because: ${esc(r.reason)}`)
      .join('<br />');
    rejectedNote.innerHTML =
      `<strong>${rejected.length} suggestion(s) hidden.</strong> ` +
      `Tried in an earlier round and rejected by the evaluator, so they are not proposed again:<br />${lines}`;
    rejectedNote.hidden = false;
  } else {
    rejectedNote.hidden = true;
  }
}

function refreshApplyButton() {
  const empty = roundSuggestions.length === 0;
  applyChangesBtn.disabled = empty || editingId !== null;
  applyChangesBtn.textContent = empty
    ? 'No suggestions to apply'
    : 'Apply changes & regenerate';

  // Show the "everything's been tried" helper only when the list is empty
  // *because* the catalogue is exhausted (not just mid-session with 0 shown).
  const exhausted = empty && getRejected().length >= ALL_SUGGESTIONS.length;
  emptySuggestions.hidden = !exhausted;
}

/* ---------- reset mock skill data ---------- */
function resetSkillData() {
  [HISTORY_KEY, REJECTED_KEY, ACTIVE_VERSION_KEY].forEach((k) => {
    try {
      localStorage.removeItem(k);
    } catch {
      /* ignore */
    }
  });
  toastMsg.textContent = 'Skill history & rejected suggestions cleared';
  toast.hidden = false;
  clearTimeout(resetToastTimer);
  resetToastTimer = setTimeout(() => {
    if (toastMsg.textContent.startsWith('Skill history')) toast.hidden = true;
  }, 3000);
  toastUndo.hidden = true; // nothing to undo for a reset

  buildRoundSuggestions();
  renderSuggestionList();
}
let resetToastTimer = null;

evalResetBtn.addEventListener('click', () => {
  resetSkillData();
  showView('evaluation');
});
historyResetBtn.addEventListener('click', () => {
  resetSkillData();
  openHistory(historyReturnView);
});

/* ---------- inline edit / delete ---------- */
skillChangeList.addEventListener('click', (e) => {
  const li = e.target.closest('.skill-change');
  if (!li) return;
  const id = li.dataset.id;

  if (e.target.classList.contains('sc-edit')) {
    editingId = id;
    renderSuggestionList();
    li.parentElement.querySelector('.editing .edit-title')?.focus();
  } else if (e.target.classList.contains('sc-delete')) {
    deleteSuggestion(id);
  } else if (e.target.classList.contains('edit-cancel')) {
    editingId = null;
    renderSuggestionList();
  } else if (e.target.classList.contains('edit-save')) {
    const s = roundSuggestions.find((x) => x.id === id);
    if (s) {
      s.tag = li.querySelector('.edit-tag').value;
      s.title = li.querySelector('.edit-title').value.trim() || s.title;
      s.detail = li.querySelector('.edit-detail').value.trim() || s.detail;
      s.edited = true;
    }
    editingId = null;
    renderSuggestionList();
  }
});

function deleteSuggestion(id) {
  const index = roundSuggestions.findIndex((x) => x.id === id);
  if (index === -1) return;
  const [item] = roundSuggestions.splice(index, 1);
  if (editingId === id) editingId = null;
  renderSuggestionList();
  showUndoToast(item, index);
}

/* ---------- undo toast ---------- */
function showUndoToast(item, index) {
  clearPendingUndo();
  toastMsg.textContent = 'Suggestion removed';
  toastUndo.hidden = false;
  toast.hidden = false;
  const timer = setTimeout(clearPendingUndo, 5000);
  pendingUndo = { item, index, timer };
}

function clearPendingUndo() {
  if (pendingUndo) clearTimeout(pendingUndo.timer);
  pendingUndo = null;
  if (toast) toast.hidden = true;
}

toastUndo.addEventListener('click', () => {
  if (!pendingUndo) return;
  const { item, index } = pendingUndo;
  roundSuggestions.splice(Math.min(index, roundSuggestions.length), 0, item);
  clearPendingUndo();
  renderSuggestionList();
});

openEvalBtn.addEventListener('click', openEvaluation);
backToDeckBtn.addEventListener('click', () => showView('result'));

/* ---------- apply changes & regenerate (mock) ---------- */
const REGEN_STEPS = [
  'Applying suggested changes to the skill',
  'Regenerating the deck from the same PDF',
  'Rendering the updated slides',
];

function renderRegenSteps(activeIndex) {
  regenSteps.innerHTML = '';
  REGEN_STEPS.forEach((label, i) => {
    const li = document.createElement('li');
    li.textContent = label;
    if (i < activeIndex) li.className = 'done';
    else if (i === activeIndex) li.className = 'active';
    regenSteps.appendChild(li);
  });
}

applyChangesBtn.addEventListener('click', async () => {
  if (!roundSuggestions.length || !currentRunId) return;

  showView('regenerating');
  regenTitle.textContent = 'Updating skill…';
  regenDetail.textContent = `Applying ${roundSuggestions.length} suggested change(s).`;
  renderRegenSteps(0);

  try {
    await fetch(`/api/runs/${currentRunId}/rounds/${currentRoundN}/lock-evaluation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ locked: true }),
    });
    const res = await fetch(`/api/runs/${currentRunId}/apply-skill`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        suggestions: roundSuggestions.map((s) => s.title || s.text || s.detail).filter(Boolean),
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Apply failed (${res.status})`);
    }
    const started = await res.json();
    currentRoundN = started.round_n || currentRoundN + 1;
    regenTitle.textContent = 'Regenerating deck…';
    regenDetail.textContent = 'Re-running the skill on the same PDF. Watch the live steps.';
    renderRegenSteps(1);
    v2Deck = await waitForRound(currentRunId, currentRoundN);
    renderRegenSteps(2);
    v1Deck = readJson(LAST_DECK_KEY);
    openCompare();
  } catch (err) {
    regenTitle.textContent = 'Regeneration failed';
    regenDetail.textContent = err.message;
    await sleep(2000);
    showView('evaluation');
  }
});

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

/* ---------- compare v1 vs v2 ---------- */
function openCompare() {
  cmpIdx = { v1: 0, v2: 0 };
  renderCmp('v1');
  renderCmp('v2');
  abReason.value = '';
  [...abChoice.querySelectorAll('input')].forEach((i) => (i.checked = false));
  refreshAbSubmit();
  document.getElementById('v1Tag').textContent = `Active skill version ${getActiveVersion()}`;
  showView('compare');
}

function renderCmp(side) {
  const deck = side === 'v1' ? v1Deck : v2Deck;
  const img = side === 'v1' ? cmpV1Img : cmpV2Img;
  const iframe = document.getElementById(side === 'v1' ? 'cmpV1Pdf' : 'cmpV2Pdf');
  const counter = side === 'v1' ? cmpV1Counter : cmpV2Counter;
  if (!deck) return;
  if (deck.pdfUrl && iframe) {
    showPdfOrSlides(deck.pdfUrl, iframe, img, iframe.parentElement, iframe.closest('.mini-carousel'));
    counter.textContent = deck.slides && deck.slides.length ? `PDF · ${deck.slides.length} slides` : 'PDF preview';
    return;
  }
  if (iframe) showPdfOrSlides('', iframe, img, iframe.parentElement, iframe.closest('.mini-carousel'));
  if (!deck.slides || !deck.slides.length) return;
  const i = cmpIdx[side];
  img.src = deck.slides[i];
  counter.textContent = `Slide ${i + 1} / ${deck.slides.length}`;
}

comparePanel.querySelectorAll('.carousel-nav[data-cmp]').forEach((btn) => {
  btn.addEventListener('click', () => {
    const side = btn.dataset.cmp;
    const dir = Number(btn.dataset.dir);
    const deck = side === 'v1' ? v1Deck : v2Deck;
    if (!deck) return;
    const len = deck.slides.length;
    cmpIdx[side] = (cmpIdx[side] + dir + len) % len;
    renderCmp(side);
  });
});

function refreshAbSubmit() {
  const picked = abChoice.querySelector('input:checked');
  abSubmitBtn.disabled = !picked || abReason.value.trim().length === 0;
}
abChoice.addEventListener('change', refreshAbSubmit);
abReason.addEventListener('input', refreshAbSubmit);

/* ---------- decision + branching outcome ---------- */
abSubmitBtn.addEventListener('click', () => {
  const picked = abChoice.querySelector('input:checked');
  const reason = abReason.value.trim();
  if (!picked || !reason) return;

  const history = getHistory();
  const roundNo = history.length + 1;
  const triedIds = roundSuggestions.map((s) => s.id);
  const triedTitles = roundSuggestions.map((s) => s.title);
  const attemptedVersion = getActiveVersion() + 1;

  if (currentRunId) {
    const winner = picked.value === 'v2' ? (v2Deck && v2Deck.round_n) || currentRoundN : (v1Deck && v1Deck.round_n) || 1;
    fetch(`/api/runs/${currentRunId}/decide`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ winner_round_n: winner }),
    }).catch(() => undefined);
  }

  if (picked.value === 'v2') {
    // keep v2 as the active skill version
    writeJson(ACTIVE_VERSION_KEY, attemptedVersion);
    writeJson(LAST_DECK_KEY, v2Deck); // v2 becomes the deck we show at rest
    history.push({
      round: roundNo,
      attemptedVersion,
      activeAfter: attemptedVersion,
      outcome: 'accepted',
      reason,
      suggestionIds: triedIds,
      suggestionTitles: triedTitles,
      at: Date.now(),
    });
    writeJson(HISTORY_KEY, history);
    loadDeck(v2Deck);
    renderOutcome('accepted', attemptedVersion, reason, triedTitles);
  } else {
    // revert: discard v2, keep v1; log tried suggestions as rejected
    const rejected = getRejected();
    const existing = new Set(rejected.map((r) => r.id));
    roundSuggestions.forEach((s) => {
      if (!existing.has(s.id)) {
        rejected.push({ id: s.id, title: s.title, reason, at: Date.now() });
      }
    });
    writeJson(REJECTED_KEY, rejected);
    history.push({
      round: roundNo,
      attemptedVersion,
      activeAfter: getActiveVersion(),
      outcome: 'reverted',
      reason,
      suggestionIds: triedIds,
      suggestionTitles: triedTitles,
      at: Date.now(),
    });
    writeJson(HISTORY_KEY, history);
    renderOutcome('reverted', getActiveVersion(), reason, triedTitles);
  }
});

function renderOutcome(outcome, activeVersion, reason, triedTitles) {
  const accepted = outcome === 'accepted';
  outcomeTitle.textContent = accepted
    ? 'Skill updated'
    : 'Reverted to previous version';

  const list = triedTitles.map((t) => `<li>${t}</li>`).join('');

  outcomeBody.innerHTML = accepted
    ? `
      <div class="outcome-banner accepted">✓ Version ${activeVersion} is now active</div>
      <p>The evaluator picked the regenerated deck. Version ${activeVersion} of
      the skill is kept as active and this round is logged in the version
      history.</p>
      <p><strong>Changes kept in this version:</strong></p>
      <ul>${list}</ul>
      <p class="history-reason">Reason given: “${reason}”</p>`
    : `
      <div class="outcome-banner reverted">↩ Version ${activeVersion} remains active</div>
      <p>The evaluator picked the original deck. Version 2 was discarded and the
      skill stays at version ${activeVersion}.</p>
      <p><strong>Suggestions recorded as rejected (won't be proposed again):</strong></p>
      <ul>${list}</ul>
      <p class="history-reason">Reason given: “${reason}”</p>`;

  showView('outcome');
}

/* ---------- version history view ---------- */
function openHistory(returnView) {
  historyReturnView = returnView || 'evaluation';
  const history = getHistory();
  activeVersionLine.textContent = `Active version: ${getActiveVersion()}`;

  historyList.innerHTML = '';
  if (!history.length) {
    const li = document.createElement('li');
    li.className = 'history-empty';
    li.textContent = 'No improvement rounds yet.';
    historyList.appendChild(li);
  } else {
    [...history].reverse().forEach((r) => {
      const li = document.createElement('li');
      li.className = 'history-round';
      const sugg = r.suggestionTitles.map((t) => `<li>${t}</li>`).join('');
      li.innerHTML = `
        <div class="history-round-head">
          <strong>Round ${r.round}</strong>
          <span>Attempted v${r.attemptedVersion}</span>
          <span class="outcome-pill ${r.outcome}">${r.outcome}</span>
          <span>· active after: v${r.activeAfter}</span>
        </div>
        <p class="history-reason">“${r.reason}”</p>
        <p class="skill-change-detail">Suggestions this round:</p>
        <ul class="history-suggestions">${sugg}</ul>`;
      historyList.appendChild(li);
    });
  }

  const rejected = getRejected();
  if (rejected.length) {
    rejectedList.innerHTML = rejected
      .map((r) => `<li>“${r.title}” — ${r.reason}</li>`)
      .join('');
    rejectedListBlock.hidden = false;
  } else {
    rejectedListBlock.hidden = true;
  }

  showView('history');
}

evalHistoryBtn.addEventListener('click', () => openHistory('evaluation'));
compareHistoryBtn.addEventListener('click', () => openHistory('compare'));
outcomeHistoryBtn.addEventListener('click', () => openHistory('outcome'));
historyBackBtn.addEventListener('click', () => showView(historyReturnView));

outcomeDoneBtn.addEventListener('click', () => showView('result'));
outcomeRestartBtn.addEventListener('click', restartJourney);

/* ---------- boot: always start on upload; restore only if the run still exists ---------- */
showView('upload');
restoreLastDeck();
