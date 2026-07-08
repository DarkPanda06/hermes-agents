"""Manual fetch script — hits the PUBLIC Polymarket Gamma API and caches raw JSON
into delphi/data/snapshots/snapshot_polymarket.json.

RUN MANUALLY, never inside `make demo-*` (the demo is offline-only). If the
network is unavailable, the demo falls back to the hand-authored
fixture_polymarket.json already committed alongside this cache.

Usage:  python -m delphi.scripts.fetch_polymarket [--limit 40]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

GAMMA_URL = "https://gamma-api.polymarket.com/markets"
OUT = Path(__file__).resolve().parents[1] / "data" / "snapshots" / "snapshot_polymarket.json"


def _normalize(raw: dict) -> dict:
    """Best-effort map of a Gamma market record into the Delphi schema."""
    outcomes = raw.get("outcomes")
    prices = raw.get("outcomePrices")
    if isinstance(outcomes, str):
        outcomes = json.loads(outcomes)
    if isinstance(prices, str):
        prices = json.loads(prices)
    return {
        "id": f"pm_{raw.get('id')}",
        "slug": raw.get("slug"),
        "question": raw.get("question"),
        "outcomes": outcomes or [],
        "prices": [float(p) for p in (prices or [])],
        "liquidity_usd": float(raw.get("liquidityNum") or raw.get("liquidity") or 0),
        "resolution_date": (raw.get("endDate") or "")[:10],
        "resolution_criteria": raw.get("description") or "",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args()

    import requests  # imported lazily so the demo never needs it

    resp = requests.get(GAMMA_URL, params={"limit": args.limit, "active": "true", "closed": "false"}, timeout=30)
    resp.raise_for_status()
    markets = [_normalize(m) for m in resp.json()]

    payload = {
        "_note": "LIVE snapshot cached from Polymarket Gamma API. Offline demo prefers fixture_polymarket.json.",
        "venue": "polymarket",
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "markets": markets,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Cached {len(markets)} Polymarket markets -> {OUT}")


if __name__ == "__main__":
    main()
