"""Cross-venue detector: the BTC pair matches, the spread is real after fees,
and the criteria-diff + warning are MANDATORY on every alert."""
from delphi import db, loader, arb_crossvenue as xv


def _markets():
    conn = db.reset(":memory:")
    loader.load_snapshots(conn)
    markets = loader.load_markets(conn)
    conn.close()
    return markets


def test_btc_pair_is_matched():
    pairs = xv.match_pairs(_markets(), min_similarity=0.5)
    ids = {frozenset((a["id"], b["id"])) for a, b, _ in pairs}
    assert frozenset(("pm_btc_100k_2026", "k_btc_100k_2026")) in ids


def test_crossvenue_alert_always_has_criteria_diff_and_warning():
    alerts = xv.scan(_markets())
    assert alerts, "expected at least the BTC cross-venue alert"
    btc = next(a for a in alerts if set(a.market_ids) == {"pm_btc_100k_2026", "k_btc_100k_2026"})

    # cheaper YES = Kalshi @0.55, cheaper NO = Polymarket @0.38 -> lock 0.93, 7% raw
    assert btc.buy_yes_venue == "kalshi" and abs(btc.buy_yes_price - 0.55) < 1e-9
    assert btc.buy_no_venue == "polymarket" and abs(btc.buy_no_price - 0.38) < 1e-9
    assert abs(btc.raw_spread_pct - 7.0) < 1e-9

    # criteria differ (Coinbase 23:59 UTC vs CME CF BRR 4pm ET)
    assert btc.criteria_identical is False
    assert btc.criteria_diff, "diff block must be present"
    assert btc.warning == "criteria are NOT identical — verify before trading."
    # economically positive, but NOT actionable as a clean arb
    assert btc.economically_fires is True
    assert btc.actionable is False


def test_no_alert_without_diff_block():
    for a in xv.scan(_markets()):
        assert a.criteria_diff is not None
        assert a.warning
