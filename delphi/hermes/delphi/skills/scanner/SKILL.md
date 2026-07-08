---
name: scanner
description: Load cached Polymarket/Kalshi market snapshots into working memory. Offline-safe; reads seeded fixtures, never the network during a demo run.
metadata:
  cadence: "*/5 * * * *"
  entrypoint: "delphi.loader:load_snapshots"
  venues: [polymarket, kalshi]
---

# scanner

Reads market snapshots from `delphi/data/snapshots/` (fixtures or cached live
pulls) into the `markets` table — the working memory every downstream skill uses.

## When to run
Every 5 minutes, and once at agent start. Feeds `arb-partition`, `arb-crossvenue`,
and `brief`.

## Inputs
- Snapshot JSON files in `data/snapshots/` (`fixture_*.json` seeded; `snapshot_*.json` cached).

## Outputs
- `markets` rows (id, venue, outcomes, prices, liquidity, resolution criteria, fetched_at).

## Reasoning contract
Prints how many markets loaded and how many are fixtures vs. live — never fakes
data silently.
