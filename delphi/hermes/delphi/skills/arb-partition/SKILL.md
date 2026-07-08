---
name: arb-partition
description: Detect partition-sum arbitrage on mutually-exclusive-exhaustive outcome sets. Fires only when the edge survives fees + slippage for a target size, with step-by-step arithmetic and a price receipt.
metadata:
  cadence: "*/5 * * * *"
  entrypoint: "delphi.arb_partition:scan"
  threshold_pct: 1.0
  default_size_usd: 5000
---

# arb-partition

For an outcome set that should sum to 1, computes `raw_edge = |Σp − 1|`, then the
edge after venue fees and liquidity-based slippage for a target size. Emits an
alert **only** if `edge_after_fees > threshold`.

## Inputs
- `markets` (from `scanner`), `size_usd`, `threshold_pct`.

## Outputs
- `alerts` rows (kind=`partition`) with full receipts_json: every arithmetic step,
  size, capital, days-to-resolution, annualized %, price-receipt timestamp.

## Reasoning contract
The alert payload IS the reasoning: 11 numbered steps ending in FIRES / does-not-fire.
