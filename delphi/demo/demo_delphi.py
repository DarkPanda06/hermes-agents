"""Delphi demo — deterministic, offline, rich-formatted. Runs in < 60s.

Sequence (matches delphi/BUILD_PLAN.md Task 7):
  scan snapshots -> partition alert (full math) -> cross-venue alert (criteria
  diff + warning) -> bot-doctor self-repair -> intern brief -> ledger table ->
  closing line.

No network. Reads only delphi/data fixtures. Every decision prints its reasoning.
"""
from __future__ import annotations

import io
import sys
import time
from pathlib import Path

# Force UTF-8 so box-drawing / em-dashes render on the Windows console.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - older interpreters / redirected streams
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.text import Text
from rich import box

from delphi import db, loader, ledger, brief
from delphi import arb_partition as ap
from delphi import arb_crossvenue as xv
from delphi import bots
from delphi.bots_fleet.scraper_polymarket import make_scraper as make_pm
from delphi.bots_fleet.scraper_kalshi import make_scraper as make_k

console = Console()
FIX = Path(__file__).resolve().parents[1] / "data" / "fixtures"
PAUSE = float(__import__("os").environ.get("DELPHI_DEMO_PAUSE", "0.0"))


def _beat(t: float = 0.0):
    if PAUSE:
        time.sleep(t or PAUSE)


def telegram(title: str, body: str, tag: str = "") -> None:
    """Print the message payload that WOULD be sent (no live bot in the demo)."""
    text = Text()
    text.append(f"📣 {title}\n", style="bold")
    text.append(body)
    console.print(Panel(text, title=f"[dim]Telegram payload (NOT sent — demo){(' · ' + tag) if tag else ''}[/dim]",
                        border_style="cyan", box=box.ROUNDED, width=88))


# --------------------------------------------------------------------------- #
def header():
    console.print()
    console.print(Panel.fit(
        Text.from_markup(
            "[bold white]DELPHI[/bold white]  ·  prediction-market intern & orchestrator\n"
            "[dim]Hermes Agent runtime · decision-support only · seeded offline demo[/dim]"),
        border_style="magenta", box=box.DOUBLE))


def step_scan():
    console.print(Rule("[bold]1 · Scan cached snapshots[/bold]", style="magenta"))
    conn = db.reset()
    n = loader.load_snapshots(conn)
    markets = loader.load_markets(conn)
    fixtures = sum(1 for m in markets if m["is_fixture"])
    console.print(f"  Loaded [bold]{n}[/bold] markets from local cache "
                  f"([yellow]{fixtures} labeled FIXTURES[/yellow], 0 network calls).")
    venues = {}
    for m in markets:
        venues[m["venue"]] = venues.get(m["venue"], 0) + 1
    console.print("  Venues: " + ", ".join(f"{v}={c}" for v, c in sorted(venues.items())))
    console.print(f"  Price receipt timestamp: [dim]{markets[0]['fetched_at']}[/dim]\n")
    _beat(0.5)
    return conn, markets


def step_partition(markets):
    console.print(Rule("[bold]2 · Partition-sum arb  (APPLAUSE A)[/bold]", style="magenta"))
    fired = ap.scan(markets)
    console.print(f"  Evaluated {len(markets)} outcome sets · [bold green]{len(fired)} alert(s) survive fees[/bold green]\n")
    a = fired[0]
    steps = "\n".join(a.steps)
    console.print(Panel(steps, title=f"[bold]{a.venue} · {a.question}[/bold]",
                        subtitle=f"[green]FIRED[/green] · net ${a.net_profit_usd:,.2f} · "
                                 f"{a.edge_after_fees_pct:.2f}% after fees · {a.annualized_pct:.0f}% annualized",
                        border_style="green", box=box.ROUNDED, width=88))
    telegram(
        f"Partition arb · {a.edge_after_fees_pct:.2f}% edge",
        (f"{a.question}\n"
         f"Σp = {a.price_sum:.3f} → sell overpriced bundle\n"
         f"Size ${a.size_usd:,.0f} · net ${a.net_profit_usd:,.2f} · {a.annualized_pct:.0f}% annualized\n"
         f"Days to resolution: {a.days_to_resolution}"),
        tag="partition")
    console.print()
    _beat(0.6)
    return a


