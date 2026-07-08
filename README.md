# Delphi — prediction-market intern & orchestrator

> Hermes Agent (Nous Research) demo agent. Deterministic, offline, zero API keys.
> This is the **`delphi` branch**; the Maître agent lives on the `maitre` branch.

Delphi watches Polymarket & Kalshi, finds arbitrage that **survives real fees**,
reads the fine print you won't, keeps its own scrapers alive, and grades itself
honestly. Every decision prints its reasoning — the "why / why not" *is* the product.

## Two applause moments

1. **Partition-sum arb with fee-aware math + receipts.** An outcome set that
   should sum to 1 sums to 1.04. Delphi shows all 11 arithmetic steps, subtracts
   venue fees and liquidity-based slippage, and fires **only** because the edge
   survives: net $146 on $5k, 2.92% after fees, 15% annualized.
2. **bot-doctor self-repair.** A venue silently renames its HTML classes; the
   scraper drifts. bot-doctor re-derives the selectors from the new markup by
   *content heuristics*, shows an old→new selector diff, and re-runs green.

Plus: cross-venue spread detection that **refuses to call a 7% gap "free money"**
because the two contracts settle on different sources/times (mandatory criteria
diff), an intern brief that flags resolution-criteria gotchas, and a paper-PnL
ledger where **"precision is measured, not claimed"** (80%, not 100%).

## Quickstart

```bash
make demo-delphi     # full deterministic demo, < 1s, no network
make test            # 9 applause-moment smoke tests
```

No `make`? Run directly (works everywhere):

```bash
python -m delphi.demo.demo_delphi     # the demo
python -m pytest delphi/tests -q      # the tests
```

- **Requirements:** Python 3.11+ and `rich` (`pip install rich`). `pydantic` /
  `requests` are only needed for the manual fetch scripts, never the demo.
- **Windows:** if `make` is missing, use `mingw32-make` or the `python -m` lines above.
- Set `DELPHI_DEMO_PAUSE=0.4` to add dramatic pauses between demo steps.

## Layout (everything self-contained under `delphi/`)

```
delphi/
  db.py                 SQLite schema + helpers (markets, alerts, ledger, bots)
  loader.py             load snapshots/fixtures -> SQLite (offline)
  fees.py               fee + slippage models — the math behind every alert
  arb_partition.py      APPLAUSE A: partition-sum arb, step-by-step receipts
  arb_crossvenue.py     cross-venue spread + MANDATORY resolution-criteria diff
  bots.py               registry + bot-doctor (heartbeat / drift / repair)
  bots_fleet/           toy HTML scrapers (v1 selectors that drift on v2)
  brief.py              intern brief with criteria-gotcha heuristics
  ledger.py             paper-PnL honesty table (measured precision)
  demo/demo_delphi.py   the deterministic rich demo
  scripts/fetch_*.py    manual, network-only cache refresh (NOT used by demo)
  data/snapshots/       fixture_*.json (15 seeded markets) — labeled as fixtures
  data/fixtures/        page_v1.html / page_v2.html (markup-drift fixtures)
  tests/                one smoke test per applause moment
  hermes/delphi/        Hermes skill manifests + cron configs + integration map
Makefile                thin launcher (demo-delphi, test, load)
```

## What's real vs. stubbed

**Real (runs today, tested):**
- Partition & cross-venue detectors with the full fee/slippage math and receipts.
- bot-doctor drift detection + selector re-derivation + repair.
- Intern-brief gotcha heuristics; paper-PnL ledger with measured precision.
- SQLite persistence across `markets / alerts / ledger / bots`.
- Deterministic offline demo; 9 passing smoke tests.
- Hermes skill manifests (agentskills.io format) + cron configs.

**Seeded / labeled (not silently faked):**
- Market data is 15 hand-authored **fixtures** in `data/snapshots/fixture_*.json`,
  clearly labeled. `scripts/fetch_*.py` hit the real public Polymarket/Kalshi APIs
  to refresh caches, but are run manually and never inside the demo.
- The 12-alert ledger history is seeded, labeled as hypothetical paper trades.

**Stubbed / mapped (not wired to a live service):**
- No live Telegram bot — the demo **prints the message payloads that would be sent**,
  formatted as Telegram messages.
- The intern brief's prose note uses deterministic heuristics in the demo;
  production routes it to a frontier Claude model (`claude-opus-4-8`).
- The `hermes-agent` runtime binding is a **mapping doc**, not a live install:
  real, well-formed manifests point at the exact Python entrypoints that run here.
  See `delphi/hermes/delphi/HERMES_INTEGRATION.md`.
- No execution, no payments, no group mode, no web UI (out of scope by design).

## Fee & slippage model (documented)

- **Polymarket:** parameterized 2% fee on winnings.
- **Kalshi:** per-contract fee `0.07 · p · (1−p)`.
- **Slippage:** linear market impact `slippage = k · size / liquidity`, `k = 0.5`.

All parameters live in `delphi/fees.py`; every alert's numbers trace back to them.

## Compliance

> Decision-support software. No execution. Polymarket/Kalshi geo-restrict access;
> nothing here is trading advice.
