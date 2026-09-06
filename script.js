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
  window.scrollTo(0, 0);
}

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

/* ---------- AI evaluation view (mock content, no API yet) ---------- */
function openEvaluation() {
  const text = (currentNotes().text || '').trim();
  yourEvalText.textContent = text || '(No feedback was entered.)';
  showView('evaluation');
}

openEvalBtn.addEventListener('click', openEvaluation);
backToDeckBtn.addEventListener('click', () => showView('result'));

/* ---------- boot ---------- */
restoreLastDeck();