def step_crossvenue(markets):
    console.print(Rule("[bold]3 · Cross-venue spread + criteria diff[/bold]", style="magenta"))
    alerts = xv.scan(markets)
    a = alerts[0]

    econ = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    econ.add_row("Buy YES", f"{a.buy_yes_venue} @ {a.buy_yes_price:.3f}")
    econ.add_row("Buy NO", f"{a.buy_no_venue} @ {a.buy_no_price:.3f}")
    econ.add_row("Lock cost", f"{a.lock_cost:.3f}  →  raw spread {a.raw_spread_pct:.2f}%")
    econ.add_row("After fees", f"[bold]{a.edge_after_fees_pct:.2f}%[/bold] net (${a.net_profit_usd:,.2f}) · {a.annualized_pct:.0f}% annualized")
    console.print(Panel(econ, title=f"[bold]{a.venues[0]} ↔ {a.venues[1]}[/bold] · matched {a.similarity:.0%}",
                        border_style="yellow", box=box.ROUNDED, width=88))

    diff = Text()
    diff.append(f"{a.venues[0]}: ", style="bold")
    diff.append(a.criteria_a + "\n\n")
    diff.append(f"{a.venues[1]}: ", style="bold")
    diff.append(a.criteria_b + "\n\n")
    diff.append("⚠  " + a.warning, style="bold red")
    console.print(Panel(diff, title="[bold red]MANDATORY resolution-criteria diff[/bold red]",
                        subtitle=f"[red]actionable as clean arb? {'YES' if a.actionable else 'NO'}[/red]",
                        border_style="red", box=box.HEAVY, width=88))
    console.print("  [dim]The 7% 'spread' is not free money — the two contracts settle on "
                  "different sources/times.[/dim]\n")
    _beat(0.6)
    return a


def step_bot_doctor(conn):
    console.print(Rule("[bold]4 · bot-doctor self-repair  (APPLAUSE B)[/bold]", style="magenta"))
    v1 = (FIX / "page_v1.html").read_text(encoding="utf-8")
    v2 = (FIX / "page_v2.html").read_text(encoding="utf-8")

    pm, k = make_pm(), make_k()
    bots.register(conn, pm, target="polymarket page", cadence_s=300)
    bots.register(conn, k, target="kalshi page", cadence_s=300)

    console.print("  Fleet registered: [bold]polymarket-scraper[/bold], [bold]kalshi-scraper[/bold]")
    hb1 = bots.heartbeat(conn, pm, v1)
    hbk = bots.heartbeat(conn, k, v1)
    console.print(f"  heartbeat · polymarket-scraper → [green]{hb1.status}[/green] ({hb1.n_markets} markets)")
    console.print(f"  heartbeat · kalshi-scraper     → [green]{hbk.status}[/green] ({hbk.n_markets} markets)")
    console.print("  [dim]…venue silently ships new markup (renamed CSS classes)…[/dim]")
    _beat(0.5)

    hb2 = bots.heartbeat(conn, pm, v2)
    console.print(f"  heartbeat · polymarket-scraper → [bold red]{hb2.status.upper()}[/bold red]")
    console.print(f"    reason: [red]{hb2.error}[/red]")
    _beat(0.5)

    console.print("  [bold]bot-doctor[/bold] re-deriving selectors from new markup by content heuristics…")
    report = bots.repair(conn, pm, v2)
    diff_tbl = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    diff_tbl.add_column("field"); diff_tbl.add_column("old selector"); diff_tbl.add_column("new selector")
    for f in ("card", "question", "price", "liquidity", "resolution"):
        old, new = report.old_selectors[f], report.new_selectors[f]
        style = "green" if old != new else "dim"
        diff_tbl.add_row(f, f"[{style}]{old}[/{style}]", f"[{style}]{new}[/{style}]")
    console.print(Panel(diff_tbl, title="[bold]selector diff (old → re-derived)[/bold]",
                        border_style="green", box=box.ROUNDED, width=88))

    hb3 = bots.heartbeat(conn, pm, v2)
    console.print(f"  heartbeat · polymarket-scraper → [bold green]REPAIRED[/bold green] "
                  f"({hb3.n_markets} markets, status={bots.get_bot(conn, pm.name)['status']})\n")
    _beat(0.6)


