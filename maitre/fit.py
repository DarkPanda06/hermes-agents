"""Transparent fit scorer — the core of Maitre.

Every event is scored by a weighted sum of named components. Each component
returns BOTH a number AND a human reason string, because the "why" is the product:

    fit =  w_genre·genre_affinity + w_vibe·vibe_match + w_budget·budget_fit
         + w_logistics·logistics  − w_crowd·crowd_penalty − w_fatigue·fatigue

A ``hard_no`` tag (e.g. a Bollywood club night, stag-entry) short-circuits to a
reject regardless of score. Everything else is judged on the transparent math and
compared against a single threshold. Every scored event writes a ``decisions`` row
carrying the full component breakdown + reasons, so any verdict is auditable later.

Nothing here is hardcoded to a specific event — all facts come from the DB
(the event row + the user's taste_profile).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime

from . import db

# --- weights (sum of positives = 0.82; penalties subtract) ----------------
W_GENRE = 0.30
W_VIBE = 0.26
W_BUDGET = 0.18
W_LOGISTICS = 0.08
W_CROWD = 0.34      # penalty weight
W_FATIGUE = 0.10    # penalty weight

SURFACE_THRESHOLD = 0.58   # raw fit must exceed this to be surfaced

# how a capacity_class maps to an intrinsic "crowd level" (0..1)
CAPACITY_CROWD_LEVEL = {"intimate": 0.12, "mid": 0.50, "massive": 0.95}
# how the profile's crowd_tolerance word maps to a tolerated crowd level (0..1)
CROWD_TOLERANCE_LEVEL = {"low": 0.20, "medium": 0.55, "high": 0.90}

# default affinity for a tag the profile has never seen
UNKNOWN_AFFINITY = 0.40
_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@dataclass
class Component:
    name: str
    value: float          # the component's 0..1 score (penalties are also 0..1, applied negatively)
    weight: float
    contribution: float   # signed contribution to the final fit (weight·value, negative for penalties)
    reason: str


@dataclass
class Decision:
    event_id: str
    title: str
    fit: float                    # raw weighted fit (can be negative)
    fit_pct: int                  # display %, clamp(raw,0,1)·100 rounded
    verdict: str                  # surface | reject
    components: list = field(default_factory=list)   # list[Component]
    hard_no: str | None = None    # the tag that vetoed it, if any
    one_liner: str = ""           # the single best "why" / "why not" line

    def reasons_json(self) -> str:
        return json.dumps(
            {
                "fit": round(self.fit, 4),
                "fit_pct": self.fit_pct,
                "verdict": self.verdict,
                "hard_no": self.hard_no,
                "one_liner": self.one_liner,
                "components": [asdict(c) for c in self.components],
            }
        )


# --- component scorers: each returns (value, weight, reason) ---------------

def _genre_component(event: dict, profile: dict):
    aff = profile.get("genre_affinities", {})
    tags = event.get("genre_tags", []) or []
    scores = [aff.get(t, UNKNOWN_AFFINITY) for t in tags]
    if not scores:
        return 0.0, W_GENRE, "no genre tags on this event"
    top = max(scores)
    mean = sum(scores) / len(scores)
    value = 0.7 * top + 0.3 * mean   # best-matching genre leads, blended with the rest
    best_tag = tags[scores.index(top)]
    reason = f"{best_tag.replace('_', ' ')} is one of your top genres (affinity {top:.2f})"
    if top < 0.35:
        reason = f"{best_tag.replace('_', ' ')} is well outside your taste (affinity {top:.2f})"
    return value, W_GENRE, reason


def _vibe_component(event: dict, profile: dict):
    aff = profile.get("vibe_affinities", {})
    tags = event.get("vibe_tags", []) or []
    scored = [(t, aff.get(t, UNKNOWN_AFFINITY)) for t in tags]
    if not scored:
        return 0.0, W_VIBE, "no vibe tags on this event"
    value = sum(s for _, s in scored) / len(scored)
    best = max(scored, key=lambda x: x[1])
    worst = min(scored, key=lambda x: x[1])
    if value >= 0.6:
        reason = f"the room reads {best[0]} ({best[1]:.2f}) — your kind of night"
    else:
        reason = f"vibe is mostly {worst[0]} ({worst[1]:.2f}), not what you seek out"
    return value, W_VIBE, reason


def _budget_component(event: dict, profile: dict):
    cap = float(profile.get("budget_cap_month", 0) or 0)
    price = float(event.get("price_min") or 0)
    if cap <= 0:
        return 1.0, W_BUDGET, "no budget cap set"
    if price <= cap:
        value = 1.0
        reason = f"₹{price:,.0f} sits inside your ₹{cap:,.0f}/month cap"
    else:
        over = (price - cap) / cap
        value = max(0.0, 1.0 - over)
        reason = f"₹{price:,.0f} entry vs your ₹{cap:,.0f}/month cap ({price / cap:.1f}× over)"
    return value, W_BUDGET, reason


def _logistics_component(event: dict, profile: dict):
    preferred = set(profile.get("preferred_areas", []) or [])
    area = event.get("area")
    if area in preferred:
        return 1.0, W_LOGISTICS, f"{area} — close to you"
    return 0.45, W_LOGISTICS, f"{area} — a hike from {profile.get('home_area', 'home')}"


def _crowd_penalty(event: dict, profile: dict):
    level = CAPACITY_CROWD_LEVEL.get(event.get("capacity_class"), 0.5)
    tol_word = profile.get("crowd_tolerance", "medium")
    tol = CROWD_TOLERANCE_LEVEL.get(tol_word, 0.55)
    penalty = max(0.0, level - tol)
    cap_word = event.get("capacity_class", "unknown")
    if penalty <= 0:
        reason = f"{cap_word} room — well within your {tol_word} crowd tolerance"
    else:
        reason = f"{cap_word} crowd overshoots your {tol_word} crowd tolerance (+{penalty:.2f})"
    return penalty, W_CROWD, reason


def _fatigue_penalty(event: dict, profile: dict):
    energy_by_day = profile.get("energy_by_day", {}) or {}
    day = _weekday(event.get("dt"))
    energy = float(energy_by_day.get(day, 0.6))
    penalty = 1.0 - energy
    reason = f"{day} energy is {energy:.2f} — {'a good night to go out' if energy >= 0.6 else 'a low-energy day for you'}"
    return penalty, W_FATIGUE, reason


def _weekday(dt_str: str | None) -> str:
    if not dt_str:
        return "Sat"
    try:
        return _WEEKDAYS[datetime.fromisoformat(dt_str).weekday()]
    except ValueError:
        return "Sat"


def _check_hard_no(event: dict, profile: dict) -> str | None:
    hard_nos = set(profile.get("hard_nos", []) or [])
    for tag in list(event.get("genre_tags", [])) + list(event.get("vibe_tags", [])):
        if tag in hard_nos:
            return tag
    return None


def score(event: dict, profile: dict) -> Decision:
    """Score one event against the taste profile. Returns a full Decision."""
    hard_no = _check_hard_no(event, profile)

    specs = [
        ("genre_affinity", _genre_component(event, profile), +1),
        ("vibe_match", _vibe_component(event, profile), +1),
        ("budget_fit", _budget_component(event, profile), +1),
        ("logistics", _logistics_component(event, profile), +1),
        ("crowd_penalty", _crowd_penalty(event, profile), -1),
        ("fatigue", _fatigue_penalty(event, profile), -1),
    ]

    components, fit = [], 0.0
    for name, (value, weight, reason), sign in specs:
        contribution = sign * weight * value
        fit += contribution
        components.append(Component(name, round(value, 4), weight, round(contribution, 4), reason))

    fit_pct = int(round(max(0.0, min(1.0, fit)) * 100))

    if hard_no:
        verdict = "reject"
        one_liner = f"hard no — you've flagged '{hard_no.replace('_', ' ')}' as a dealbreaker"
    else:
        verdict = "surface" if fit > SURFACE_THRESHOLD else "reject"
        one_liner = _one_liner(event, components, verdict)

    return Decision(
        event_id=event["id"], title=event["title"], fit=fit, fit_pct=fit_pct,
        verdict=verdict, components=components, hard_no=hard_no, one_liner=one_liner,
    )


def _one_liner(event: dict, components: list, verdict: str) -> str:
    """Pick the single most informative reason for the verdict."""
    if verdict == "surface":
        # the biggest positive contribution sells it
        best = max((c for c in components if c.contribution > 0), key=lambda c: c.contribution)
        return best.reason
    # rejected: the biggest drag explains it (largest-magnitude negative, else weakest positive)
    negatives = [c for c in components if c.contribution < 0]
    if negatives:
        worst = min(negatives, key=lambda c: c.contribution)
        # only lead with a penalty if it's actually meaningful
        if abs(worst.contribution) > 0.05:
            return worst.reason
    weakest = min((c for c in components if c.contribution >= 0), key=lambda c: c.value)
    return weakest.reason


def scan(conn, *, upcoming_only: bool = True, record: bool = True) -> list[Decision]:
    """Score every (upcoming) event, optionally persist decisions, return them sorted.

    Surfaced events come first (highest fit first); rejects follow.
    """
    from . import loader
    profile = db.get_profile(conn)
    events = loader.load_events(conn, upcoming_only=upcoming_only)
    decisions = [score(e, profile) for e in events]
    if record:
        _record(conn, decisions)
    decisions.sort(key=lambda d: (d.verdict != "surface", -d.fit))
    return decisions


def _record(conn, decisions: list[Decision]) -> None:
    ts = datetime(2026, 7, 9, 9, 0, 0).isoformat()  # deterministic stamp for the demo
    for d in decisions:
        conn.execute(
            """
            INSERT OR REPLACE INTO decisions (id, event_id, fit_score, verdict, reasons_json, ts)
            VALUES (?,?,?,?,?,?)
            """,
            (f"dec_{d.event_id}", d.event_id, round(d.fit, 4), d.verdict, d.reasons_json(), ts),
        )
    conn.commit()


def surfaced(decisions: list[Decision]) -> list[Decision]:
    return [d for d in decisions if d.verdict == "surface"]


def rejected(decisions: list[Decision]) -> list[Decision]:
    return [d for d in decisions if d.verdict == "reject"]
