"""Selector-driven HTML market scraper (stdlib only).

A scraper is just a mapping of schema-field -> CSS class name. Parsing splits the
page into <article class="{card}"> blocks and pulls each field's text by its class.
When a venue renames its classes, the old mapping extracts nothing -> schema drift.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Fields the market schema requires from a scraped page.
REQUIRED_FIELDS = ("question", "prices", "liquidity_usd", "resolution_date")


@dataclass
class Selectors:
    card: str            # article/container class
    question: str
    price: str           # element carries data-outcome="..."
    liquidity: str
    resolution: str

    def as_dict(self) -> dict:
        return {
            "card": self.card, "question": self.question, "price": self.price,
            "liquidity": self.liquidity, "resolution": self.resolution,
        }


def _blocks(html: str, card_cls: str) -> list[tuple[str, str]]:
    """Return [(opening_tag_attrs, inner_html)] for each matching card."""
    return re.findall(rf'<article class="{re.escape(card_cls)}"([^>]*)>(.*?)</article>', html, re.S)


def _first_text(block: str, cls: str) -> str | None:
    m = re.search(rf'<[a-z0-9]+ class="{re.escape(cls)}"[^>]*>(.*?)</[a-z0-9]+>', block, re.S)
    return m.group(1).strip() if m else None


def _priced(block: str, cls: str) -> list[tuple[str, float]]:
    out = []
    for outcome, txt in re.findall(
        rf'<[a-z0-9]+ class="{re.escape(cls)}" data-outcome="([^"]+)"[^>]*>(.*?)</[a-z0-9]+>', block, re.S):
        try:
            out.append((outcome.strip(), float(txt.strip())))
        except ValueError:
            pass
    return out


def _market_id(block: str) -> str | None:
    m = re.search(r'data-market-id="([^"]+)"', block)
    return m.group(1) if m else None


@dataclass
class ScrapeResult:
    ok: bool
    markets: list = field(default_factory=list)
    error: str | None = None


class HTMLMarketScraper:
    def __init__(self, name: str, venue: str, selectors: Selectors):
        self.name = name
        self.venue = venue
        self.selectors = selectors

    def parse(self, html: str) -> ScrapeResult:
        s = self.selectors
        blocks = _blocks(html, s.card)
        if not blocks:
            return ScrapeResult(ok=False, error=f"no <article class='{s.card}'> blocks found — markup drift?")
        markets = []
        for attrs, b in blocks:
            question = _first_text(b, s.question)
            priced = _priced(b, s.price)
            liq_txt = _first_text(b, s.liquidity)
            resolution = _first_text(b, s.resolution)
            if not question or len(priced) < 2 or liq_txt is None or resolution is None:
                return ScrapeResult(
                    ok=False,
                    error=(f"card {_market_id(attrs)!r}: extracted "
                           f"question={bool(question)} prices={len(priced)} "
                           f"liquidity={liq_txt is not None} resolution={resolution is not None} "
                           f"— fields missing, schema drift"))
            markets.append({
                "id": f"{self.venue[:2]}_{_market_id(attrs)}",
                "venue": self.venue,
                "question": question,
                "outcomes": [o for o, _ in priced],
                "prices": [p for _, p in priced],
                "liquidity_usd": float(liq_txt),
                "resolution_date": resolution,
            })
        return ScrapeResult(ok=True, markets=markets)
