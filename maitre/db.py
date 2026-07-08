"""SQLite helpers for Maitre. Self-contained (does NOT use core/).

The schema mirrors maitre/BUILD_PLAN.md exactly:
  events, taste_profile, outings, decisions
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DATA_DIR / "maitre.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id             TEXT PRIMARY KEY,
    title          TEXT NOT NULL,
    venue          TEXT,
    area           TEXT,
    dt             TEXT,               -- ISO datetime of the event
    price_min      REAL,
    price_max      REAL,
    genre_tags     TEXT NOT NULL,      -- JSON list[str]
    vibe_tags      TEXT NOT NULL,      -- JSON list[str]
    capacity_class TEXT,               -- intimate | mid | massive
    source         TEXT,               -- listings | instagram | whatsapp | seed
    url            TEXT,
    is_past        INTEGER DEFAULT 0   -- 1 = historical (feeds outings, not the scan)
);

CREATE TABLE IF NOT EXISTS taste_profile (
    key   TEXT PRIMARY KEY,
    value TEXT                          -- scalar as text, or JSON for structured values
);

CREATE TABLE IF NOT EXISTS outings (
    id           TEXT PRIMARY KEY,
    event_id     TEXT NOT NULL,
    rating       INTEGER,               -- 1..5
    vibe_match   REAL,                  -- 0..1, how the room actually felt
    would_repeat INTEGER,               -- 0 | 1
    notes        TEXT,
    ts           TEXT                   -- ISO datetime the outing happened
);

CREATE TABLE IF NOT EXISTS decisions (
    id          TEXT PRIMARY KEY,
    event_id    TEXT NOT NULL,
    fit_score   REAL,
    verdict     TEXT,                   -- surface | reject
    reasons_json TEXT,                  -- JSON: components + human reason strings
    ts          TEXT
);
"""

TABLES = ("events", "taste_profile", "outings", "decisions")


def connect(db_path: os.PathLike | str | None = None) -> sqlite3.Connection:
    """Open (creating if needed) the Maitre DB with the full schema applied."""
    path = Path(db_path) if db_path else DB_PATH
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def reset(db_path: os.PathLike | str | None = None) -> sqlite3.Connection:
    """Drop and recreate all tables — used by the deterministic demo/loader."""
    conn = connect(db_path)
    for tbl in TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {tbl}")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


# --- taste_profile access -------------------------------------------------
# Values are stored as text. Structured values (dicts/lists) are JSON-encoded
# on write and decoded on read so callers work with native Python objects.

def get_profile(conn) -> dict:
    """Return the whole taste profile as a dict, JSON-decoding structured values."""
    rows = conn.execute("SELECT key, value FROM taste_profile").fetchall()
    out = {}
    for r in rows:
        out[r["key"]] = _maybe_json(r["value"])
    return out


def set_profile_value(conn, key: str, value) -> None:
    """Upsert one profile value, JSON-encoding dicts/lists."""
    stored = value if isinstance(value, str) else json.dumps(value)
    conn.execute(
        "INSERT OR REPLACE INTO taste_profile (key, value) VALUES (?, ?)",
        (key, stored),
    )
    conn.commit()


def _maybe_json(value):
    if not isinstance(value, str):
        return value
    s = value.strip()
    if s and s[0] in "[{":
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return value
    # numeric scalars stored as text -> keep as float where it round-trips cleanly
    try:
        f = float(s)
        return int(f) if f.is_integer() and "." not in s and "e" not in s.lower() else f
    except (TypeError, ValueError):
        return value
