"""Smoke test for APPLAUSE MOMENT B — bot-doctor detects drift and self-repairs.

v1 markup: scraper is green.
v2 markup (renamed classes): scraper drifts.
repair: re-derives selectors by content heuristics, re-runs green with correct fields.
"""
from pathlib import Path

from delphi import db, bots
from delphi.bots_fleet.scraper_polymarket import make_scraper

FIX = Path(__file__).resolve().parents[1] / "data" / "fixtures"
V1 = (FIX / "page_v1.html").read_text(encoding="utf-8")
V2 = (FIX / "page_v2.html").read_text(encoding="utf-8")


def _registered_bot():
    conn = db.reset(":memory:")
    scraper = make_scraper()
    bots.register(conn, scraper, target="page_v1.html", cadence_s=300)
    return conn, scraper


def test_v1_is_green():
    conn, scraper = _registered_bot()
    hb = bots.heartbeat(conn, scraper, V1)
    assert hb.ok and hb.status == "ok"
    assert hb.n_markets == 3
    conn.close()


def test_v2_triggers_drift():
    conn, scraper = _registered_bot()
    bots.heartbeat(conn, scraper, V1)          # healthy first
    hb = bots.heartbeat(conn, scraper, V2)     # venue shipped renamed markup
    assert hb.ok is False
    assert hb.status == "drift"
    assert bots.get_bot(conn, scraper.name)["status"] == "drift"
    conn.close()


def test_repair_produces_correct_fields():
    conn, scraper = _registered_bot()
    bots.heartbeat(conn, scraper, V2)          # drift
    report = bots.repair(conn, scraper, V2)

    assert report.success is True
    assert report.n_markets == 3
    # selectors were re-derived to the v2 class names
    assert report.new_selectors["question"] == "mkt__title"
    assert report.new_selectors["price"] == "mkt__odds"
    assert report.new_selectors["liquidity"] == "mkt__liq"
    assert report.new_selectors["resolution"] == "mkt__resolve"
    assert report.new_selectors["card"] == "mkt"
    # a diff was produced and the bot is marked repaired
    assert any("->" in line for line in report.diff)
    assert bots.get_bot(conn, scraper.name)["status"] == "repaired"

    # re-run with repaired selectors yields correct market data
    result = scraper.parse(V2)
    assert result.ok
    btc = next(m for m in result.markets if "btc" in m["id"])
    assert btc["question"].startswith("Will Bitcoin close above $100,000")
    assert btc["outcomes"] == ["Yes", "No"]
    assert btc["prices"] == [0.62, 0.38]
    assert btc["liquidity_usd"] == 500000.0
    assert btc["resolution_date"] == "2026-12-31"
    conn.close()
