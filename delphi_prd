# delphi/BUILD_PLAN.md — Prediction-Market Intern & Orchestrator (demo cut)

Two applause moments: (A) **partition-sum arb alert with fee-aware math + receipts**,
(B) **bot-doctor detects a broken scraper and self-repairs it**. Order guarantees
both exist even if the run dies early.

## Data model (SQLite: delphi/data/delphi.db)
- `markets(id, venue[polymarket|kalshi], slug, question, outcomes_json,
  prices_json, liquidity_usd, resolution_date, resolution_criteria, fetched_at)`
- `alerts(id, kind[partition|crossvenue|stale], market_ids_json, edge_pct,
  edge_after_fees_pct, size_usd, annualized_pct, receipts_json, ts)`
- `ledger(alert_id, still_executable_60s, hypothetical_pnl_usd, resolved, notes)`
- `bots(name, target, cadence_s, last_heartbeat, status[ok|drift|repaired], schema_hash)`

## Tasks (in order — commit after each)

### Task 1: Cached market snapshots
`scripts/fetch_polymarket.py` + `scripts/fetch_kalshi.py` hit the PUBLIC APIs
(Polymarket Gamma https://gamma-api.polymarket.com/markets ; Kalshi public REST)
and cache raw JSON to `delphi/data/snapshots/`. Run once IF network available;
otherwise generate `delphi/data/snapshots/fixture_*.json` — 15 realistic markets
including: (a) one multi-outcome market whose prices sum to ~1.04, (b) one pair of
near-equivalent cross-venue markets with a criteria difference, (c) one clean
efficient market. Fixtures must be clearly labeled as fixtures in filenames.
Loader → SQLite. Demo ALWAYS reads from cache/fixtures, never network.

### Task 2: Partition-sum arb detector  ← APPLAUSE MOMENT A
`delphi/arb_partition.py` — for mutually-exclusive-exhaustive outcome sets:
raw_edge = |Σp − 1|. Then compute edge_after_fees for a target size S:
apply venue fee model (Polymarket ~2% on winnings; parameterized) + slippage
estimated from liquidity (simple model: slippage_pct = k·S/liquidity, document k).
Alert fires ONLY if edge_after_fees > threshold. Alert payload includes: the exact
arithmetic shown step-by-step, size, capital, days-to-resolution, annualized %,
timestamped price receipt. Unit test: fixture (a) fires with correct math;
fixture (c) does not fire.

### Task 3: Cross-venue detector with criteria diff
`delphi/arb_crossvenue.py` — match candidate pairs (fixture (b)), compute spread
after both venues' fees, and MANDATORY: print the resolution-criteria diff verbatim
with a warning line: "criteria are NOT identical — verify before trading."
Never emit a cross-venue alert without the diff block.

### Task 4: Bot registry + bot-doctor  ← APPLAUSE MOMENT B
`delphi/bots.py` — registry table + two toy scrapers in `delphi/bots_fleet/`:
each parses a local HTML fixture (simulating a venue page) into the market schema.
Include `data/fixtures/page_v1.html` and `page_v2.html` where v2 has changed
markup (renamed CSS classes). Bot-doctor flow:
1. heartbeat run detects parse failure / schema drift on v2,
2. marks bot status=drift,
3. "repair": regenerates the parser mapping from the new markup (rule-based
   re-derivation is fine — find the same fields by content heuristics), shows a
   diff of old vs new selectors,
4. re-runs green, status=repaired.
Demo prints this whole sequence. Unit test: v2 fixture triggers drift and repair
produces correct fields.

### Task 5: Intern brief (lightweight)
`delphi/brief.py` — for one "newly listed" fixture market, print a structured
brief: question summary, resolution criteria with gotchas flagged (regex/heuristic
flags: "unless", "official source", date ambiguity), current odds, liquidity,
one-paragraph efficient-vs-mispriced note. Template + heuristics; no LLM call
needed in demo (note in README that production routes this to a frontier model).

### Task 6: Paper-PnL ledger
`delphi/ledger.py` — seed 12 historical alerts with outcomes; print the honesty
table: precision %, avg edge, hypothetical PnL. One line in demo: "alert precision
is measured, not claimed."

### Task 7: Demo script
`demo/demo_delphi.py` — sequence: scan snapshots → fire partition alert (full
math) → fire cross-venue alert (criteria diff + warning) → bot-doctor sequence on
the v2 fixture → ledger table → closing line. Deterministic, <60s, rich-formatted.

### Task 8: Hermes mapping
`hermes/delphi/` — skill manifests (scanner, arb-*, bot-doctor, brief), cron
configs per cadence. Same real-or-mapping-doc rule as Maitre.

## Compliance note for README
Include verbatim: "Decision-support software. No execution. Polymarket/Kalshi
geo-restrict access; nothing here is trading advice."
