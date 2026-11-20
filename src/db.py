"""SQLite storage for daily price observations.

Every price is stored in one long table, one row per (date, series).
Keeping the raw observations (no forward-filling) is deliberate: it lets
the analysis step see exactly which days each market actually printed.
"""

import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "prices.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    date    TEXT NOT NULL,   -- ISO date, YYYY-MM-DD
    series  TEXT NOT NULL,   -- e.g. 'brent_spot', 'wti_fut'
    price   REAL NOT NULL,   -- USD per barrel
    source  TEXT NOT NULL,   -- where the number came from
    PRIMARY KEY (date, series)
);
"""


def connect(path=DB_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    return conn


def save_prices(conn, df):
    """Insert or replace rows. df needs columns: date, series, price, source."""
    rows = df[["date", "series", "price", "source"]].itertuples(index=False)
    conn.executemany(
        "INSERT OR REPLACE INTO prices (date, series, price, source) VALUES (?, ?, ?, ?)",
        [(str(d)[:10], s, float(p), src) for d, s, p, src in rows],
    )
    conn.commit()


def load_prices(conn):
    """Return the raw observations as a long DataFrame, oldest first."""
    df = pd.read_sql_query(
        "SELECT date, series, price FROM prices ORDER BY date, series", conn
    )
    df["date"] = pd.to_datetime(df["date"])
    return df
