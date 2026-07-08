# README_SKELETON.md — fill in the morning (15 min max)

---

# Hermes Agents: Maitre & Delphi Desk

**One thesis, demonstrated twice: the valuable agent is the one that says no.**
Same Hermes spine — cron ingestion → subagents → durable memory → transparent
judgment with receipts — pointed at two domains.

<!-- GIF 1: Maitre rejecting the trending event (record: `make demo-maitre`, crop
to the rejection block, ~12s). Tools: terminalizer / asciinema+agg / plain screen rec → gif -->

**Maitre** — a concierge with a compounding taste graph. Scans events across
listings, Instagram flyers, and WhatsApp forwards; rejects ~90% before you see
them — including the trending ones — with reasons drawn from *your* history; books
what survives; gets sharper after every outing.

<!-- GIF 2: Delphi's arb alert with fee math OR the bot-doctor repair sequence, ~12s -->

**Delphi Desk** — a prediction-market intern. Reads every new Polymarket/Kalshi
listing on cron, fires arbitrage alerts only when edge survives fees at executable
size (math shown, receipts attached), and self-repairs its own scraper fleet when
sites change. Alert quality is tracked in a paper-PnL ledger — measured, not claimed.

## Run the demos (no API keys, ~60s each)
```
make demo-maitre
make demo-delphi
make test
```

## The two moments to look at
1. `maitre`: ask why the trending event was excluded → data-driven rejection citing
   the user's own past ratings and budget. (maitre/explain.py)
2. `delphi`: a scraper breaks on changed markup → orchestrator detects drift,
   re-derives the parser, shows the diff, resumes. (delphi/bots.py)

## Architecture on Hermes
[2-3 sentences + point to hermes/ manifests, cron configs, memory mapping]

## What's real vs. stubbed (honesty section)
| Real | Stubbed / seeded |
|---|---|
| Fit scoring, rejection explanations, feedback→weight deltas | Event inventory seeded from real listings (no live scraping in demo) |
| Partition & cross-venue arb math w/ fee models, criteria diff | Market snapshots cached/fixtured (fetch scripts included) |
| Bot drift detection + self-repair on fixtures | Telegram delivery printed, not sent; briefs heuristic, LLM-routed in prod |

## Compliance
Decision-support software. No trade execution. Polymarket/Kalshi geo-restrict
access. Nothing here is trading advice.

## PRDs
Full product thinking in /docs: [link the two PRD md files — commit them, they show depth]
