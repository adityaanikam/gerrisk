# GeriRisk — Deployment Guide

> **Prerequisites:** Git, a GitHub account, a Render account (free), a Vercel account (free)

---

## Overview

| Service | Platform | Directory |
|---|---|---|
| Next.js frontend + API | **Vercel** | `geririsk-ai/` |
| Python ML backend | **Render** | `ml-api/` |

---

## Step 1 — Push to GitHub

Replace `FRIEND_USERNAME` and `REPO_NAME` with the actual values.

```bash
# From the repo root (GeriRisk-main/)

# If you haven't initialised git yet:
git init
git add .
git commit -m "initial commit"

# Add the remote and push
git remote add origin https://github.com/FRIEND_USERNAME/REPO_NAME.git
git branch -M main
git push -u origin main
```

If the repo already exists on GitHub:
```bash
git add .
git commit -m "feat: add FastAPI ML backend, connect frontend, prepare for deployment"
git push origin main
```

---

## Step 2 — Deploy `ml-api/` to Render

### Option A — Render Blueprint (recommended, uses `render.yaml`)

1. Go to **render.com** → **New** → **Blueprint**
2. Connect your GitHub repo
3. Render will detect `render.yaml` at the repo root and create the `geririsk-ml-api` service automatically
4. Click **Apply**

### Option B — Manual Web Service

1. Go to **render.com** → **New** → **Web Service**
2. Connect your GitHub repo
3. Fill in the settings:

| Field | Value |
|---|---|
| **Name** | `geririsk-ml-api` |
| **Root Directory** | `ml-api` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free (or Starter for always-on) |

4. Under **Environment Variables**, add:

| Key | Value |
|---|---|
| `ALLOWED_ORIGIN` | `*` *(change this after Vercel deploy)* |
| `PYTHONUNBUFFERED` | `1` |

5. Click **Create Web Service**
6. Wait for the build to complete (~2–3 minutes)
7. **Copy the service URL** — it will look like:
   ```
   https://geririsk-ml-api.onrender.com
   ```

### Verify the ML backend is working

```bash
curl https://geririsk-ml-api.onrender.com/health
# Expected: {"status":"ok"}

curl -X POST https://geririsk-ml-api.onrender.com/predict \
  -H "Content-Type: application/json" \
  -d '{"avgHeartRate":78,"maxHeartRate":120,"minHeartRate":55,"minSpO2":94,"totalSteps":3200,"recordCount":48}'
# Expected: {"cardiacRisk":{...},"fallRisk":{...},"respiratoryRisk":{...}}
```

---

## Step 3 — Deploy `geririsk-ai/` to Vercel

1. Go to **vercel.com** → **Add New** → **Project**
2. Import your GitHub repo
3. Under **Configure Project**, set:

| Field | Value |
|---|---|
| **Framework Preset** | Next.js *(auto-detected)* |
| **Root Directory** | `geririsk-ai` |
| **Build Command** | `npm run build` *(leave as default)* |
| **Output Directory** | `.next` *(leave as default)* |

4. Under **Environment Variables**, add all three:

| Name | Value |
|---|---|
| `ML_API_URL` | `https://geririsk-ml-api.onrender.com` *(no trailing slash)* |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://xxxx.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `eyJ…` |

5. Click **Deploy**
6. Wait for the build (~1–2 minutes)
7. **Copy your Vercel URL** — e.g. `https://geririsk.vercel.app`

---

## Step 4 — Lock down CORS on Render

Now that you have your Vercel URL, update the `ALLOWED_ORIGIN` on Render:

1. Go to Render → `geririsk-ml-api` → **Environment**
2. Change `ALLOWED_ORIGIN` from `*` to your Vercel URL:
   ```
   https://geririsk.vercel.app
   ```
3. Click **Save Changes** — Render will redeploy automatically

---

## Step 5 — Verify End-to-End

1. Open your Vercel URL in the browser
2. Log in with:
   - Username: `admin`
   - Password: `algoavengers@04`
3. Upload one of the sample CSVs from `GeriRiskCSVs/`
4. Confirm the dashboard loads with risk scores, sleep timeline, and alerts

---

## Troubleshooting

### "ML_API_URL not configured" error on Vercel
→ Go to Vercel → Project → Settings → Environment Variables → confirm `ML_API_URL` is set, then redeploy (Deployments → Redeploy)

### Render service returns 503 on `/health`
→ The free plan spins down after inactivity. Wait 30–60 seconds for cold start, then retry.

### Supabase upload fails silently
→ The app degrades gracefully — uploads still work, they just aren't persisted to Supabase. Check your `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` values in Vercel.

### CORS error when calling `/predict` from Vercel
→ The call goes **server-to-server** (Next.js API route → Render), so CORS headers don't apply here. CORS only matters for **browser** calls. If you see a CORS error, the call is being made client-side — verify the `/api/upload` route is calling `ML_API_URL` server-side.

### Login redirects loop
→ Clear cookies and try again. If the issue persists, check that `NODE_ENV=production` is set on Vercel (it is by default) — the `secure` cookie flag requires HTTPS, which Vercel always provides.

---

## Updating the Deployment

```bash
# Make your changes locally, then:
git add .
git commit -m "fix: description of change"
git push origin main

# Vercel auto-deploys on push to main
# Render auto-deploys on push to main (if auto-deploy is enabled)
```
