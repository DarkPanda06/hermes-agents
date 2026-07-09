"""Intern brief for a newly-listed market (lightweight, no LLM in the demo).

Prints a structured brief: question, resolution criteria with GOTCHAS flagged by
regex/heuristics ("unless", "official source", date ambiguity), current odds,
liquidity, and a one-paragraph efficient-vs-mispriced note.

In production this template + the raw market is routed to a frontier model for the
prose note; the demo uses deterministic heuristics so it runs offline (see README).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import arb_partition as ap

# Heuristic gotcha patterns: (label, regex, why-it-matters)
_GOTCHAS = [
    ("conditional carve-out", re.compile(r"\bunless\b|\bexcept\b|\bprovided that\b", re.I),
     "resolution has an exception clause — the obvious YES/NO can be overridden."),
    ("source dependency", re.compile(r"\bofficial\b|\bper the\b|\bsource\b|\bblog\b", re.I),
     "resolution depends on a specific named source; if it is silent/late, resolution is ambiguous."),
    ("subjective threshold", re.compile(r"\blimited\b|\bpreview\b|\bmeaningful\b|\bsignificant\b", re.I),
     "contains a subjective qualifier a human must judge — dispute risk."),
    ("date/timezone ambiguity", re.compile(r"\bend of\b|\bby (the )?end\b|\baround\b|\bearly\b|\blate\b", re.I),
     "fuzzy timing with no explicit timezone/cutoff — settlement moment is unclear."),
]


@dataclass
class Brief:
    market_id: str
    venue: str
    question: str
    criteria: str
    odds: dict
    liquidity_usd: float
    resolution_date: str | None
    days_to_resolution: int | None
    gotchas: list = field(default_factory=list)   # [{label, why, evidence}]
    efficiency_note: str = ""


def _find_gotchas(criteria: str) -> list:
    found = []
    for label, rx, why in _GOTCHAS:
        m = rx.search(criteria or "")
        if m:
            start = max(0, m.start() - 25)
            end = min(len(criteria), m.end() + 25)
            snippet = criteria[start:end].strip()
            found.append({"label": label, "why": why, "evidence": f"...{snippet}..."})
    return found


def _efficiency_note(market: dict) -> str:
    alert = ap.evaluate(market)
    odds = ", ".join(f"{o} {p:.0%}" for o, p in zip(market["outcomes"], market["prices"]))
    if alert.fired:
        return (f"MISPRICED: outcome prices sum to {alert.price_sum:.3f} — a partition edge of "
                f"{alert.raw_edge_pct:.2f}% survives fees ({alert.edge_after_fees_pct:.2f}% net). "
                f"Current odds: {odds}. Worth a closer look before it corrects.")
    return (f"EFFICIENT-ish: prices sum to {alert.price_sum:.3f}; any raw edge "
            f"({alert.raw_edge_pct:.2f}%) does not survive fees/slippage "
            f"({alert.edge_after_fees_pct:.2f}% net). Current odds: {odds}. "
            f"No free money here — the interesting risk is in the resolution criteria above.")


def build_brief(market: dict) -> Brief:
    days = ap._days_between(market.get("fetched_at"), market.get("resolution_date"))
    return Brief(
        market_id=market["id"], venue=market.get("venue", ""),
        question=market["question"], criteria=market.get("resolution_criteria", ""),
        odds={o: p for o, p in zip(market["outcomes"], market["prices"])},
        liquidity_usd=market.get("liquidity_usd") or 0.0,
        resolution_date=market.get("resolution_date"), days_to_resolution=days,
        gotchas=_find_gotchas(market.get("resolution_criteria", "")),
        efficiency_note=_efficiency_note(market),
    )


def newly_listed(markets: list) -> list:
    return [m for m in markets if m.get("newly_listed")]
