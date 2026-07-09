"""Load cached market snapshots/fixtures from delphi/data/snapshots/ into SQLite.

The demo ALWAYS reads from here — never the network. Files named ``fixture_*.json``
are seeded/hand-authored; files named ``snapshot_*.json`` are cached live pulls
produced by scripts/fetch_*.py. Both share one shape and are loaded identically.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import db

SNAPSHOT_DIR = Path(__file__).resolve().parent / "data" / "snapshots"


def _iter_market_files(snapshot_dir: Path):
    # Deterministic order: fixtures first, then snapshots, alpha within each.
    files = sorted(snapshot_dir.glob("*.json"), key=lambda p: (not p.name.startswith("fixture_"), p.name))
    for f in files:
        yield f


def load_snapshots(conn=None, snapshot_dir: Path | None = None) -> int:
    """Load every JSON snapshot file into the ``markets`` table. Returns count."""
    close = False
    if conn is None:
        conn = db.reset()
        close = True
    snapshot_dir = snapshot_dir or SNAPSHOT_DIR

    n = 0
    for path in _iter_market_files(snapshot_dir):
        payload = json.loads(path.read_text(encoding="utf-8"))
        venue = payload.get("venue")
        fetched_at = payload.get("fetched_at")
        is_fixture = 1 if path.name.startswith("fixture_") else 0
        for m in payload.get("markets", []):
            conn.execute(
                """
                INSERT OR REPLACE INTO markets
                  (id, venue, slug, question, outcomes_json, prices_json,
                   liquidity_usd, resolution_date, resolution_criteria,
                   fetched_at, is_fixture, newly_listed)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    m["id"],
                    m.get("venue", venue),
                    m.get("slug"),
                    m["question"],
                    json.dumps(m["outcomes"]),
                    json.dumps(m["prices"]),
                    m.get("liquidity_usd"),
                    m.get("resolution_date"),
                    m.get("resolution_criteria"),
                    m.get("fetched_at", fetched_at),
                    is_fixture,
                    1 if m.get("newly_listed") else 0,
                ),
            )
            n += 1
    conn.commit()
    if close:
        conn.close()
    return n


def load_markets(conn) -> list[dict]:
    """Return all markets as decoded dicts (outcomes/prices as Python lists)."""
    rows = conn.execute("SELECT * FROM markets ORDER BY venue, id").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["outcomes"] = json.loads(d.pop("outcomes_json"))
        d["prices"] = json.loads(d.pop("prices_json"))
        out.append(d)
    return out


if __name__ == "__main__":
    conn = db.reset()
    count = load_snapshots(conn)
    fixtures = conn.execute("SELECT COUNT(*) FROM markets WHERE is_fixture=1").fetchone()[0]
    print(f"Loaded {count} markets into {db.DB_PATH} ({fixtures} from fixtures).")
    conn.close()
