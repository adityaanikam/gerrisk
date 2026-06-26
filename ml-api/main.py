"""
GeriRisk ML API — FastAPI inference service
============================================
Wraps the predict.py logic in an HTTP service suitable for Render deployment.

Endpoint
--------
POST /predict
    Body  : PredictRequest  (see schema below)
    Returns: PredictionResponse

GET /health
    Returns: {"status": "ok"}

Environment variables
---------------------
ALLOWED_ORIGIN  (optional)
    Comma-separated list of origins to allow for CORS.
    Defaults to "*" (all origins) when not set.
    Example: https://geririsk.vercel.app,https://geririsk-staging.vercel.app
"""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("geririsk-ml")

# ─── Model loading ────────────────────────────────────────────────────────────

MODELS_DIR = Path(__file__).parent / "models"


def _load(filename: str):
    """Load a joblib artefact from the models directory."""
    path = MODELS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Model file not found: {path}. "
            "Ensure the models/ directory is present and contains all .pkl files."
        )
    return joblib.load(path)


# Module-level model store — populated at startup, never reloaded per-request.
_models: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all models once on startup; release on shutdown."""
    logger.info("Loading ML models from %s …", MODELS_DIR)
    _models["cardiac_model"]  = _load("cardiac_risk_model.pkl")
    _models["cardiac_scaler"] = _load("cardiac_scaler.pkl")
    _models["fall_model"]     = _load("fall_risk_model.pkl")
    _models["fall_scaler"]    = _load("fall_scaler.pkl")
    _models["resp_model"]     = _load("respiratory_risk_model.pkl")
    _models["resp_scaler"]    = _load("respiratory_scaler.pkl")
    logger.info("All models loaded successfully.")
    yield
    _models.clear()
    logger.info("Models unloaded.")


# ─── App factory ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="GeriRisk ML API",
    description="Geriatric risk prediction service (cardiac, fall, respiratory).",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# ALLOWED_ORIGIN can be a comma-separated list, e.g.:
#   ALLOWED_ORIGIN=https://geririsk.vercel.app,https://geririsk-staging.vercel.app
# If not set, all origins are permitted (useful during development / Render preview).

_raw_origins = os.environ.get("ALLOWED_ORIGIN", "*")
ALLOWED_ORIGINS: list[str] = (
    ["*"] if _raw_origins.strip() == "*"
    else [o.strip() for o in _raw_origins.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,   # must be False when allow_origins=["*"]
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

logger.info("CORS configured for origins: %s", ALLOWED_ORIGINS)

# ─── Schemas ──────────────────────────────────────────────────────────────────


class PredictRequest(BaseModel):
    """Aggregated wearable metrics sent by the Next.js /api/upload route."""

    avgHeartRate: Optional[float] = Field(default=72,  description="Average heart rate (bpm)")
    maxHeartRate: Optional[float] = Field(default=100, description="Maximum heart rate (bpm)")
    minHeartRate: Optional[float] = Field(default=55,  description="Minimum heart rate (bpm)")
    minSpO2:      Optional[float] = Field(default=95,  description="Minimum blood-oxygen saturation (%)")
    totalSteps:   Optional[float] = Field(default=0,   description="Total step count")
    recordCount:  Optional[float] = Field(default=1,   description="Number of CSV records processed")


class RiskScore(BaseModel):
    score: float = Field(description="Probability score in [0, 1]")
    level: str   = Field(description="Risk level: High | Moderate | Low")


class PredictionResponse(BaseModel):
    cardiacRisk:     RiskScore
    fallRisk:        RiskScore
    respiratoryRisk: RiskScore


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _risk_level(score: float) -> str:
    """Map a probability score to a human-readable risk tier."""
    if score >= 0.75:
        return "High"
    if score >= 0.40:
        return "Moderate"
    return "Low"


def _safe_float(value: Optional[float], default: float) -> float:
    """
    Return a clean float, falling back to *default* for None / NaN / non-numeric.
    Mirrors the safe_get() logic in the original predict.py.
    """
    if value is None:
        return float(default)
    try:
        v = float(value)
        return float(default) if np.isnan(v) else v
    except (ValueError, TypeError):
        return float(default)


# ─── Routes ───────────────────────────────────────────────────────────────────


@app.get("/health", tags=["ops"])
def health_check():
    """
    Liveness probe used by Render and docker-compose healthchecks.
    Also verifies that models have been loaded.
    """
    if not _models:
        raise HTTPException(status_code=503, detail="Models not loaded yet.")
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse, tags=["inference"])
def predict(request: PredictRequest):
    """
    Run all three risk models against the supplied wearable aggregates.

    Feature vectors mirror the original predict.py exactly:
      - Cardiac:     [avgHR, maxHR, minHR, minSpO2, totalSteps, recordCount]
      - Fall:        [avgHR, totalSteps, recordCount]
      - Respiratory: [minSpO2, avgHR, recordCount]
    """
    if not _models:
        raise HTTPException(status_code=503, detail="Models are not loaded.")

    # Sanitise inputs — same defaults as the original predict.py
    avg_hr      = _safe_float(request.avgHeartRate, 72)
    max_hr      = _safe_float(request.maxHeartRate, 100)
    min_hr      = _safe_float(request.minHeartRate, 55)
    min_spo2    = _safe_float(request.minSpO2,      95)
    total_steps = _safe_float(request.totalSteps,   0)
    record_cnt  = _safe_float(request.recordCount,  1)

    try:
        # ── Cardiac ──────────────────────────────────────────────────────────
        cardiac_X = np.array([[avg_hr, max_hr, min_hr, min_spo2, total_steps, record_cnt]])
        cardiac_prob: float = _models["cardiac_model"].predict_proba(
            _models["cardiac_scaler"].transform(cardiac_X)
        )[0][1]

        # ── Fall ─────────────────────────────────────────────────────────────
        fall_X = np.array([[avg_hr, total_steps, record_cnt]])
        fall_prob: float = _models["fall_model"].predict_proba(
            _models["fall_scaler"].transform(fall_X)
        )[0][1]

        # ── Respiratory ──────────────────────────────────────────────────────
        resp_X = np.array([[min_spo2, avg_hr, record_cnt]])
        resp_prob: float = _models["resp_model"].predict_proba(
            _models["resp_scaler"].transform(resp_X)
        )[0][1]

    except Exception as exc:
        logger.exception("Inference error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc

    logger.info(
        "Prediction — cardiac=%.3f (%s) | fall=%.3f (%s) | resp=%.3f (%s)",
        cardiac_prob, _risk_level(cardiac_prob),
        fall_prob,    _risk_level(fall_prob),
        resp_prob,    _risk_level(resp_prob),
    )

    return PredictionResponse(
        cardiacRisk=RiskScore(
            score=round(float(cardiac_prob), 3),
            level=_risk_level(cardiac_prob),
        ),
        fallRisk=RiskScore(
            score=round(float(fall_prob), 3),
            level=_risk_level(fall_prob),
        ),
        respiratoryRisk=RiskScore(
            score=round(float(resp_prob), 3),
            level=_risk_level(resp_prob),
        ),
    )
