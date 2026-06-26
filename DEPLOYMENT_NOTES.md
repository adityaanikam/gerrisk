# GeriRisk — Deployment Notes

## Full Repository Structure

```
GeriRisk-main/                          ← Repo root
│
├── geririsk-ai/                        ← Next.js 16 frontend + API
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               ← Landing page (marketing)
│   │   │   ├── login/page.tsx         ← Login (cookie-based auth)
│   │   │   ├── upload/page.tsx        ← CSV drag-and-drop wizard
│   │   │   ├── dashboard/page.tsx     ← Main analytics dashboard
│   │   │   └── api/
│   │   │       ├── auth/
│   │   │       │   ├── login/route.ts  ← POST: sets HttpOnly session cookie
│   │   │       │   └── logout/route.ts ← POST: clears session cookie
│   │   │       ├── upload/route.ts     ← POST: parse CSV → aggregate → call ML API
│   │   │       └── process/route.ts   ← GET: re-fetch from Supabase → call ML API
│   │   ├── components/                ← React UI components (RiskCard, SleepTimeline…)
│   │   ├── lib/
│   │   │   ├── supabaseClient.ts      ← Supabase singleton (reads NEXT_PUBLIC_ vars)
│   │   │   ├── csvParser.ts           ← PapaParse wrapper
│   │   │   ├── preprocess.ts          ← Data cleaning (nulls, key normalisation)
│   │   │   ├── features.ts            ← Aggregate calculation + sleep extraction
│   │   │   ├── generateAlerts.ts      ← Clinical threshold alert engine
│   │   │   └── api.ts                 ← Shared TypeScript types
│   │   └── middleware.ts              ← Edge middleware: cookie-based route protection
│   ├── ml/
│   │   ├── predict.py                 ← Original CLI inference script (local dev only)
│   │   └── models/                   ← Pre-trained .pkl model files (source of truth)
│   ├── public/                        ← Static assets (SVG logos, images)
│   ├── vercel.json                    ← Vercel deployment configuration
│   ├── ENV_SETUP.md                   ← Environment variable documentation
│   └── .env.local.example             ← Template for local .env.local
│
├── ml-api/                            ← Standalone FastAPI ML service (→ Render)
│   ├── main.py                        ← FastAPI app with POST /predict, GET /health
│   ├── requirements.txt               ← Python dependencies
│   ├── render.yaml                    ← Render Blueprint deployment manifest
│   ├── README.md                      ← ML API local dev + deploy guide
│   └── models/                        ← Copy of .pkl files (used by Render service)
│       ├── cardiac_risk_model.pkl
│       ├── cardiac_scaler.pkl
│       ├── fall_risk_model.pkl
│       ├── fall_scaler.pkl
│       ├── respiratory_risk_model.pkl
│       └── respiratory_scaler.pkl
│
├── GeriRiskCSVs/                      ← Sample wearable CSV data (3 patients, for testing)
├── docker-compose.yml                 ← Docker Compose for local containerised dev
├── requirements.txt                   ← Root Python deps (for Docker build only)
├── DEPLOYMENT_NOTES.md                ← This file
├── DEPLOY.md                          ← Step-by-step deployment commands
└── README.md                          ← Project overview
```

---

## How the Frontend Calls the ML Backend

### Upload Flow (`/api/upload`)

```
Browser
  │
  │  POST /api/upload  (multipart/form-data, CSV file)
  ▼
Next.js API Route (Vercel serverless)
  │
  ├─ 1. Upload CSV → Supabase Storage (graceful, skipped if unreachable)
  ├─ 2. Insert metadata row → Supabase DB
  ├─ 3. Parse CSV with PapaParse
  ├─ 4. Preprocess rows (remove nulls, normalise keys)
  ├─ 5. calculateDatasetAggregates() → { avgHeartRate, maxHR, minHR, minSpO2, totalSteps, recordCount, … }
  ├─ 6. calculateTrends()            → 24-point HR + SpO2 time series
  │
  │  POST ML_API_URL/predict  (JSON aggregates)
  ▼
Render FastAPI service (ml-api/)
  │
  ├─ Load pre-trained scikit-learn models from models/*.pkl
  ├─ Run 3 independent predict_proba() calls
  └─ Return { cardiacRisk, fallRisk, respiratoryRisk }
  │
  ▼
Next.js API Route assembles full response → browser
  │
  └─ Browser stores in localStorage ("dashboard_data") → navigates to /dashboard
```

### Re-process Flow (`/api/process`)

Same as upload but starts by fetching the latest CSV from **Supabase Storage** instead
of a user upload. Same ML API call at the end.

### Authentication Flow

```
POST /api/auth/login  { username, password }
  → validates against hardcoded credentials
  → sets HttpOnly cookie "geririsk_session=authenticated" (24h, Secure, SameSite=Lax)

Next.js Edge Middleware (middleware.ts)
  → runs on every request to /dashboard/:path* and /upload/:path*
  → reads "geririsk_session" cookie server-side
  → redirects to /login if cookie missing or invalid
  → cannot be bypassed from the browser (runs before response is sent)

POST /api/auth/logout
  → sets maxAge=0 on the cookie (browser deletes it immediately)
```

---

## Required Environment Variables

### On Vercel (geririsk-ai/)

| Variable | Value | Notes |
|---|---|---|
| `ML_API_URL` | `https://geririsk-ml-api.onrender.com` | **No trailing slash.** Server-side only. |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://xxxx.supabase.co` | From Supabase → Settings → API |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `eyJ…` | From Supabase → Settings → API |

### On Render (ml-api/)

| Variable | Value | Notes |
|---|---|---|
| `ALLOWED_ORIGIN` | `https://your-app.vercel.app` | Restricts CORS. Use `*` during dev. |
| `PYTHONUNBUFFERED` | `1` | Ensures real-time logs in Render dashboard |
| `PORT` | *(auto-injected by Render)* | Do not set manually |

---

## What Changes Are Needed for Production

### Already done in this codebase

- [x] Python subprocess (`child_process.spawn`) removed from all API routes
- [x] Both `/api/upload` and `/api/process` call `ML_API_URL/predict` via `fetch()`
- [x] Authentication uses HttpOnly cookies via `/api/auth/login` + Edge middleware
- [x] `ml-api/` is a self-contained FastAPI service with `render.yaml`
- [x] `vercel.json` links `ML_API_URL` to a Vercel environment variable secret

### Steps required before deploying

1. **Deploy `ml-api/` to Render** (see `DEPLOY.md`) → copy the service URL
2. **Set env vars in Vercel** — `ML_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
3. **Set `ALLOWED_ORIGIN` on Render** → your Vercel app URL
4. **Configure Supabase** — create `uploads` table and `wearable-uploads` storage bucket

### Supabase table schema required

```sql
create table uploads (
  id            uuid primary key default gen_random_uuid(),
  file_name     text not null,
  file_path     text not null,
  uploaded_at   timestamptz default now()
);
```

Storage bucket: `wearable-uploads` (public or with service-role key)

---

## Local Development Quick Start

```bash
# Terminal 1 — Python ML API
cd ml-api
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — Next.js
cd geririsk-ai
cp .env.local.example .env.local
# Set ML_API_URL=http://localhost:8000 in .env.local
npm install
npm run dev
```

Open <http://localhost:3000>. Login: `admin` / `algoavengers@04`.
