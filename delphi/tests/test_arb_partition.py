"""Smoke test for APPLAUSE MOMENT A — partition-sum arb math.

fixture (a): pm_fed_sep2026, Σp = 1.04, FIRES with correct arithmetic.
fixture (c): pm_rain_nyc_2026, Σp = 1.01 marginal overround, does NOT fire
             because fees + slippage eat the edge.
"""
from delphi import db, loader, arb_partition as ap


def _load():
    conn = db.reset(":memory:")
    loader.load_snapshots(conn)
    markets = {m["id"]: m for m in loader.load_markets(conn)}
    conn.close()
    return markets


def test_fixture_a_fires_with_correct_math():
    m = _load()["pm_fed_sep2026"]
    alert = ap.evaluate(m, size_usd=5000.0, threshold_pct=1.0)

    # raw edge: |1.04 - 1| = 4%
    assert abs(alert.price_sum - 1.04) < 1e-9
    assert abs(alert.raw_edge_pct - 4.0) < 1e-9
    assert alert.direction == "sell overpriced bundle"

    # gross = 5000 sets * 0.04 = 200 ; fee = 0.02*0.04*5000 = 4 ; slippage = 0.01*5000 = 50
    assert abs(alert.gross_profit_usd - 200.0) < 1e-6
    assert abs(alert.fee_usd - 4.0) < 1e-6
    assert abs(alert.slippage_usd - 50.0) < 1e-6
    assert abs(alert.net_profit_usd - 146.0) < 1e-6

    # edge after fees = 146/5000 = 2.92%  -> fires above 1% threshold
    assert abs(alert.edge_after_fees_pct - 2.92) < 1e-9
    assert alert.fired is True
    assert alert.days_to_resolution == 71  # 2026-07-08 -> 2026-09-17
    assert alert.steps and alert.steps[-1].endswith("FIRES")


def test_fixture_c_does_not_fire():
    m = _load()["pm_rain_nyc_2026"]
    alert = ap.evaluate(m, size_usd=5000.0, threshold_pct=1.0)

    # Σp = 1.01 -> raw edge looks like 1% but fees+slippage make net negative.
    assert abs(alert.price_sum - 1.01) < 1e-9
    assert alert.net_profit_usd < 0
    assert alert.fired is False


def test_scan_returns_only_fired_sorted():
    markets = list(_load().values())
    fired = ap.scan(markets, size_usd=5000.0, threshold_pct=1.0)
    ids = [a.market_id for a in fired]
    assert "pm_fed_sep2026" in ids
    assert "pm_rain_nyc_2026" not in ids
    # sorted by edge_after_fees descending
    assert fired == sorted(fired, key=lambda a: a.edge_after_fees_pct, reverse=True)
