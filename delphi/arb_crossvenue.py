"""Cross-venue arbitrage detector with MANDATORY resolution-criteria diff.

Matches near-equivalent binary markets across venues, computes the lock-in spread
after BOTH venues' fees, and — crucially — never emits an alert without printing
the resolution-criteria diff verbatim plus the warning:

    "criteria are NOT identical — verify before trading."

The whole point: a fat cross-venue spread is often NOT free money, because the
two contracts do not resolve on the same thing. The diff is the product.
"""
from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass, field, asdict

from . import fees
from .arb_partition import _days_between, DEFAULT_SIZE_USD, DEFAULT_THRESHOLD_PCT

_STOP = {
    "will", "the", "a", "an", "on", "at", "be", "of", "in", "to", "for", "by",
    "end", "close", "above", "is", "are", "than", "and", "or", "yes", "no",
}


def _tokens(question: str) -> set:
    words = re.findall(r"[a-z0-9$,]+", (question or "").lower())
    return {w for w in words if w not in _STOP and len(w) > 1}


def _similarity(q1: str, q2: str) -> float:
    t1, t2 = _tokens(q1), _tokens(q2)
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / len(t1 | t2)


def _is_binary(m: dict) -> bool:
    outs = [o.lower() for o in m["outcomes"]]
    return outs == ["yes", "no"]


def match_pairs(markets: list, min_similarity: float = 0.5) -> list:
    """Return [(market_a, market_b, similarity)] cross-venue binary candidates."""
    binaries = [m for m in markets if _is_binary(m)]
    pairs = []
    for i, a in enumerate(binaries):
        for b in binaries[i + 1:]:
            if a.get("venue") == b.get("venue"):
                continue
            sim = _similarity(a["question"], b["question"])
            if sim >= min_similarity:
                pairs.append((a, b, sim))
    pairs.sort(key=lambda t: t[2], reverse=True)
    return pairs


def _criteria_diff(a: dict, b: dict) -> list:
    """Verbatim side-by-side + a unified word-level diff of the two criteria."""
    ca = a.get("resolution_criteria", "") or ""
    cb = b.get("resolution_criteria", "") or ""
    identical = ca.strip() == cb.strip()
    diff = list(difflib.unified_diff(
        ca.split(), cb.split(),
        fromfile=f"{a['venue']}:{a['id']}", tofile=f"{b['venue']}:{b['id']}",
        lineterm="", n=0,
    ))
    return identical, ca, cb, diff


@dataclass
class CrossVenueAlert:
    market_ids: list
    venues: list
    question_a: str
    question_b: str
    similarity: float
    buy_yes_venue: str
    buy_yes_price: float
    buy_no_venue: str
    buy_no_price: float
    lock_cost: float
    raw_spread_pct: float
    size_usd: float
    gross_profit_usd: float
    fee_usd: float
    slippage_usd: float
    net_profit_usd: float
    edge_after_fees_pct: float
    days_to_resolution: int | None
    annualized_pct: float
    economically_fires: bool
    criteria_identical: bool
    actionable: bool
    warning: str
    criteria_a: str
    criteria_b: str
    criteria_diff: list
    receipt_ts: str | None
    steps: list = field(default_factory=list)

    def to_alert_row(self) -> dict:
        return {
            "id": f"alert_crossvenue_{'_'.join(self.market_ids)}",
            "kind": "crossvenue",
            "market_ids_json": json.dumps(self.market_ids),
            "edge_pct": round(self.raw_spread_pct, 4),
            "edge_after_fees_pct": round(self.edge_after_fees_pct, 4),
            "size_usd": self.size_usd,
            "annualized_pct": round(self.annualized_pct, 4),
            "receipts_json": json.dumps(asdict(self)),
            "ts": self.receipt_ts,
        }


