"""Polymarket-style page scraper. Hard-coded to the page_v1.html markup — it will
DRIFT on page_v2.html until bot-doctor re-derives the selectors.
"""
from pathlib import Path

from .base import HTMLMarketScraper, Selectors

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "fixtures"

V1_SELECTORS = Selectors(
    card="market-card",
    question="market-question",
    price="outcome-price",
    liquidity="market-liquidity",
    resolution="resolution-date",
)


def make_scraper() -> HTMLMarketScraper:
    return HTMLMarketScraper("polymarket-scraper", "polymarket", V1_SELECTORS)
