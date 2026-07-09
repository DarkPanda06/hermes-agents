---
name: brief
description: Produce an intern brief for a newly-listed market — question, resolution criteria with gotchas flagged (conditional carve-outs, source dependency, subjective thresholds, date/timezone ambiguity), current odds, liquidity, and an efficient-vs-mispriced note.
metadata:
  cadence: "@on-new-listing"
  entrypoint: "delphi.brief:build_brief"
  production_note: "prose note routed to a frontier model in production; demo uses deterministic heuristics"
---

# brief

For a newly-listed market, flags resolution-criteria gotchas by regex/heuristic and
writes a short efficient-vs-mispriced note (backed by the partition detector's math).

## Inputs
- A `markets` row flagged `newly_listed`.

## Outputs
- A structured brief (question, criteria, gotchas[], odds, liquidity, note).

## Reasoning contract
Every gotcha carries its evidence snippet and why-it-matters. Demo runs offline;
production routes the prose note to a frontier Claude model.
