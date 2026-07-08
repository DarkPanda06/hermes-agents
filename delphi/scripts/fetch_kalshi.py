"""Manual fetch script — hits the PUBLIC Kalshi REST API and caches raw JSON into
delphi/data/snapshots/snapshot_kalshi.json.

RUN MANUALLY, never inside `make demo-*` (the demo is offline-only). If the
network is unavailable, the demo falls back to the hand-authored
fixture_kalshi.json already committed alongside this cache.

Usage:  python -m delphi.scripts.fetch_kalshi [--limit 40]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

KALSHI_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"
OUT = Path(__file__).resolve().parents[1] / "data" / "snapshots" / "snapshot_kalshi.json"


def _normalize(raw: dict) -> dict:
    """Best-effort map of a Kalshi market record into the Delphi schema.

    Kalshi quotes YES/NO in cents; convert to 0-1 probabilities.
    """
    yes = float(raw.get("yes_ask") or raw.get("last_price") or 0) / 100.0
    return {
        "id": f"k_{raw.get('ticker')}",
        "slug": raw.get("ticker"),
        "question": raw.get("title"),
        "outcomes": ["Yes", "No"],
        "prices": [round(yes, 4), round(1 - yes, 4)],
        "liquidity_usd": float(raw.get("liquidity") or 0) / 100.0,
        "resolution_date": (raw.get("close_time") or "")[:10],
        "resolution_criteria": raw.get("rules_primary") or "",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args()

    import requests  # imported lazily so the demo never needs it

    resp = requests.get(KALSHI_URL, params={"limit": args.limit, "status": "open"}, timeout=30)
    resp.raise_for_status()
    markets = [_normalize(m) for m in resp.json().get("markets", [])]

    payload = {
        "_note": "LIVE snapshot cached from Kalshi public REST API. Offline demo prefers fixture_kalshi.json.",
        "venue": "kalshi",
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "markets": markets,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Cached {len(markets)} Kalshi markets -> {OUT}")


if __name__ == "__main__":
    main()
