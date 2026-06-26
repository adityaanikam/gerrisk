# GeriRisk — Environment Variables Setup

## Required for Vercel Deployment

Set these in **Vercel → Project → Settings → Environment Variables**.

---

### Supabase (used by `/api/upload` on Vercel)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL, e.g. `https://xxxx.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Your Supabase anon/public key |

Find both under **Supabase Dashboard → Project → Settings → API**.

---

### Render ML Backend (used by `/api/upload` and `/api/process` on Vercel)

| Variable | Description |
|---|---|
| `ML_API_URL` | Base URL of your Render Python service, e.g. `https://geririsk-ml.onrender.com` |

> **Why this exists:** Vercel serverless functions run in a sandboxed Node.js
> environment and **cannot** spawn child processes (no `child_process.spawn`,
> no filesystem access to `.py` files or `.pkl` models). The ML inference that
> was previously done by calling `predict.py` locally must instead be served by
> a separate Python web service hosted on Render (or any always-on platform).
>
> The Render service should expose a `POST /predict` endpoint that accepts the
> aggregates JSON body and returns `{ cardiacRisk, fallRisk, respiratoryRisk }`.
> See `ml/predict.py` for the existing inference logic to wrap in a Flask/FastAPI
> server.

---

### Local Development (`.env.local`)

Create `geririsk-ai/.env.local` (never commit this file):

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Point to local Python server during dev (e.g. uvicorn / flask on :8000)
ML_API_URL=http://localhost:8000
```

---

### Render Python Service — required environment (on Render)

The Render service itself needs no extra env vars beyond what the Python
inference script already uses. If you add auth to the `/predict` endpoint
later, add a shared secret here and in Vercel as `ML_API_SECRET`.
