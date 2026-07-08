"""Rejection explainer  —  THE APPLAUSE MOMENT.

Given a rejected event, produce the "why not" grounded in the user's OWN history:
we walk the Decision's negative components, then pull the taste_profile values and
the past outing ratings that actually drove each drag. Nothing here is a hardcoded
fact about a specific event — every receipt is queried from the DB, so if you edit
a rating or the budget cap, the explanation changes with it.

Output shape (see demo):
  "Rejected Sunburn Reload: massive room (your crowd tolerance is low — you rated
   Sunburn Arena 2/5 in Jan, NH7 2/5 in Mar), ₹3,999 vs your ₹1,500/mo cap,
   EDM affinity 0.08. Override?"
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from . import db, loader, fit

# how much a component must hurt the fit before it earns a spot in the "why not"
DRAG_CUTOFF = 0.03
# a positive component counts as a drag if it's meaningfully below this
WEAK_POSITIVE = 0.55
_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_CAPACITY_PHRASE = {
    "massive": "a massive (3,000+) room",
    "mid": "a mid-size room",
    "intimate": "an intimate room",
}


@dataclass
class Receipt:
    factor: str            # crowd | budget | genre | vibe | logistics
    claim: str             # the short, headline-ready phrase
    evidence: list = field(default_factory=list)   # human strings pulled from the DB


@dataclass
class Explanation:
    event_id: str
    title: str
    verdict: str
    receipts: list = field(default_factory=list)   # list[Receipt], most-damning first
    loves: list = field(default_factory=list)      # positive contrast from 5/5 history
    hard_no: str | None = None

    def headline(self) -> str:
        """One-line rejection with its top receipts inline, ending in 'Override?'."""
        if self.hard_no:
            return (f"Rejected {self.title}: hard no — you've flagged "
                    f"'{self.hard_no.replace('_', ' ')}' as a dealbreaker. Override?")
        parts = "; ".join(r.claim for r in self.receipts[:3])
        return f"Rejected {self.title}: {parts}. Override?"


def _month(ts: str | None) -> str:
    try:
        return _MONTHS[datetime.fromisoformat(ts).month]
    except (TypeError, ValueError):
        return ""


def _drag_score(component) -> float:
    """How much this component is costing the fit (higher = more damning)."""
    if component.contribution < 0:                 # a penalty (crowd, fatigue)
        return -component.contribution
    if component.value < WEAK_POSITIVE:            # a positive that failed to fire
        return component.weight * (0.85 - component.value)
    return 0.0


def _crowd_receipt(event, profile, outings, component) -> Receipt:
    tol = profile.get("crowd_tolerance", "medium")
    phrase = _CAPACITY_PHRASE.get(event.get("capacity_class"), "a large room")
    claim = f"{phrase} vs your {tol} crowd tolerance"
    # Evidence: past nights in the SAME capacity class the user rated poorly.
    evidence = []
    for o in sorted(outings, key=lambda o: o["rating"]):
        if o["event_capacity_class"] == event.get("capacity_class") and o["rating"] <= 2:
            evidence.append(
                f"you rated {o['event_title']} {o['rating']}/5 in {_month(o['ts'])}"
                f" (“{_clip(o['notes'])}”)"
            )
    return Receipt("crowd", claim, evidence)


def _budget_receipt(event, profile, component) -> Receipt:
    cap = float(profile.get("budget_cap_month", 0) or 0)
    price = float(event.get("price_min") or 0)
    claim = f"₹{price:,.0f} entry vs your ₹{cap:,.0f}/month cap ({price / cap:.1f}× over)"
    return Receipt("budget", claim, [f"budget_cap_month = ₹{cap:,.0f} (from your profile)"])


def _genre_receipt(event, profile, outings, component) -> Receipt:
    aff = profile.get("genre_affinities", {})
    weak = sorted(((g, aff.get(g, fit.UNKNOWN_AFFINITY)) for g in event.get("genre_tags", [])),
                  key=lambda x: x[1])
    if not weak:
        return Receipt("genre", "genre is off for you", [])
    g, a = weak[0]
    claim = f"{g.replace('_', ' ')} affinity {a:.2f} — near the bottom of your graph"
    evidence = []
    for o in sorted(outings, key=lambda o: o["rating"]):
        if g in o["event_genre_tags"] and o["rating"] <= 2:
            evidence.append(f"last {g.replace('_', ' ')} night ({o['event_title']}) you rated {o['rating']}/5")
    return Receipt("genre", claim, evidence)


def _vibe_receipt(event, profile, component) -> Receipt:
    aff = profile.get("vibe_affinities", {})
    weak = sorted(((v, aff.get(v, fit.UNKNOWN_AFFINITY)) for v in event.get("vibe_tags", [])),
                  key=lambda x: x[1])[:2]
    labels = ", ".join(f"{v} {a:.2f}" for v, a in weak)
    return Receipt("vibe", f"vibe reads {labels} — not what you seek out", [])


def _logistics_receipt(event, profile, component) -> Receipt:
    return Receipt("logistics", component.reason, [])


def _loves(outings) -> list:
    """Positive contrast: the rooms this user actually rates 5/5."""
    out = []
    for o in sorted(outings, key=lambda o: (-o["rating"], o["ts"])):
        if o["rating"] >= 5:
            out.append(f"{o['event_title']} ({o['rating']}/5, {o['event_capacity_class']})")
    return out


def _clip(text: str | None, n: int = 48) -> str:
    if not text:
        return ""
    text = text.strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def explain(conn, decision) -> Explanation:
    """Build a data-driven Explanation for a (typically rejected) Decision."""
    profile = db.get_profile(conn)
    event = {e["id"]: e for e in loader.load_events(conn, upcoming_only=False)}[decision.event_id]
    outings = loader.load_outings(conn)

    if decision.hard_no:
        return Explanation(decision.event_id, decision.title, decision.verdict,
                           receipts=[], loves=_loves(outings), hard_no=decision.hard_no)

    builders = {
        "crowd_penalty": lambda c: _crowd_receipt(event, profile, outings, c),
        "budget_fit": lambda c: _budget_receipt(event, profile, c),
        "genre_affinity": lambda c: _genre_receipt(event, profile, outings, c),
        "vibe_match": lambda c: _vibe_receipt(event, profile, c),
        "logistics": lambda c: _logistics_receipt(event, profile, c),
    }

    cap = float(profile.get("budget_cap_month", 0) or 0)
    price = float(event.get("price_min") or 0)

    scored = []
    for c in decision.components:
        drag = _drag_score(c)
        # A hard budget blowout is a headline-worthy receipt even though its weight
        # is modest — money over the cap is crisp evidence. Float it just under crowd.
        if c.name == "budget_fit" and cap and price > cap:
            drag = max(drag, 0.24)
        if drag > DRAG_CUTOFF and c.name in builders:
            scored.append((drag, c))
    scored.sort(key=lambda x: x[0], reverse=True)

    receipts = [builders[c.name](c) for _, c in scored]
    return Explanation(decision.event_id, decision.title, decision.verdict,
                       receipts=receipts, loves=_loves(outings))
