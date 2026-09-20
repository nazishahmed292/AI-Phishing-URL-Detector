"""
main.py — FastAPI backend for the phishing detector.

Endpoints:
  GET  /health            -> liveness check
  POST /predict           -> {"url": "..."} -> phishing verdict + confidence
  GET  /stats             -> aggregate counts for the dashboard
  GET  /recent?limit=50   -> most recent predictions

Run:
    uvicorn app.api.main:app --reload --port 8000
(run from the project root so the "app" package resolves)
"""

import os
import sys
import joblib
import numpy as np
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "model"))
sys.path.append(os.path.dirname(__file__))
from feature_extractor import extract_features, features_to_vector  # noqa: E402
from database import init_db, log_prediction, fetch_all, fetch_stats  # noqa: E402

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "model")
MODEL_PATH = os.path.join(MODEL_DIR, "model.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")

app = FastAPI(
    title="Phishing URL Detector API",
    description="Lightweight ML API that scores a URL for phishing risk.",
    version="1.0.0",
)

# Allow the browser extension (which calls from an extension origin) and
# the Streamlit dashboard (localhost) to reach this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_model = None
_scaler = None


class PredictRequest(BaseModel):
    url: str = Field(..., description="The full URL to classify")
    source: str = Field("api", description="Caller tag, e.g. 'extension' or 'dashboard'")


class PredictResponse(BaseModel):
    url: str
    is_phishing: bool
    confidence: float
    risk_level: str
    top_signals: list


@app.on_event("startup")
def load_model():
    global _model, _scaler
    init_db()
    if not (os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH)):
        raise RuntimeError(
            "Model files not found. Run `python app/model/train_model.py` first."
        )
    _model = joblib.load(MODEL_PATH)
    _scaler = joblib.load(SCALER_PATH)


def _risk_level(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.6:
        return "medium"
    return "low"


def _top_signals(feats: dict, n=3):
    """Return a short, human-readable list of why a URL looked risky."""
    signals = []
    if feats["has_ip_host"]:
        signals.append("Uses a raw IP address as the domain")
    if feats["suspicious_word_count"] >= 2:
        signals.append("Contains multiple suspicious keywords (login/verify/secure...)")
    if feats["has_shortener"]:
        signals.append("Uses a URL shortener")
    if feats["num_subdomains"] >= 2:
        signals.append("Unusually many subdomains")
    if not feats["is_https"]:
        signals.append("Not served over HTTPS")
    if feats["has_hyphen_in_domain"]:
        signals.append("Hyphenated domain name (common brand-impersonation trick)")
    if feats["hostname_entropy"] > 4.0:
        signals.append("High-entropy / randomized-looking domain name")
    return signals[:n] if signals else ["No strong individual red flags — score is pattern-based"]


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if _model is None or _scaler is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Empty URL")

    feats = extract_features(url)
    vector = np.array([features_to_vector(feats)], dtype=float)
    vector_scaled = _scaler.transform(vector)

    proba = _model.predict_proba(vector_scaled)[0]
    phishing_confidence = float(proba[1])
    is_phishing = phishing_confidence >= 0.5

    hostname = urlparse(url if "://" in url else "http://" + url).hostname or ""
    log_prediction(
        url=url,
        hostname=hostname,
        is_phishing=int(is_phishing),
        confidence=phishing_confidence,
        source=req.source,
    )

    return PredictResponse(
        url=url,
        is_phishing=is_phishing,
        confidence=round(phishing_confidence, 4),
        risk_level=_risk_level(phishing_confidence),
        top_signals=_top_signals(feats),
    )


@app.get("/stats")
def stats():
    return fetch_stats()


@app.get("/recent")
def recent(limit: int = 50):
    rows = fetch_all(limit=limit)
    return [
        {
            "id": r[0], "url": r[1], "hostname": r[2],
            "is_phishing": bool(r[3]), "confidence": r[4],
            "source": r[5], "created_at": r[6],
        }
        for r in rows
    ]
