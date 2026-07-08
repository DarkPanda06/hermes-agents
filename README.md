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