def step_brief(markets):
    console.print(Rule("[bold]5 · Intern brief · newly-listed market[/bold]", style="magenta"))
    nl = brief.newly_listed(markets)
    b = brief.build_brief(nl[0])
    body = Text()
    body.append(f"{b.question}\n", style="bold")
    body.append(f"odds: {', '.join(f'{o} {p:.0%}' for o, p in b.odds.items())}  ·  "
                f"liquidity ${b.liquidity_usd:,.0f}  ·  resolves {b.resolution_date} "
                f"({b.days_to_resolution}d)\n\n")
    body.append("resolution criteria:\n", style="bold")
    body.append(b.criteria + "\n\n")
    body.append("gotchas flagged:\n", style="bold red")
    for g in b.gotchas:
        body.append(f"  ⚠ {g['label']}: ", style="red")
        body.append(f"{g['why']}\n")
        body.append(f"      evidence: {g['evidence']}\n", style="dim")
    body.append("\nnote: ", style="bold")
    body.append(b.efficiency_note)
    console.print(Panel(body, border_style="blue", box=box.ROUNDED, width=88))
    console.print("  [dim]Demo uses deterministic heuristics; production routes this to a frontier model.[/dim]\n")
    _beat(0.6)


def step_ledger(conn):
    console.print(Rule("[bold]6 · Paper-PnL ledger · measured honesty[/bold]", style="magenta"))
    ledger.seed_ledger(conn)
    tbl = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    tbl.add_column("alert"); tbl.add_column("kind"); tbl.add_column("edge%", justify="right")
    tbl.add_column("exec 60s", justify="center"); tbl.add_column("outcome"); tbl.add_column("PnL $", justify="right")
    for r in ledger.rows(conn):
        won = r["resolved"]
        execu = r["still_executable_60s"]
        outcome = ("won" if won else "false+") if execu else "missed"
        style = "green" if (won and execu) else ("red" if (execu and not won) else "yellow")
        tbl.add_row(r["id"], r["kind"], f"{r['edge']:.1f}",
                    "✓" if execu else "—", f"[{style}]{outcome}[/{style}]",
                    f"[{style}]{r['hypothetical_pnl_usd']:+.0f}[/{style}]")
    console.print(tbl)
    s = ledger.stats(conn)
    console.print(Panel.fit(
        Text.from_markup(
            f"precision [bold]{s.precision_pct:.0f}%[/bold] ({s.n_correct}/{s.n_executable} executable)   ·   "
            f"avg edge [bold]{s.avg_edge_pct:.2f}%[/bold]   ·   "
            f"hypothetical PnL [bold green]${s.total_pnl_usd:,.0f}[/bold green]"),
        border_style="green", box=box.ROUNDED))
    console.print('  [bold]"alert precision is measured, not claimed."[/bold]\n')
    _beat(0.5)


def closing():
    console.print(Rule(style="magenta"))
    console.print(Panel.fit(
        Text.from_markup(
            "[bold]Delphi[/bold]: partition arb · cross-venue w/ criteria diff · bot-doctor · brief · measured PnL\n"
            "[dim]Decision-support software. No execution. Polymarket/Kalshi geo-restrict access; "
            "nothing here is trading advice.[/dim]"),
        border_style="magenta", box=box.DOUBLE))
    console.print()


def main():
    header()
    conn, markets = step_scan()
    pa = step_partition(markets)
    xa = step_crossvenue(markets)
    # persist the two live-scan alerts (ledger seeds use ts='seed', no collision)
    conn.execute("INSERT OR REPLACE INTO alerts (id, kind, market_ids_json, edge_pct, "
                 "edge_after_fees_pct, size_usd, annualized_pct, receipts_json, ts) "
                 "VALUES (:id,:kind,:market_ids_json,:edge_pct,:edge_after_fees_pct,"
                 ":size_usd,:annualized_pct,:receipts_json,:ts)", pa.to_alert_row())
    conn.execute("INSERT OR REPLACE INTO alerts (id, kind, market_ids_json, edge_pct, "
                 "edge_after_fees_pct, size_usd, annualized_pct, receipts_json, ts) "
                 "VALUES (:id,:kind,:market_ids_json,:edge_pct,:edge_after_fees_pct,"
                 ":size_usd,:annualized_pct,:receipts_json,:ts)", xa.to_alert_row())
    conn.commit()
    step_bot_doctor(conn)
    step_brief(markets)
    step_ledger(conn)
    closing()
    conn.close()


if __name__ == "__main__":
    main()