def evaluate_pair(a: dict, b: dict, size_usd: float = DEFAULT_SIZE_USD,
                  threshold_pct: float = DEFAULT_THRESHOLD_PCT,
                  similarity: float | None = None) -> CrossVenueAlert:
    """Compute the lock-in spread + fees for a candidate pair, always with diff."""
    # YES/NO prices per venue (index 0 = Yes, 1 = No by fixture convention).
    a_yes, a_no = float(a["prices"][0]), float(a["prices"][1])
    b_yes, b_no = float(b["prices"][0]), float(b["prices"][1])

    # Lock a guaranteed $1 payout: buy the cheaper YES and the cheaper NO.
    if a_yes <= b_yes:
        buy_yes_venue, buy_yes_price, yes_liq = a["venue"], a_yes, a.get("liquidity_usd") or 0
    else:
        buy_yes_venue, buy_yes_price, yes_liq = b["venue"], b_yes, b.get("liquidity_usd") or 0
    if a_no <= b_no:
        buy_no_venue, buy_no_price, no_liq = a["venue"], a_no, a.get("liquidity_usd") or 0
    else:
        buy_no_venue, buy_no_price, no_liq = b["venue"], b_no, b.get("liquidity_usd") or 0

    lock_cost = buy_yes_price + buy_no_price
    raw_spread = 1.0 - lock_cost
    raw_spread_pct = raw_spread * 100.0

    n_sets = size_usd / lock_cost if lock_cost else 0.0
    gross_profit = n_sets * raw_spread

    # Per-leg fees. Kalshi charges per contract upfront; Polymarket 2% on the
    # winning leg's profit (worst case = the more expensive winning leg).
    def leg_fee(venue, price):
        v = venue.lower()
        if v == "kalshi":
            return fees.kalshi_fee_per_contract(price) * n_sets
        # polymarket: profit if this leg wins = (1 - price)
        return fees.polymarket_fee(1.0 - price) * n_sets

    fee = leg_fee(buy_yes_venue, buy_yes_price) + leg_fee(buy_no_venue, buy_no_price)

    yes_notional = n_sets * buy_yes_price
    no_notional = n_sets * buy_no_price
    slippage = (fees.slippage_pct(yes_notional, yes_liq) * yes_notional
                + fees.slippage_pct(no_notional, no_liq) * no_notional)

    net = gross_profit - fee - slippage
    edge_after_fees_pct = (net / size_usd * 100.0) if size_usd else 0.0
    days = _days_between(a.get("fetched_at"), a.get("resolution_date"))
    annualized = fees.annualized_pct(edge_after_fees_pct, days)
    economically_fires = edge_after_fees_pct > threshold_pct

    identical, ca, cb, diff = _criteria_diff(a, b)
    actionable = economically_fires and identical
    warning = ("criteria ARE identical — spread is a clean arb candidate."
               if identical else
               "criteria are NOT identical — verify before trading.")

    steps = [
        f"1. Matched pair (similarity {similarity:.2f}): {a['venue']}:{a['id']}  vs  {b['venue']}:{b['id']}",
        f"2. Cheapest YES = {buy_yes_venue} @ {buy_yes_price:.3f} ; cheapest NO = {buy_no_venue} @ {buy_no_price:.3f}",
        f"3. Lock cost = {buy_yes_price:.3f} + {buy_no_price:.3f} = {lock_cost:.3f}  →  raw spread = {raw_spread_pct:.2f}%",
        f"4. Size ${size_usd:,.0f}  →  N = {n_sets:,.0f} sets ; gross = ${gross_profit:,.2f}",
        f"5. Fees (both venues) = ${fee:,.2f} ; slippage = ${slippage:,.2f}",
        f"6. Net = ${net:,.2f}  →  edge after fees = {edge_after_fees_pct:.2f}% (annualized {annualized:.1f}%)",
        f"7. Economics: {'PASS' if economically_fires else 'FAIL'} vs {threshold_pct:.1f}% threshold",
        f"8. Criteria identical? {'YES' if identical else 'NO'}  →  {warning}",
        f"9. ACTIONABLE as clean arb? {'YES' if actionable else 'NO — review criteria diff below'}",
    ]

    return CrossVenueAlert(
        market_ids=[a["id"], b["id"]], venues=[a["venue"], b["venue"]],
        question_a=a["question"], question_b=b["question"],
        similarity=round(similarity or 0.0, 4),
        buy_yes_venue=buy_yes_venue, buy_yes_price=buy_yes_price,
        buy_no_venue=buy_no_venue, buy_no_price=buy_no_price,
        lock_cost=round(lock_cost, 4), raw_spread_pct=raw_spread_pct,
        size_usd=size_usd, gross_profit_usd=round(gross_profit, 2),
        fee_usd=round(fee, 2), slippage_usd=round(slippage, 2),
        net_profit_usd=round(net, 2), edge_after_fees_pct=edge_after_fees_pct,
        days_to_resolution=days, annualized_pct=annualized,
        economically_fires=economically_fires, criteria_identical=identical,
        actionable=actionable, warning=warning, criteria_a=ca, criteria_b=cb,
        criteria_diff=diff, receipt_ts=a.get("fetched_at"), steps=steps,
    )


def scan(markets: list, size_usd: float = DEFAULT_SIZE_USD,
         threshold_pct: float = DEFAULT_THRESHOLD_PCT,
         min_similarity: float = 0.5) -> list:
    """Emit an alert for every matched pair whose raw spread clears threshold.

    Note: an alert is emitted for the economics, but ALWAYS carries the criteria
    diff + warning; ``actionable`` is only True when criteria are also identical.
    """
    alerts = []
    for a, b, sim in match_pairs(markets, min_similarity):
        alert = evaluate_pair(a, b, size_usd, threshold_pct, similarity=sim)
        if alert.raw_spread_pct > threshold_pct:
            alerts.append(alert)
    alerts.sort(key=lambda x: x.edge_after_fees_pct, reverse=True)
    return alerts
