"""
database.py
-----------
Tiny SQLite wrapper for logging every prediction the API makes.
The Streamlit dashboard reads from the same file, so both processes
must point at the same DB_PATH (default: data/logs.db).
"""

import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "logs.db")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            hostname TEXT,
            is_phishing INTEGER NOT NULL,
            confidence REAL NOT NULL,
            source TEXT DEFAULT 'api',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def log_prediction(url: str, hostname: str, is_phishing: int, confidence: float, source: str = "api"):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO predictions (url, hostname, is_phishing, confidence, source, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (url, hostname, is_phishing, confidence, source, datetime.datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def fetch_all(limit: int = 2000):
    conn = get_connection()
    cur = conn.execute(
        "SELECT id, url, hostname, is_phishing, confidence, source, created_at "
        "FROM predictions ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def fetch_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    phishing = conn.execute("SELECT COUNT(*) FROM predictions WHERE is_phishing = 1").fetchone()[0]
    conn.close()
    return {"total": total, "phishing": phishing, "legit": total - phishing}


if __name__ == "__main__":
    init_db()
    print(f"Initialized DB at {DB_PATH}")
