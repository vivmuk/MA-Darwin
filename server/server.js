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
      slideCount: deck.slideCount,
      slides: deck.slides,
      pptxUrl: deck.pptxUrl,
    });
  } catch (err) {
    console.error('Conversion error:', err);
    res.status(500).json({ error: 'Conversion failed' });
  }
});

// Serve generated deck assets. In the mock, every deck maps to the same
// bundled sample files.
app.get('/api/decks/:id/:asset', (req, res) => {
  const { id, asset } = req.params;
  if (!decks.has(id)) return res.status(404).send('Unknown deck');

  if (/^slide-\d+\.svg$/.test(asset)) {
    const n = Number(asset.match(/\d+/)[0]);
    return res.type('image/svg+xml').send(mockSlideSvg(n, decks.get(id).slideCount));
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
function mockSlideSvg(n, total) {
  const titles = [
    'Title slide - DRAFT',
    'Disease context',
    'Unmet need',
    'The evidence',
    'Safety profile',
    'What remains unknown',
    'References',
    'Backup - anticipated questions',
  ];
  const label = titles[n - 1] || `Slide ${n}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" font-family="Arial, Helvetica, sans-serif">
  <rect width="1280" height="720" fill="#ffffff"/>
  <rect width="1280" height="14" fill="#1d4ed8"/>
  <rect x="0" y="706" width="1280" height="14" fill="#dbeafe"/>
  <text x="64" y="120" font-size="30" fill="#1d4ed8" font-weight="700" letter-spacing="3">MOCK PREVIEW</text>
  <text x="64" y="230" font-size="64" fill="#0f172a" font-weight="700">${label}</text>
  <text x="64" y="300" font-size="30" fill="#475569">Placeholder slide ${n} of ${total}</text>
  <text x="64" y="356" font-size="24" fill="#475569">Real content will be generated from the uploaded PDF</text>
  <text x="64" y="388" font-size="24" fill="#475569">by the sundai-powerpoint skill via the Anthropic API.</text>
  <circle cx="1120" cy="560" r="90" fill="#dbeafe"/>
  <text x="1120" y="575" font-size="72" fill="#1d4ed8" font-weight="700" text-anchor="middle">${n}</text>
</svg>`;
}
