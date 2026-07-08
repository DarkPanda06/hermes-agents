"""Smoke tests for the fit scorer (Task 2).

The seeded taste graph must produce the demo's headline numbers deterministically:
40 events scanned -> 3 surfaced, 37 rejected, and the trending EDM event rejected
with the crowd penalty as its dominant drag.
"""
from maitre import db, loader, fit


def _load():
    conn = db.reset(":memory:")
    loader.load_seed(conn)
    return conn


def test_scan_surfaces_exactly_three():
    conn = _load()
    decisions = fit.scan(conn)
    surfaced = fit.surfaced(decisions)
    rejected = fit.rejected(decisions)
    assert len(surfaced) == 3
    assert len(rejected) == 37
    # surfaced list is sorted best-first
    assert surfaced[0].event_id == "ev_pianoman_quartet"
    assert surfaced == sorted(surfaced, key=lambda d: d.fit, reverse=True)
    conn.close()


def test_trending_event_is_rejected_hard():
    conn = _load()
    profile = db.get_profile(conn)
    event = {e["id"]: e for e in loader.load_events(conn)}["ev_sunburn_reload"]
    d = fit.score(event, profile)

    assert d.verdict == "reject"
    assert d.fit < 0                      # deeply negative for this persona
    assert d.fit_pct == 0
    # crowd penalty is the single biggest drag
    crowd = next(c for c in d.components if c.name == "crowd_penalty")
    assert crowd.contribution < 0
    assert crowd.contribution == min(c.contribution for c in d.components)
    # budget also fails: ₹3,999 far over the ₹1,500 cap -> budget_fit collapses to 0
    budget = next(c for c in d.components if c.name == "budget_fit")
    assert budget.value == 0.0
    conn.close()


def test_every_component_carries_a_reason():
    conn = _load()
    profile = db.get_profile(conn)
    event = {e["id"]: e for e in loader.load_events(conn)}["ev_pianoman_quartet"]
    d = fit.score(event, profile)
    assert d.verdict == "surface"
    assert len(d.components) == 6
    for c in d.components:
        assert c.reason and isinstance(c.reason, str)
    conn.close()


def test_hard_no_short_circuits():
    conn = _load()
    profile = db.get_profile(conn)
    events = {e["id"]: e for e in loader.load_events(conn)}
    # Bollywood club night carries the 'bollywood_night' hard-no tag.
    d = fit.score(events["ev_privee_bollywood"], profile)
    assert d.verdict == "reject"
    assert d.hard_no == "bollywood_night"
    # stag-entry club night is vetoed too
    d2 = fit.score(events["ev_nightclub_ladies"], profile)
    assert d2.hard_no == "stag_entry"
    conn.close()


def test_decisions_are_persisted_with_reasons():
    conn = _load()
    fit.scan(conn, record=True)
    row = conn.execute(
        "SELECT verdict, reasons_json FROM decisions WHERE event_id = 'ev_sunburn_reload'"
    ).fetchone()
    assert row["verdict"] == "reject"
    import json
    payload = json.loads(row["reasons_json"])
    assert payload["components"] and payload["one_liner"]
    conn.close()
