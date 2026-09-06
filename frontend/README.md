# Frontend

Landing (downloaded MA-Darwin HTML) at `/`. Zac’s Document Center at `/app`.

```bash
cd frontend
npm install
echo API_UPSTREAM=http://localhost:8000> .env.local
npm run dev
```

With `API_UPSTREAM` set, `/api/*` rewrites to the FastAPI backend. Without it, Next.js fixture routes still replay `backend/tests/fixtures/`.
