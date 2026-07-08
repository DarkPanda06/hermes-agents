---
name: bot-doctor
description: Heartbeat the scraper fleet, detect parse failure / schema drift when a venue renames its markup, then self-repair by re-deriving selectors from the new markup via content heuristics and re-running green.
metadata:
  cadence: "*/10 * * * *"
  entrypoint: "delphi.bots:heartbeat"
  repair_entrypoint: "delphi.bots:repair"
---

# bot-doctor

Runs each scraper against its target page. On drift (missing fields / no matching
containers) it marks the bot `status=drift`, then `repair` re-derives the selector
mapping from the new markup by CONTENT heuristics (a `?` = the question, a
`data-outcome` element = a price, a `YYYY-MM-DD` = resolution, a bare integer =
liquidity), shows an old→new selector diff, and re-runs to `status=repaired`.

## Inputs
- `bots` registry, current page HTML.

## Outputs
- `bots` rows updated (status, last_heartbeat, schema_hash); a selector diff report.

## Reasoning contract
Prints the full detect → drift → re-derive (diff) → repaired sequence.
