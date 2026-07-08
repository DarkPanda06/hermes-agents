"""Partition-sum arbitrage detector  —  APPLAUSE MOMENT A.

For a mutually-exclusive-and-exhaustive outcome set, the prices must sum to 1.
Any deviation is a raw edge:  raw_edge = |Σp − 1|.

An alert fires ONLY if the edge SURVIVES fees + slippage for a target size S.
Every alert carries the full arithmetic (step-by-step), the price receipt, size,
capital, days-to-resolution and annualized return — the reasoning IS the product.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import date

from . import fees

DEFAULT_SIZE_USD = 5000.0
DEFAULT_THRESHOLD_PCT = 1.0  # edge_after_fees must exceed this to fire


def _days_between(as_of: str | None, resolution_date: str | None) -> int | None:
    if not as_of or not resolution_date:
        return None
    try:
        a = date.fromisoformat(as_of[:10])
        b = date.fromisoformat(resolution_date[:10])
    except ValueError:
        return None
    return (b - a).days


@dataclass
class PartitionAlert:
    market_id: str
    venue: str
    question: str
    outcomes: list
    prices: list
    price_sum: float
    raw_edge_pct: float
    direction: str                 # "sell overpriced bundle" | "buy underpriced bundle"
    size_usd: float
    capital_usd: float
    gross_profit_usd: float
    fee_usd: float
    slippage_usd: float
    net_profit_usd: float
    edge_after_fees_pct: float
    days_to_resolution: int | None
    annualized_pct: float
    fired: bool
    threshold_pct: float
    receipt_ts: str | None
    steps: list = field(default_factory=list)

    def to_alert_row(self) -> dict:
        """Shape for the alerts table."""
        return {
            "id": f"alert_partition_{self.market_id}",
            "kind": "partition",
            "market_ids_json": json.dumps([self.market_id]),
            "edge_pct": round(self.raw_edge_pct, 4),
            "edge_after_fees_pct": round(self.edge_after_fees_pct, 4),
            "size_usd": self.size_usd,
            "annualized_pct": round(self.annualized_pct, 4),
            "receipts_json": json.dumps(asdict(self)),
            "ts": self.receipt_ts,
        }


def evaluate(market: dict, size_usd: float = DEFAULT_SIZE_USD,
             threshold_pct: float = DEFAULT_THRESHOLD_PCT) -> PartitionAlert:
    """Evaluate one market's outcome set. Returns a PartitionAlert (fired flag set).

    ``market`` is a decoded dict from loader.load_markets (outcomes/prices lists).
    """
    prices = [float(p) for p in market["prices"]]
    P = sum(prices)
    raw_edge = abs(P - 1.0)
    raw_edge_pct = raw_edge * 100.0
    venue = market.get("venue", "polymarket")
    as_of = market.get("fetched_at")
    days = _days_between(as_of, market.get("resolution_date"))

    # Direction & capital per guaranteed $1-payout set.
    if P > 1.0:
        direction = "sell overpriced bundle"
        capital_per_set = 1.0            # post collateral to cover the $1 payout
    else:
        direction = "buy underpriced bundle"
        capital_per_set = P              # pay Σp now, collect $1 at resolution

    n_sets = size_usd / capital_per_set if capital_per_set else 0.0
    gross_profit = n_sets * raw_edge
    # Fee on winnings across all sets, via the venue model.
    fee = _partition_fee(venue, raw_edge, n_sets)
    slippage = fees.slippage_pct(size_usd, market.get("liquidity_usd") or 0) * size_usd
    net = gross_profit - fee - slippage
    edge_after_fees_pct = (net / size_usd * 100.0) if size_usd else 0.0
    annualized = fees.annualized_pct(edge_after_fees_pct, days)
    fired = edge_after_fees_pct > threshold_pct

    steps = _build_steps(market, prices, P, raw_edge_pct, direction, size_usd,
                         capital_per_set, n_sets, gross_profit, fee, slippage,
                         net, edge_after_fees_pct, days, annualized,
                         threshold_pct, fired, venue)

    return PartitionAlert(
        market_id=market["id"], venue=venue, question=market["question"],
        outcomes=market["outcomes"], prices=prices, price_sum=round(P, 6),
        raw_edge_pct=raw_edge_pct, direction=direction, size_usd=size_usd,
        capital_usd=round(capital_per_set * n_sets, 2), gross_profit_usd=round(gross_profit, 2),
        fee_usd=round(fee, 2), slippage_usd=round(slippage, 2), net_profit_usd=round(net, 2),
        edge_after_fees_pct=edge_after_fees_pct, days_to_resolution=days,
        annualized_pct=annualized, fired=fired, threshold_pct=threshold_pct,
        receipt_ts=as_of, steps=steps,
    )


def _partition_fee(venue: str, raw_edge_per_set: float, n_sets: float) -> float:
    """Fee on winnings across all sets. Polymarket: 2% of profit; Kalshi: per-contract."""
    if (venue or "").lower() == "kalshi":
        # profit is realized on the winning leg; approximate per-set contract fee at p=0.5
        return fees.kalshi_fee_per_contract(0.5) * n_sets
    return fees.polymarket_fee(raw_edge_per_set) * n_sets


def _build_steps(market, prices, P, raw_edge_pct, direction, size_usd, capital_per_set,
                 n_sets, gross_profit, fee, slippage, net, edge_after_fees_pct,
                 days, annualized, threshold_pct, fired, venue) -> list:
    terms = " + ".join(f"{o}={p:.3f}" for o, p in zip(market["outcomes"], prices))
    verdict = "FIRES" if fired else "does NOT fire"
    return [
        f"1. Outcome set (mutually exclusive & exhaustive): {terms}",
        f"2. Σp = {P:.4f}   →   raw edge = |Σp − 1| = {raw_edge_pct:.2f}%",
        f"3. Strategy: {direction}  (capital ${capital_per_set:.3f} per guaranteed $1 set)",
        f"4. Size ${size_usd:,.0f}  →  N = {n_sets:,.0f} sets",
        f"5. Gross profit = N × raw_edge = {n_sets:,.0f} × {raw_edge_pct/100:.4f} = ${gross_profit:,.2f}",
        f"6. Venue fee ({venue}) = ${fee:,.2f}",
        f"7. Slippage = k·S/liquidity × S = {fees.SLIP_K}·{size_usd:,.0f}/{market.get('liquidity_usd'):,.0f} × ${size_usd:,.0f} = ${slippage:,.2f}",
        f"8. Net profit = {gross_profit:,.2f} − {fee:,.2f} − {slippage:,.2f} = ${net:,.2f}",
        f"9. Edge after fees = ${net:,.2f} / ${size_usd:,.0f} = {edge_after_fees_pct:.2f}%",
        f"10. Days to resolution = {days}  →  annualized = {annualized:.1f}%",
        f"11. Threshold = {threshold_pct:.1f}%  →  {edge_after_fees_pct:.2f}% {'>' if fired else '≤'} {threshold_pct:.1f}%  →  {verdict}",
    ]


def scan(markets: list, size_usd: float = DEFAULT_SIZE_USD,
         threshold_pct: float = DEFAULT_THRESHOLD_PCT) -> list:
    """Evaluate every market; return only the alerts that FIRED (sorted by edge)."""
    fired = [a for m in markets if (a := evaluate(m, size_usd, threshold_pct)).fired]
    fired.sort(key=lambda a: a.edge_after_fees_pct, reverse=True)
    return fired
