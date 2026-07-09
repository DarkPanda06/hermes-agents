"""SQLite helpers for Delphi. Self-contained (does NOT use core/).

The schema mirrors delphi/BUILD_PLAN.md exactly:
  markets, alerts, ledger, bots
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DATA_DIR / "delphi.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS markets (
    id                  TEXT PRIMARY KEY,
    venue               TEXT NOT NULL,      -- polymarket | kalshi
    slug                TEXT,
    question            TEXT NOT NULL,
    outcomes_json       TEXT NOT NULL,      -- JSON list[str]
    prices_json         TEXT NOT NULL,      -- JSON list[float], index-aligned with outcomes
    liquidity_usd       REAL,
    resolution_date     TEXT,               -- ISO date
    resolution_criteria TEXT,
    fetched_at          TEXT,               -- ISO timestamp (from snapshot)
    is_fixture          INTEGER DEFAULT 1,  -- 1 = seeded fixture, 0 = live snapshot
    newly_listed        INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alerts (
    id                  TEXT PRIMARY KEY,
    kind                TEXT NOT NULL,      -- partition | crossvenue | stale
    market_ids_json     TEXT NOT NULL,
    edge_pct            REAL,               -- raw edge %
    edge_after_fees_pct REAL,
    size_usd            REAL,
    annualized_pct      REAL,
    receipts_json       TEXT,
    ts                  TEXT
);

CREATE TABLE IF NOT EXISTS ledger (
    alert_id                TEXT,
    still_executable_60s    INTEGER,
    hypothetical_pnl_usd    REAL,
    resolved                INTEGER,
    notes                   TEXT
);

CREATE TABLE IF NOT EXISTS bots (
    name            TEXT PRIMARY KEY,
    target          TEXT,
    cadence_s       INTEGER,
    last_heartbeat  TEXT,
    status          TEXT,                   -- ok | drift | repaired
    schema_hash     TEXT
);
"""


def connect(db_path: os.PathLike | str | None = None) -> sqlite3.Connection:
    """Open (creating if needed) the Delphi DB with the full schema applied."""
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def reset(db_path: os.PathLike | str | None = None) -> sqlite3.Connection:
    """Drop and recreate all tables — used by the deterministic demo/loader."""
    conn = connect(db_path)
    for tbl in ("markets", "alerts", "ledger", "bots"):
        conn.execute(f"DROP TABLE IF EXISTS {tbl}")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
