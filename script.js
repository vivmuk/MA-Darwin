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
  loadingDetail.textContent = 'Uploading document and generating slides…';

  const formData = new FormData();
  formData.append('pdf', selectedFile);

  try {
    const res = await fetch('/api/convert', { method: 'POST', body: formData });
    if (!res.ok) throw new Error(`Server responded ${res.status}`);
    const data = await res.json();

    loadDeck(data);
    writeJson(LAST_DECK_KEY, data);
    showView('result');
  } catch (err) {
    loadingDetail.textContent = `Conversion failed: ${err.message}`;
    setTimeout(() => showView('upload'), 2500);
  }
});

/* ---------- deck load / restore ---------- */
function loadDeck(data) {
  slides = data.slides || [];
  currentSlide = 0;
  currentDeckId = data.id || 'unknown';
  deckTitle.textContent = data.title || 'PowerPoint preview';
  downloadBtn.href = data.pptxUrl || '#';

  renderThumbs();
  renderSlide();
  restoreNotes();
}

function restoreLastDeck() {
  const data = readJson(LAST_DECK_KEY);
  if (data && Array.isArray(data.slides) && data.slides.length) {
    loadDeck(data);
    showView('result');
  }
}

/* ---------- carousel ---------- */
function renderSlide() {
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
  currentDeckId = null;
  selectedFile = null;
  pdfInput.value = '';
  fileName.textContent = 'None';
  statusMessage.textContent = 'Waiting for a PDF file...';
  pdfPreview.src = 'about:blank';
  convertBtn.hidden = true;
  try {
    localStorage.removeItem(LAST_DECK_KEY);
  } catch {
    /* ignore */
  }
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

lockConfirm.addEventListener('click', () => {
  // flush any pending edit, then lock
  clearTimeout(saveTimer);
  persistNotes({ text: notesInput.value, locked: true });
  setLockedUI(true);
  lockModal.hidden = true;
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
  buildRoundSuggestions();
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
}

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
  if (!roundSuggestions.length) return;

  showView('regenerating');
  regenTitle.textContent = 'Updating skill…';
  regenDetail.textContent = `Applying ${roundSuggestions.length} suggested change(s).`;
  renderRegenSteps(0);

  await sleep(900);
  regenTitle.textContent = 'Regenerating deck…';
  regenDetail.textContent = 'Re-running the conversion on the same PDF.';
  renderRegenSteps(1);

  try {
    const res = await fetch('/api/regenerate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ deckId: currentDeckId }),
    });
    if (!res.ok) throw new Error(`Server responded ${res.status}`);
    v2Deck = await res.json();
  } catch (err) {
    regenTitle.textContent = 'Regeneration failed';
    regenDetail.textContent = err.message;
    await sleep(2000);
    showView('evaluation');
    return;
  }

  renderRegenSteps(2);
  await sleep(700);

  v1Deck = readJson(LAST_DECK_KEY);
  openCompare();
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
  const counter = side === 'v1' ? cmpV1Counter : cmpV2Counter;
  if (!deck || !deck.slides || !deck.slides.length) return;
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

/* ---------- boot ---------- */
restoreLastDeck();
