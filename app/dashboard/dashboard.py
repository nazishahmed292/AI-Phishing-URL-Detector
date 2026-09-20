"""
dashboard.py — Streamlit dashboard for the phishing detector.

Shows:
  - Live manual URL checker (calls the FastAPI /predict endpoint)
  - Aggregate stats (total scanned, phishing rate)
  - Recent detections table
  - Charts: phishing vs legit split, confidence distribution, timeline
  - Model feature-importance chart (from training metrics.json)

Run (with the API already running on port 8000):
    streamlit run app/dashboard/dashboard.py
"""

import os
import sys
import json
import requests
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "api"))
from database import init_db, fetch_all, fetch_stats  # noqa: E402

API_URL = os.environ.get("PHISHING_API_URL", "http://127.0.0.1:8000")
METRICS_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "metrics.json")

st.set_page_config(
    page_title="Phishing Detector Dashboard",
    page_icon="🛡️",
    layout="wide",
)

init_db()

st.title("🛡️ AI Phishing URL Detector — Dashboard")
st.caption("Real-time monitoring for the browser-extension phishing detector.")

# ---------------------------------------------------------------- Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    st.text_input("API URL", value=API_URL, key="api_url", disabled=True)
    st.markdown("---")
    st.markdown(
        "**How it works**\n\n"
        "1. The browser extension sends the active tab's URL here.\n"
        "2. A trained RandomForest model scores lexical & structural "
        "features of the URL.\n"
        "3. Results are logged and shown live below."
    )
    if st.button("🔄 Refresh data"):
        st.rerun()

# ---------------------------------------------------------------- Manual check
st.subheader("🔎 Check a URL manually")
col1, col2 = st.columns([4, 1])
with col1:
    manual_url = st.text_input(
        "Paste a URL to test", placeholder="https://example.com/login",
        label_visibility="collapsed",
    )
with col2:
    check_clicked = st.button("Check URL", use_container_width=True)

if check_clicked and manual_url.strip():
    try:
        resp = requests.post(
            f"{API_URL}/predict",
            json={"url": manual_url.strip(), "source": "dashboard"},
            timeout=5,
        )
        resp.raise_for_status()
        result = resp.json()
        if result["is_phishing"]:
            st.error(
                f"⚠️ **Likely Phishing** — confidence {result['confidence']*100:.1f}% "
                f"({result['risk_level']} risk)"
            )
        else:
            st.success(
                f"✅ **Likely Legitimate** — phishing confidence only "
                f"{result['confidence']*100:.1f}%"
            )
        with st.expander("Why this verdict?"):
            for s in result["top_signals"]:
                st.write(f"- {s}")
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not reach API at {API_URL}. Is it running? ({e})")

st.markdown("---")

# ---------------------------------------------------------------- Stats
stats = fetch_stats()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total URLs Scanned", stats["total"])
c2.metric("Flagged Phishing", stats["phishing"])
c3.metric("Marked Legitimate", stats["legit"])
rate = (stats["phishing"] / stats["total"] * 100) if stats["total"] else 0
c4.metric("Phishing Rate", f"{rate:.1f}%")

# ---------------------------------------------------------------- Recent table + charts
rows = fetch_all(limit=500)
if rows:
    df = pd.DataFrame(
        rows,
        columns=["id", "url", "hostname", "is_phishing", "confidence", "source", "created_at"],
    )
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["verdict"] = df["is_phishing"].map({1: "Phishing", 0: "Legit"})

    left, right = st.columns(2)
    with left:
        st.subheader("Verdict split")
        pie_data = df["verdict"].value_counts().reset_index()
        pie_data.columns = ["verdict", "count"]
        chart = alt.Chart(pie_data).mark_arc().encode(
            theta="count", color=alt.Color("verdict", scale=alt.Scale(
                domain=["Phishing", "Legit"], range=["#e74c3c", "#2ecc71"]
            )),
            tooltip=["verdict", "count"],
        )
        st.altair_chart(chart, use_container_width=True)

    with right:
        st.subheader("Confidence distribution")
        hist = alt.Chart(df).mark_bar().encode(
            x=alt.X("confidence:Q", bin=alt.Bin(maxbins=20), title="Phishing confidence"),
            y=alt.Y("count()", title="Count"),
            color=alt.Color("verdict", scale=alt.Scale(
                domain=["Phishing", "Legit"], range=["#e74c3c", "#2ecc71"]
            )),
        )
        st.altair_chart(hist, use_container_width=True)

    st.subheader("Detections over time")
    timeline = df.copy()
    timeline["minute"] = timeline["created_at"].dt.floor("min")
    ts = timeline.groupby(["minute", "verdict"]).size().reset_index(name="count")
    line = alt.Chart(ts).mark_line(point=True).encode(
        x="minute:T", y="count:Q",
        color=alt.Color("verdict", scale=alt.Scale(
            domain=["Phishing", "Legit"], range=["#e74c3c", "#2ecc71"]
        )),
    )
    st.altair_chart(line, use_container_width=True)

    st.subheader("Recent detections")
    st.dataframe(
        df[["created_at", "url", "hostname", "verdict", "confidence", "source"]]
        .sort_values("created_at", ascending=False)
        .head(100),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No predictions logged yet — check a URL above, or browse with the extension active.")

# ---------------------------------------------------------------- Model insight
st.markdown("---")
st.subheader("🧠 Model feature importance")
if os.path.exists(METRICS_PATH):
    with open(METRICS_PATH) as f:
        metrics = json.load(f)
    fi = pd.DataFrame(
        list(metrics.get("feature_importances", {}).items()),
        columns=["feature", "importance"],
    ).sort_values("importance", ascending=False).head(12)
    bar = alt.Chart(fi).mark_bar().encode(
        x=alt.X("importance:Q"),
        y=alt.Y("feature:N", sort="-x"),
        color=alt.value("#3498db"),
    )
    st.altair_chart(bar, use_container_width=True)
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("Test Accuracy", metrics["accuracy"])
    mcol2.metric("Precision", metrics["precision"])
    mcol3.metric("Recall", metrics["recall"])
    mcol4.metric("F1 Score", metrics["f1_score"])
else:
    st.info("Train the model first: `python app/model/train_model.py`")

st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
