/**
 * MA Darwin - PDF to PowerPoint backend
 *
 * Serves the static frontend AND the conversion API from a single origin, so
 * the browser only ever talks to us -- never directly to Anthropic.
 *
 * The ANTHROPIC_API_KEY is read from the environment and stays server-side.
 * It is NEVER sent to the client. Right now the conversion itself is MOCKED:
 * POST /api/convert accepts the PDF, waits, and returns canned slide images +
 * a placeholder .pptx. The real skill invocation gets wired in later inside
 * runConversion().
 */

const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const express = require('express');
const multer = require('multer');

const PORT = process.env.PORT || 3000;
const ROOT = path.join(__dirname, '..');
const UPLOAD_DIR = path.join(ROOT, 'uploads');
const MOCK_DIR = path.join(__dirname, 'mock');

fs.mkdirSync(UPLOAD_DIR, { recursive: true });

const app = express();

const upload = multer({
  dest: UPLOAD_DIR,
  limits: { fileSize: 25 * 1024 * 1024 }, // 25 MB
  fileFilter: (_req, file, cb) => {
    const ok =
      file.mimetype === 'application/pdf' ||
      file.originalname.toLowerCase().endsWith('.pdf');
    cb(ok ? null : new Error('Only PDF files are accepted'), ok);
  },
});

// In-memory registry of generated decks: id -> { dir, title, slideCount }
const decks = new Map();

/**
 * Turn an uploaded PDF into a deck.
 *
 * MOCK IMPLEMENTATION: ignores the PDF content and returns the bundled sample
 * slides. Kept async and isolated so the real version -- call the Anthropic API
 * with process.env.ANTHROPIC_API_KEY + the sundai-powerpoint skill, then render
 * slides to PNG (via LibreOffice: pptx -> pdf -> png) -- is a drop-in swap.
 */
async function runConversion(pdfPath) {
  await new Promise((r) => setTimeout(r, 2000)); // simulate work

  const id = crypto.randomUUID();
  const slideCount = 8;
  const slides = Array.from(
    { length: slideCount },
    (_, i) => `/api/decks/${id}/slide-${i + 1}.svg`
  );

  decks.set(id, {
    id,
    title: 'DRAFT M2M deck (mock)',
    slideCount,
    slides,
    pptxUrl: `/api/decks/${id}/deck.pptx`,
    sourcePdf: pdfPath,
  });

  return decks.get(id);
}

app.post('/api/convert', upload.single('pdf'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No PDF uploaded (field name: pdf)' });
  }
  try {
    const deck = await runConversion(req.file.path);
    res.json({
      id: deck.id,
      title: deck.title,
      version: deck.version,
      slideCount: deck.slideCount,
      slides: deck.slides,
      pptxUrl: deck.pptxUrl,
    });
  } catch (err) {
    console.error('Conversion error:', err);
    res.status(500).json({ error: 'Conversion failed' });
  }
});

/**
 * Re-run the conversion on the SAME source PDF after (mock) skill changes.
 *
 * MOCK IMPLEMENTATION: ignores the applied suggestions and returns a fixed
 * "v2" deck (9 slides — adds an executive summary, splits evidence into
 * design/results, renders safety as a table). Real version would edit the
 * skill file, re-invoke it against deck.sourcePdf, and re-render.
 */
app.post('/api/regenerate', express.json(), async (req, res) => {
  const sourceId = req.body && req.body.deckId;
  const source = sourceId && decks.get(sourceId);

  await new Promise((r) => setTimeout(r, 900)); // "updating skill"
  await new Promise((r) => setTimeout(r, 1100)); // "regenerating deck"

  const id = crypto.randomUUID();
  const slideCount = 9;
  const slides = Array.from(
    { length: slideCount },
    (_, i) => `/api/decks/${id}/slide-${i + 1}.svg`
  );

  decks.set(id, {
    id,
    title: 'DRAFT M2M deck (v2 — updated)',
    version: 2,
    variant: 'v2',
    slideCount,
    slides,
    pptxUrl: `/api/decks/${id}/deck.pptx`,
    sourcePdf: source ? source.sourcePdf : null,
    regeneratedFrom: sourceId || null,
  });

  res.json({
    id,
    title: 'DRAFT M2M deck (v2 — updated)',
    version: 2,
    slideCount,
    slides,
    pptxUrl: `/api/decks/${id}/deck.pptx`,
  });
});

