<<<<<<< HEAD
# Hermes Agents: Maitre & Delphi Desk

**One thesis, demonstrated twice: the valuable agent is the one that says no.**
Same Hermes spine — cron ingestion → subagents → durable memory → transparent
judgment with receipts — pointed at two domains.

> _GIF 1: Maitre rejecting the trending event — run `make demo-maitre`, crop to the
> "why it never reached you" block (~12s)._

**Maitre** — a concierge with a compounding taste graph. Scans events across
listings, Instagram flyers, and WhatsApp forwards; rejects ~90% before you see
them — including the trending ones — with reasons drawn from *your* history; books
what survives; gets sharper after every outing.

> _GIF 2: Delphi's arb alert with fee math OR the bot-doctor repair sequence (~12s)._

**Delphi Desk** — a prediction-market intern. Reads every new Polymarket/Kalshi
listing on cron, fires arbitrage alerts only when edge survives fees at executable
size (math shown, receipts attached), and self-repairs its own scraper fleet when
sites change. Alert quality is tracked in a paper-PnL ledger — measured, not claimed.

> Maitre is on this (`maitre`) branch; Delphi is built on the `delphi` branch. This
> is a monorepo assembled from both.

## Run the demos (no API keys, ~60s each)
```bash
make demo-maitre     # or:  python -m demo.demo_maitre
make demo-delphi     # (delphi branch)
make test            # or:  python -m pytest maitre/tests -q
```
No `make`? The `python -m …` forms above work directly (Python 3.11+, `pip install
rich pytest`). Everything runs against seeded local data — zero network calls.

## The two moments to look at
1. **`maitre`**: ask why the trending event was excluded → a data-driven rejection
   citing the user's own past ratings and budget cap. The receipts ("you rated
   Sunburn Arena 2/5 in Jan", "₹3,999 vs your ₹1,500/mo cap") are queried from the
   DB, not templated. (`maitre/explain.py`)
2. **`maitre` compounds**: a 5/5 review sharpens the taste graph (weights printed:
   `genre·jazz 0.92 → 0.95`, `crowd_tolerance 0.20 → 0.26`), and a mid-size jazz
   night that was *rejected at 57%* now *surfaces at 60%* — with the agent
   explaining the shift. (`maitre/feedback.py`)
3. **`delphi`**: a scraper breaks on changed markup → orchestrator detects drift,
   re-derives the parser, shows the diff, resumes. (`delphi/bots.py`, delphi branch)

## Architecture on Hermes
Both agents share one spine: a **cron** ingests inventory into **durable memory**,
**skills** (subagents) score it with transparent, weighted judgment, and every
verdict persists with its reasons so "why?" is answerable later. Maitre's four
skills (`taste-intake`, `fit-scorer`, `plan-composer`, `feedback-loop`) and its cron
config live in [`hermes/maitre/`](hermes/maitre/); the module-by-module mapping is in
[`hermes/maitre/HERMES_INTEGRATION.md`](hermes/maitre/HERMES_INTEGRATION.md). The
compounding taste graph *is* the memory: `feedback-loop` writes it, and the next
scan reads a sharper user.

## What's real vs. stubbed (honesty section)
| Real | Stubbed / seeded |
|---|---|
| Fit scoring, rejection explanations, feedback→weight deltas (`maitre/`) | Event inventory seeded from realistic listings (`maitre/data/seed_events.json`) — no live scraping in the demo |
| Every decision persists with per-component reasons (`decisions` table) | Flyer OCR: real extraction **prompt** + a pre-extracted example (`scripts/extract_flyer.py`); no live vision call |
| Partition & cross-venue arb math w/ fee models, criteria diff (`delphi/`) | Market snapshots cached/fixtured (fetch scripts included) |
| Bot drift detection + self-repair on fixtures | Telegram/calendar delivery **printed as payloads**, not sent; no live network anywhere in `make demo-*` |

## Compliance
Decision-support software. No trade execution. Polymarket/Kalshi geo-restrict
access. Nothing here is trading advice.

## PRDs
Product thinking in [`docs/maitre_PRD.md`](docs/maitre_PRD.md) (Delphi's PRD lives on
the `delphi` branch).
=======
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
>>>>>>> delphi
