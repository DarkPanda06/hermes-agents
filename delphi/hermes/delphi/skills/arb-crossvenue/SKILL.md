---
name: arb-crossvenue
description: Detect cross-venue spreads on near-equivalent binary markets after both venues' fees. NEVER emits an alert without the verbatim resolution-criteria diff and the "criteria are NOT identical — verify before trading" warning.
metadata:
  cadence: "*/15 * * * *"
  entrypoint: "delphi.arb_crossvenue:scan"
  min_similarity: 0.5
---

# arb-crossvenue

Matches binary markets across venues by question similarity, computes the lock-in
spread after both venues' fees + slippage, and attaches a MANDATORY criteria diff.
An alert is only `actionable` when the economics clear threshold AND the resolution
criteria are identical — otherwise it is flagged for human review.

## Inputs
- `markets` (from `scanner`), `size_usd`, `threshold_pct`, `min_similarity`.

## Outputs
- `alerts` rows (kind=`crossvenue`) including the criteria diff and warning.

## Reasoning contract
Hard rule: no cross-venue alert is ever emitted without the criteria diff block.