// Serve generated deck assets. In the mock, every deck maps to the same
// bundled sample files.
app.get('/api/decks/:id/:asset', (req, res) => {
  const { id, asset } = req.params;
  if (!decks.has(id)) return res.status(404).send('Unknown deck');

  if (/^slide-\d+\.svg$/.test(asset)) {
    const n = Number(asset.match(/\d+/)[0]);
    const deck = decks.get(id);
    return res
      .type('image/svg+xml')
      .send(mockSlideSvg(n, deck.slideCount, deck.variant));
  }
  if (asset === 'deck.pptx') {
    const file = path.join(MOCK_DIR, 'deck.pptx');
    if (fs.existsSync(file)) {
      return res.download(file, 'converted-deck.pptx');
    }
    return res.status(404).send('Mock deck.pptx not found');
  }
  return res.status(404).send('Unknown asset');
});

app.get('/api/health', (_req, res) => {
  res.json({
    ok: true,
    mock: true,
    anthropicKeyConfigured: Boolean(process.env.ANTHROPIC_API_KEY),
  });
});

// Static frontend (index.html, script.js, styles.css) from the repo root.
app.use(
  express.static(ROOT, {
    index: 'index.html',
    setHeaders: (res, filePath) => {
      if (filePath.endsWith('.html')) res.setHeader('Cache-Control', 'no-store');
    },
  })
);

app.listen(PORT, () => {
  console.log(`MA Darwin server on http://localhost:${PORT}`);
  console.log(`  conversion: MOCK`);
  console.log(
    `  ANTHROPIC_API_KEY: ${process.env.ANTHROPIC_API_KEY ? 'configured' : 'NOT set'}`
  );
});

/* ----------------- mock slide rendering ----------------- */
const SLIDE_TITLES = {
  v1: [
    'Title slide - DRAFT',
    'Disease context',
    'Unmet need',
    'The evidence',
    'Safety profile',
    'What remains unknown',
    'References',
    'Backup - anticipated questions',
  ],
  v2: [
    'Title slide - DRAFT',
    'Executive summary (NEW)',
    'Disease context',
    'Unmet need',
    'Study design',
    'Results (CIs on all estimates)',
    'Safety profile - table',
    'What remains unknown (3 gaps)',
    'References',
  ],
};

function mockSlideSvg(n, total, variant) {
  const titles = SLIDE_TITLES[variant === 'v2' ? 'v2' : 'v1'];
  const label = titles[n - 1] || `Slide ${n}`;
  const accent = variant === 'v2' ? '#0f766e' : '#1d4ed8';
  const soft = variant === 'v2' ? '#ccfbf1' : '#dbeafe';
  const tag = variant === 'v2' ? 'MOCK PREVIEW - V2' : 'MOCK PREVIEW';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" font-family="Arial, Helvetica, sans-serif">
  <rect width="1280" height="720" fill="#ffffff"/>
  <rect width="1280" height="14" fill="${accent}"/>
  <rect x="0" y="706" width="1280" height="14" fill="${soft}"/>
  <text x="64" y="120" font-size="30" fill="${accent}" font-weight="700" letter-spacing="3">${tag}</text>
  <text x="64" y="230" font-size="60" fill="#0f172a" font-weight="700">${label}</text>
  <text x="64" y="300" font-size="30" fill="#475569">Placeholder slide ${n} of ${total}</text>
  <text x="64" y="356" font-size="24" fill="#475569">Mock content — real slides come from the sundai-powerpoint</text>
  <text x="64" y="388" font-size="24" fill="#475569">skill via the Anthropic API.</text>
  <circle cx="1120" cy="560" r="90" fill="${soft}"/>
  <text x="1120" y="575" font-size="72" fill="${accent}" font-weight="700" text-anchor="middle">${n}</text>
</svg>`;
}
