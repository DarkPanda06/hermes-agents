"""Kalshi-style page scraper. Its target page markup is stable across the demo,
so this bot stays green while the polymarket bot drifts and self-repairs.
"""
from pathlib import Path

from .base import HTMLMarketScraper, Selectors

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "fixtures"

SELECTORS = Selectors(
    card="market-card",
    question="market-question",
    price="outcome-price",
    liquidity="market-liquidity",
    resolution="resolution-date",
)


def make_scraper() -> HTMLMarketScraper:
    return HTMLMarketScraper("kalshi-scraper", "kalshi", SELECTORS)
