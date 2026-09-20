# 🛡️ AI Phishing URL Detector — Browser Extension + ML API + Streamlit Dashboard

A mini but production-shaped project: a Chrome extension that scores every
page you visit for phishing risk in real time, backed by a scikit-learn
model served through FastAPI, with a Streamlit dashboard for monitoring
and analytics.

**Why it's a bit different from the usual "phishing URL classifier" demo:**
- It's a full loop, not just a notebook: **extension → live API → model →
  logging → dashboard**, all wired together.
- Detection is **explainable** — every verdict returns the top 2–3 reasons
  ("uses an IP address as host", "hyphenated brand-lookalike domain", etc.),
  not just a bare score.
- **Zero paid APIs, zero external services** required to run end-to-end —
  everything (including training data) is generated locally, so anyone can
  clone and run it immediately, then swap in real PhishTank/OpenPhish data
  for production use.

---

## Architecture

```
 ┌─────────────────────┐        POST /predict         ┌──────────────────────┐
 │  Chrome Extension    │ ───────────────────────────▶ │   FastAPI Backend    │
 │  (background.js +    │ ◀─────────────────────────── │   (app/api/main.py)  │
 │   content.js banner) │      verdict + reasons        │  loads model.pkl     │
 └─────────────────────┘                               └──────────┬───────────┘
                                                                    │ logs every
                                                                    │ prediction
                                                          ┌─────────▼──────────┐
                                                          │   SQLite (logs.db) │
                                                          └─────────┬──────────┘
                                                                    │ reads
                                                          ┌─────────▼──────────┐
                                                          │ Streamlit Dashboard│
                                                          │ (live charts,      │
                                                          │  manual URL check) │
                                                          └────────────────────┘
```

Model layer:
```
URL  →  feature_extractor.py (23 lexical/structural features)
     →  StandardScaler
     →  RandomForestClassifier (300 trees)
     →  phishing probability + human-readable "top signals"
```

---

## Project structure

```
phishing-detector/
├── app/
│   ├── model/
│   │   ├── feature_extractor.py   # URL → feature vector (shared by train + serve)
│   │   ├── dataset_generator.py   # synthetic labeled dataset (swap for real data)
│   │   ├── train_model.py         # trains RandomForest, saves model.pkl/scaler.pkl
│   │   ├── model.pkl              # (generated)
│   │   ├── scaler.pkl             # (generated)
│   │   └── metrics.json           # (generated) accuracy/precision/recall/f1
│   ├── api/
│   │   ├── main.py                # FastAPI app: /predict /health /stats /recent
│   │   └── database.py            # SQLite logging used by API + dashboard
│   └── dashboard/
│       └── dashboard.py           # Streamlit monitoring dashboard
├── extension/
│   ├── manifest.json              # Chrome MV3 manifest
│   ├── background.js              # watches tab navigation, calls API
│   ├── content.js                 # injects in-page warning banner
│   ├── popup.html / popup.js      # toolbar popup UI
│   └── icons/
├── data/                          # generated dataset + logs.db (gitignored)
├── requirements.txt
└── .gitignore
```

---

## 1. Local setup

```bash
git clone https://github.com/<your-username>/phishing-detector.git
cd phishing-detector

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## 2. Train the model

```bash
python app/model/train_model.py
```

This generates a synthetic dataset (`data/urls_dataset.csv`, 3,000 labeled
URLs), trains a RandomForest classifier, and saves `model.pkl`,
`scaler.pkl`, and `metrics.json` under `app/model/`. Typical result on the
synthetic set: ~99–100% accuracy (the synthetic classes are cleanly
separable — see **"Using real data"** below to harden this for production).

## 3. Run the API

```bash
uvicorn app.api.main:app --reload --port 8000
```

Test it:
```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"url": "http://paypal-secure-login.tk/verify?token=99213"}'
```

Interactive docs: http://127.0.0.1:8000/docs

## 4. Run the dashboard

In a second terminal (venv still active):
```bash
streamlit run app/dashboard/dashboard.py
```
Open http://localhost:8501 — paste URLs to test manually, or leave it
running while browsing with the extension active to watch live detections
stream in.

## 5. Load the browser extension

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** → select the `extension/` folder
4. Make sure the FastAPI server (step 3) is running on `http://127.0.0.1:8000`
5. Browse normally — the toolbar icon badges ✓ (safe) or ! (risky) per tab,
   and a red banner appears automatically on high-confidence phishing pages

To point the extension at a **deployed** API instead of localhost, open the
extension's service worker console and run:
```js
chrome.storage.local.set({ apiBaseUrl: "https://your-deployed-api.com" })
```

---

## Using real phishing data (recommended before relying on this for real use)

`dataset_generator.py` produces synthetic-but-realistic URLs so the whole
project trains and runs with zero setup. For a stronger, resume-credible
model, replace it with a real feed:

- **PhishTank** (verified phishing URLs, free API key): https://phishtank.org/developer_info.php
- **UCI Phishing Websites Dataset**: https://archive.ics.uci.edu/dataset/327
- **OpenPhish** feed: https://openphish.com/

Just write a loader that yields `(url, label)` pairs matching the CSV
format used by `train_model.py` (columns: `url,label`) — the feature
extraction and model code need no changes.

---

## Deploying

**API (FastAPI)** — any of these work well for a free/low-cost deploy:
- **Render**: New → Web Service → connect your GitHub repo → build command
  `pip install -r requirements.txt` → start command
  `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
- **Railway**: same start command, auto-detects Python
- Make sure `app/model/model.pkl` and `scaler.pkl` are committed (or trained
  via a build step) so the deployed API has a model to load

**Dashboard (Streamlit)**:
- **Streamlit Community Cloud** (free): https://streamlit.io/cloud → point
  it at your repo, entry file `app/dashboard/dashboard.py`
- Set the `PHISHING_API_URL` environment variable in the app's secrets to
  your deployed API's URL

**Extension**: for real distribution, zip the `extension/` folder and
submit it to the Chrome Web Store developer dashboard
(https://chrome.google.com/webstore/devconsole) — for a portfolio/demo
project, "Load unpacked" is enough.

---

## Publishing to GitHub

```bash
cd phishing-detector
git init
git add .
git commit -m "Initial commit: AI phishing detector (API + dashboard + extension)"
git branch -M main
git remote add origin https://github.com/<your-username>/phishing-detector.git
git push -u origin main
```

`.gitignore` already excludes generated artifacts (`data/logs.db`,
`data/urls_dataset.csv`, `model.pkl`, `scaler.pkl`, `metrics.json`) so the
repo stays clean — anyone cloning it just runs `train_model.py` once to
regenerate everything locally. If you'd rather ship a pretrained model,
remove those lines from `.gitignore` and commit the `.pkl` files directly.

---

## API reference

| Endpoint         | Method | Body                              | Returns |
|------------------|--------|------------------------------------|---------|
| `/health`        | GET    | —                                   | `{"status": "ok", "model_loaded": true}` |
| `/predict`       | POST   | `{"url": "...", "source": "..."}`   | verdict, confidence, risk_level, top_signals |
| `/stats`         | GET    | —                                   | total / phishing / legit counts |
| `/recent?limit=` | GET    | —                                   | most recent logged predictions |

---

## Ideas for extending this further

- Add a browser-history-based bulk scanner
- Swap RandomForest for a gradient-boosted model (XGBoost/LightGBM) and compare
- Add WHOIS-based domain-age features (requires network access + rate limiting)
- Add a Firefox build (`browser_specific_settings` in manifest)
- Add user feedback ("this was wrong") that retrains the model periodically
