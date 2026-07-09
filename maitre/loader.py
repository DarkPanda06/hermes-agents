"""Load the seeded taste graph from maitre/data/seed_events.json into SQLite.

The demo ALWAYS reads from here — never the network. The seed file carries four
blocks: ``events`` (future, scanned), ``past_events`` (historical, feed outings),
``taste_profile`` (the compounding graph), and ``outings`` (rated history).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import db

SEED_PATH = Path(__file__).resolve().parent / "data" / "seed_events.json"


def _insert_event(conn, e: dict, is_past: int) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO events
          (id, title, venue, area, dt, price_min, price_max,
           genre_tags, vibe_tags, capacity_class, source, url, is_past)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            e["id"], e["title"], e.get("venue"), e.get("area"), e.get("dt"),
            e.get("price_min"), e.get("price_max"),
            json.dumps(e.get("genre_tags", [])),
            json.dumps(e.get("vibe_tags", [])),
            e.get("capacity_class"), e.get("source", "seed"), e.get("url"),
            is_past,
        ),
    )


def load_seed(conn=None, seed_path: Path | None = None) -> dict:
    """Load the seed file into events/taste_profile/outings. Returns a count summary."""
    close = False
    if conn is None:
        conn = db.reset()
        close = True
    seed_path = seed_path or SEED_PATH
    payload = json.loads(seed_path.read_text(encoding="utf-8"))

    for e in payload.get("events", []):
        _insert_event(conn, e, is_past=0)
    for e in payload.get("past_events", []):
        _insert_event(conn, e, is_past=1)

    for key, value in payload.get("taste_profile", {}).items():
        db.set_profile_value(conn, key, value)

    for o in payload.get("outings", []):
        conn.execute(
            """
            INSERT OR REPLACE INTO outings
              (id, event_id, rating, vibe_match, would_repeat, notes, ts)
            VALUES (?,?,?,?,?,?,?)
            """,
            (o["id"], o["event_id"], o.get("rating"), o.get("vibe_match"),
             1 if o.get("would_repeat") else 0, o.get("notes"), o.get("ts")),
        )
    conn.commit()

    summary = {
        "events": len(payload.get("events", [])),
        "past_events": len(payload.get("past_events", [])),
        "outings": len(payload.get("outings", [])),
        "profile_keys": len(payload.get("taste_profile", {})),
    }
    if close:
        conn.close()
    return summary


def load_events(conn, *, upcoming_only: bool = False) -> list[dict]:
    """Return events as decoded dicts (genre/vibe tags as Python lists).

    ``upcoming_only`` filters to the future scan set (is_past = 0).
    """
    q = "SELECT * FROM events"
    if upcoming_only:
        q += " WHERE is_past = 0"
    q += " ORDER BY dt, id"
    out = []
    for r in conn.execute(q).fetchall():
        d = dict(r)
        d["genre_tags"] = json.loads(d["genre_tags"])
        d["vibe_tags"] = json.loads(d["vibe_tags"])
        out.append(d)
    return out


def load_outings(conn) -> list[dict]:
    """Return outings joined to their event (title/tags/capacity) for the explainer."""
    rows = conn.execute(
        """
        SELECT o.*, e.title AS event_title, e.venue AS event_venue,
               e.genre_tags AS event_genre_tags, e.vibe_tags AS event_vibe_tags,
               e.capacity_class AS event_capacity_class, e.price_min AS event_price_min
        FROM outings o
        JOIN events e ON e.id = o.event_id
        ORDER BY o.ts
        """
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["event_genre_tags"] = json.loads(d["event_genre_tags"] or "[]")
        d["event_vibe_tags"] = json.loads(d["event_vibe_tags"] or "[]")
        out.append(d)
    return out


if __name__ == "__main__":
    conn = db.reset()
    summary = load_seed(conn)
    print(
        f"Loaded {summary['events']} upcoming + {summary['past_events']} past events, "
        f"{summary['outings']} outings, {summary['profile_keys']} profile keys "
        f"into {db.DB_PATH}."
    )
    conn.close()
