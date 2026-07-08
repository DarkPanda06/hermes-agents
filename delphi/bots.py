"""Bot registry + bot-doctor  —  APPLAUSE MOMENT B.

A fleet of scraper bots each parses a venue page into the market schema. When a
venue silently renames its markup, the bot's hard-coded selectors extract nothing
(schema drift). bot-doctor:
  1. heartbeat detects the parse failure / schema drift,
  2. marks the bot status=drift,
  3. re-derives the selector mapping from the NEW markup by CONTENT heuristics
     (find the same fields by what their text looks like) and shows a selector diff,
  4. re-runs the scraper green and marks status=repaired.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field

from .bots_fleet.base import HTMLMarketScraper, Selectors, ScrapeResult

DEMO_CLOCK = "2026-07-08T14:30:00Z"


# ---------------------------------------------------------------- registry ---
def register(conn, scraper: HTMLMarketScraper, target: str, cadence_s: int, ts: str = DEMO_CLOCK) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO bots (name, target, cadence_s, last_heartbeat, status, schema_hash) "
        "VALUES (?,?,?,?,?,?)",
        (scraper.name, target, cadence_s, ts, "ok", ""),
    )
    conn.commit()


def get_bot(conn, name: str) -> dict | None:
    row = conn.execute("SELECT * FROM bots WHERE name=?", (name,)).fetchone()
    return dict(row) if row else None


def _shape_hash(markets: list) -> str:
    if not markets:
        return ""
    fields = sorted(markets[0].keys())
    return hashlib.sha1(("|".join(fields)).encode()).hexdigest()[:12]


# --------------------------------------------------------------- heartbeat ---
@dataclass
class Heartbeat:
    bot: str
    status: str            # ok | drift
    ok: bool
    n_markets: int
    error: str | None
    schema_hash: str
    ts: str


def heartbeat(conn, scraper: HTMLMarketScraper, html: str, ts: str = DEMO_CLOCK) -> Heartbeat:
    result = scraper.parse(html)
    status = "ok" if result.ok else "drift"
    shash = _shape_hash(result.markets) if result.ok else ""
    conn.execute(
        "UPDATE bots SET status=?, last_heartbeat=?, schema_hash=? WHERE name=?",
        (status, ts, shash, scraper.name),
    )
    conn.commit()
    return Heartbeat(
        bot=scraper.name, status=status, ok=result.ok,
        n_markets=len(result.markets), error=result.error, schema_hash=shash, ts=ts,
    )


# ------------------------------------------------------- selector re-derive ---
_ELEM = re.compile(r'<([a-z0-9]+)\s+class="([^"]+)"([^>]*)>(.*?)</\1>', re.S)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_INT = re.compile(r"^\d+$")


def _dominant_card_class(html: str) -> str | None:
    classes = re.findall(r'<article class="([^"]+)"', html)
    if not classes:
        return None
    return Counter(classes).most_common(1)[0][0]


def rederive_selectors(html: str) -> Selectors | None:
    """Infer selector classes from the new markup purely by content heuristics."""
    card = _dominant_card_class(html)
    if not card:
        return None
    blocks = re.findall(rf'<article class="{re.escape(card)}"[^>]*>(.*?)</article>', html, re.S)
    if not blocks:
        return None
    q_cls = p_cls = liq_cls = res_cls = None
    for m in _ELEM.finditer(blocks[0]):
        tag, cls, attrs, text = m.groups()
        t = text.strip()
        if "data-outcome=" in attrs:
            p_cls = p_cls or cls
        elif t.endswith("?"):
            q_cls = q_cls or cls
        elif _DATE.match(t):
            res_cls = res_cls or cls
        elif _INT.match(t):
            liq_cls = liq_cls or cls
    if not all([q_cls, p_cls, liq_cls, res_cls]):
        return None
    return Selectors(card=card, question=q_cls, price=p_cls, liquidity=liq_cls, resolution=res_cls)


def selector_diff(old: Selectors, new: Selectors) -> list:
    """Human-readable diff of changed selector fields (old -> new)."""
    o, n = old.as_dict(), new.as_dict()
    lines = []
    for field_name in o:
        if o[field_name] != n[field_name]:
            lines.append(f"  {field_name:12s}: '{o[field_name]}'  ->  '{n[field_name]}'")
        else:
            lines.append(f"  {field_name:12s}: '{o[field_name]}'  (unchanged)")
    return lines


# ------------------------------------------------------------------ repair ---
@dataclass
class RepairReport:
    bot: str
    success: bool
    old_selectors: dict
    new_selectors: dict | None
    diff: list = field(default_factory=list)
    n_markets: int = 0
    error: str | None = None


def repair(conn, scraper: HTMLMarketScraper, html: str, ts: str = DEMO_CLOCK) -> RepairReport:
    old = scraper.selectors
    new = rederive_selectors(html)
    if new is None:
        return RepairReport(bot=scraper.name, success=False, old_selectors=old.as_dict(),
                            new_selectors=None, error="could not re-derive selectors from markup")
    diff = selector_diff(old, new)
    scraper.selectors = new            # apply the repaired mapping
    result: ScrapeResult = scraper.parse(html)
    if result.ok:
        conn.execute(
            "UPDATE bots SET status='repaired', last_heartbeat=?, schema_hash=? WHERE name=?",
            (ts, _shape_hash(result.markets), scraper.name),
        )
        conn.commit()
    return RepairReport(
        bot=scraper.name, success=result.ok, old_selectors=old.as_dict(),
        new_selectors=new.as_dict(), diff=diff, n_markets=len(result.markets),
        error=None if result.ok else result.error,
    )
