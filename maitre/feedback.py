"""Feedback loop — the compounding proof.

A rated outing writes back into the taste graph:
  • a strong review reinforces the matched genre & vibe affinities, and
  • sustained good nights out nudge crowd_tolerance up a touch (never toward the
    massive rooms the user hates — it's clamped well below 'medium').

The point of the demo is the DELTA: we print every weight that moved, then re-scan
and show a previously-rejected, borderline event crossing the bar — with the agent
explaining exactly why it shifted. All of this is persisted, so it compounds.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from . import db, loader, fit

LR_GENRE = 0.35        # learning rate for matched genre affinities
LR_VIBE = 0.30         # learning rate for matched vibe affinities
TOL_STEP = 0.06        # how far crowd_tolerance can move per great night
TOL_CEILING = 0.45     # never let a single good streak push into 'medium' territory


@dataclass
class Delta:
    dimension: str     # e.g. "genre · jazz", "crowd_tolerance"
    before: float
    after: float

    @property
    def moved(self) -> bool:
        return round(self.after, 3) != round(self.before, 3)

    def line(self) -> str:
        return f"{self.dimension}: {self.before:.2f} → {self.after:.2f}"


def _boost(old: float, lr: float, strength: float) -> float:
    """Move an affinity toward 1.0 by a fraction of the remaining headroom."""
    return round(old + lr * (1.0 - old) * strength, 3)


def apply_review(conn, event_id: str, rating: int, vibe_match: float | None = None,
                 notes: str | None = None) -> list[Delta]:
    """Record an outing and mutate the taste profile. Returns the weight deltas."""
    profile = db.get_profile(conn)
    event = {e["id"]: e for e in loader.load_events(conn, upcoming_only=False)}[event_id]
    vibe_match = vibe_match if vibe_match is not None else (rating / 5.0)

    # log the outing (durable memory — the history the explainer later cites)
    conn.execute(
        """INSERT OR REPLACE INTO outings
             (id, event_id, rating, vibe_match, would_repeat, notes, ts)
           VALUES (?,?,?,?,?,?,?)""",
        (f"out_fb_{event_id}", event_id, rating, vibe_match, 1 if rating >= 4 else 0,
         notes or "reviewed via feedback loop", datetime(2026, 7, 12, 1, 0, 0).isoformat()),
    )
    conn.commit()

    deltas: list[Delta] = []
    if rating < 4:
        return deltas  # only positive reviews sharpen the graph in this demo

    strength = (rating - 3) / 2.0 * float(vibe_match)   # 5/5 @ 0.95 -> ~0.95

    genre_aff = dict(profile.get("genre_affinities", {}))
    for tag in event.get("genre_tags", []):
        old = genre_aff.get(tag, fit.UNKNOWN_AFFINITY)
        new = _boost(old, LR_GENRE, strength)
        genre_aff[tag] = new
        deltas.append(Delta(f"genre · {tag.replace('_', ' ')}", old, new))
    db.set_profile_value(conn, "genre_affinities", genre_aff)

    vibe_aff = dict(profile.get("vibe_affinities", {}))
    for tag in event.get("vibe_tags", []):
        old = vibe_aff.get(tag, fit.UNKNOWN_AFFINITY)
        new = _boost(old, LR_VIBE, strength)
        vibe_aff[tag] = new
        deltas.append(Delta(f"vibe · {tag}", old, new))
    db.set_profile_value(conn, "vibe_affinities", vibe_aff)

    # engagement: a run of good nights out earns the user a slightly bigger room
    tol_before = fit.crowd_tolerance_level(profile)
    tol_after = round(min(TOL_CEILING, tol_before + TOL_STEP * strength), 3)
    if tol_after != tol_before:
        db.set_profile_value(conn, "crowd_tolerance", tol_after)
        deltas.append(Delta("crowd_tolerance", tol_before, tol_after))

    return deltas


def explain_shift(before: "fit.Decision", after: "fit.Decision") -> str:
    """One-line 'why did this cross the bar now' for a newly-surfaced event."""
    return (f"{after.title} crossed your bar this time — {before.fit_pct}% → {after.fit_pct}%. "
            "Two weeks ago the mid-size room sank it; after last night your jazz affinity "
            "ticked up and I trust you a notch more in a mid room for the right music.")


def newly_surfaced(before: list, after: list) -> list:
    """Events that were rejected before the review and surface after it."""
    was_reject = {d.event_id for d in before if d.verdict == "reject"}
    return [d for d in after if d.verdict == "surface" and d.event_id in was_reject]


# --- demo orchestration (called by demo/demo_maitre.py) -------------------

def run_demo_step(conn, console, *, booked_event_id, render_scan, render_rejection,
                  user_says, agent_says, rule) -> None:
    from rich.panel import Panel
    from rich.text import Text
    from rich import box

    rule("4 · feedback → the graph compounds")
    user_says("last night was perfect. 5/5 — front table, could hear every brush on the snare.")

    before = fit.scan(conn, record=False)
    deltas = apply_review(conn, booked_event_id, rating=5, vibe_match=0.96,
                          notes="Perfect. Front table, heard every brush on the snare.")
    after = fit.scan(conn)   # re-scan with the sharpened graph, persist new decisions

    body = Text()
    body.append("your taste graph moved:\n\n", style="bold white")
    for d in deltas:
        if d.moved:
            body.append("  ▲ ", style="green")
            body.append(d.line() + "\n", style="white")
    body.append("\ncrowd_tolerance is still 'low' — Sunburn is still a hard pass. "
                "But a mid-size jazz room just came into range.", style="dim")
    console.print()
    console.print(Panel(body, border_style="green", box=box.ROUNDED,
                        title="[bold]🧠 memory write[/]", title_align="left", padding=(1, 2)))

    rule("5 · next Saturday?")
    user_says("what about next Saturday?")

    fresh = newly_surfaced(before, after)
    render_scan(after)
    if fresh:
        d_after = fresh[0]
        d_before = next(b for b in before if b.event_id == d_after.event_id)
        agent_says("[bold green]new this week[/] — something that didn't clear your bar two weeks ago:")
        console.print()
        console.print(Panel(
            Text(explain_shift(d_before, d_after), style="white"),
            border_style="green", box=box.HEAVY, padding=(1, 2),
            title=f"[bold green]▲ now surfacing · {d_after.fit_pct}% fit[/]", title_align="left",
        ))
