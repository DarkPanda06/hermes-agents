"""Deterministic, no-network demo for Maitre — the terminal IS the product.

Run:  make demo-maitre   (or)   python -m demo.demo_maitre

Flow (see maitre/BUILD_PLAN.md Task 4 & 5):
  1. "Saturday night?"  -> scan 40 events, surface 3, reject 37, with the WHY.
  2. Planted question    -> the trending EDM event's data-driven rejection.
  3. "Book option 1"     -> Telegram / calendar / logistics payloads.
  4. Feedback loop       -> a 5/5 review sharpens the graph; a borderline event
                            that was rejected now surfaces, and the agent says why.
Everything is seeded & local. No API keys. No network calls.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the repo root importable no matter how this file is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from maitre import db, loader, fit, explain, notify

console = Console(highlight=False)

USER = "[bold cyan]you ›[/]"
AGENT = "[bold magenta]maître ›[/]"


# --- narration helpers ----------------------------------------------------

def banner() -> None:
    console.print()
    console.print(Panel(
        Text.assemble(
            ("MAÎTRE", "bold white"),
            ("  ·  a concierge with a compounding taste graph\n", "white"),
            ("Scans every listing. Rejects ~90% before you see them — including the "
             "trending ones — with reasons drawn from your own history.", "dim"),
        ),
        box=box.DOUBLE, border_style="magenta", padding=(1, 3),
    ))


def user_says(text: str) -> None:
    console.print()
    console.print(f"{USER} [white]{text}[/]")


def agent_says(text: str) -> None:
    console.print(f"{AGENT} [white]{text}[/]")


def rule(title: str) -> None:
    console.print()
    console.rule(f"[bold]{title}", style="magenta")


# --- step renderers -------------------------------------------------------

def render_scan(decisions: list) -> None:
    surfaced = fit.surfaced(decisions)
    rejected = fit.rejected(decisions)
    agent_says(
        f"scanned [bold]{len(decisions)}[/] events → "
        f"[green]surfaced {len(surfaced)}[/], [red]rejected {len(rejected)}[/]. "
        "here's what survives for you:"
    )
    console.print()
    for i, d in enumerate(surfaced, 1):
        ev = _event(d.event_id)
        meta = (f"{ev['venue']} · {ev['area']} · ₹{ev['price_min']:,.0f} · "
                f"{ev['capacity_class']} room")
        body = Text.assemble(
            (meta + "\n", "dim"),
            ("why  ", "bold green"), (d.one_liner, "white"),
        )
        console.print(Panel(
            body, title=f"[bold]#{i}  ·  {d.fit_pct}% fit[/]",
            title_align="left", border_style="green", box=box.ROUNDED, padding=(0, 2),
        ))


def render_rejection(ex: explain.Explanation) -> None:
    lines = Text()
    lines.append("REJECTED  ", style="bold red")
    lines.append(ex.title + "\n\n", style="bold white")
    for r in ex.receipts[:4]:
        lines.append(f"• {r.claim}\n", style="white")
        for e in r.evidence:
            lines.append(f"     ↳ {e}\n", style="dim")
    if ex.loves:
        lines.append("\nthe rooms you actually rate 5/5: ", style="bold green")
        lines.append(", ".join(ex.loves), style="green")
    lines.append("\n\nOverride?", style="bold yellow")
    console.print(Panel(lines, border_style="red", box=box.HEAVY, padding=(1, 2),
                        title="[bold red]why it never reached you[/]", title_align="left"))


def render_booking(event: dict, profile: dict) -> None:
    tg = notify.telegram_confirmation(event)
    cal = notify.calendar_hold(event)
    packet = notify.logistics_packet(event, profile)

    console.print(Panel(tg, border_style="cyan", box=box.ROUNDED,
                        title="[bold]📱 Telegram → you[/]", title_align="left", padding=(1, 2)))

    cal_tbl = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    cal_tbl.add_column(style="bold dim"); cal_tbl.add_column(style="white")
    cal_tbl.add_row("event", cal["summary"])
    cal_tbl.add_row("when", f"{cal['dtstart']} → {cal['dtend']}")
    cal_tbl.add_row("where", cal["location"])
    cal_tbl.add_row("status", cal["status"])
    console.print(Panel(cal_tbl, border_style="blue", box=box.ROUNDED,
                        title="[bold]📅 Calendar hold[/]", title_align="left"))

    log_tbl = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    log_tbl.add_column(style="bold dim"); log_tbl.add_column(style="white")
    log_tbl.add_row("leave by", packet["leave_by"])
    log_tbl.add_row("travel", packet["travel"])
    log_tbl.add_row("doors", packet["doors"])
    log_tbl.add_row("budget", packet["budget"])
    log_tbl.add_row("table", packet["reservation"])
    log_tbl.add_row("note", packet["note"])
    console.print(Panel(log_tbl, border_style="green", box=box.ROUNDED,
                        title="[bold]🧭 Logistics packet[/]", title_align="left"))


# --- shared DB handle -----------------------------------------------------

_CONN = None

def _event(event_id: str) -> dict:
    return {e["id"]: e for e in loader.load_events(_CONN, upcoming_only=False)}[event_id]


def main() -> None:
    global _CONN
    banner()
    _CONN = db.reset()
    summary = loader.load_seed(_CONN)
    profile = db.get_profile(_CONN)

    # ---- Step 1: the Saturday scan ----
    rule("1 · Saturday night?")
    user_says("Saturday night?")
    decisions = fit.scan(_CONN)
    render_scan(decisions)

    # ---- Step 2: the planted question (APPLAUSE) ----
    rule("2 · “why isn't Sunburn Reload on there? it's all over my feed.”")
    user_says("wait — why isn't Sunburn Reload listed? it's all over my feed.")
    trending = next(d for d in decisions if d.event_id == "ev_sunburn_reload")
    ex = explain.explain(_CONN, trending)
    agent_says("because I already know how that night ends for you:")
    console.print()
    render_rejection(ex)

    # ---- Step 3: book option 1 ----
    rule("3 · book option 1")
    user_says("nailed it. book option 1.")
    top = fit.surfaced(decisions)[0]
    booked = _event(top.event_id)
    agent_says(f"booking [bold]{booked['title']}[/] — sending your packet:")
    console.print()
    render_booking(booked, profile)

    # ---- Step 4: the feedback loop (compounding proof) — wired in Task 5 ----

    console.print()
    console.rule("[dim]seeded, deterministic, zero network — see README 'What's real vs. stubbed'[/]",
                 style="dim")
    console.print()
    _CONN.close()


if __name__ == "__main__":
    main()
