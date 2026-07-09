"""Smoke test for the APPLAUSE MOMENT — the data-driven rejection explainer.

The rejection of the trending EDM event must cite the user's OWN history: the two
2/5 big-format outings, the budget cap, and the EDM affinity — all pulled from the
DB. The final assertion proves it is NOT a hardcoded template: mutate a rating in
the DB and the evidence changes with it.
"""
from maitre import db, loader, fit, explain


def _load():
    conn = db.reset(":memory:")
    loader.load_seed(conn)
    return conn


def _reject(conn, event_id):
    decs = fit.scan(conn)
    return next(d for d in decs if d.event_id == event_id)


def test_rejection_cites_users_own_history():
    conn = _load()
    ex = explain.explain(conn, _reject(conn, "ev_sunburn_reload"))
    head = ex.headline()

    assert head.startswith("Rejected Sunburn Reload")
    assert head.endswith("Override?")

    factors = {r.factor for r in ex.receipts}
    assert {"crowd", "budget", "genre"} <= factors

    # crowd receipt is grounded in the two poorly-rated massive nights
    crowd = next(r for r in ex.receipts if r.factor == "crowd")
    joined = " ".join(crowd.evidence)
    assert "Sunburn Arena" in joined and "2/5" in joined
    assert "NH7" in joined

    # budget receipt carries the real numbers from the event + profile
    budget = next(r for r in ex.receipts if r.factor == "budget")
    assert "3,999" in budget.claim and "1,500" in budget.claim

    # positive contrast comes from the 5/5 history, not a template
    assert any("5/5" in s for s in ex.loves)


def test_top_three_receipts_lead_the_headline():
    conn = _load()
    ex = explain.explain(conn, _reject(conn, "ev_sunburn_reload"))
    # crowd + budget are the two dominant, headline-leading receipts
    assert ex.receipts[0].factor == "crowd"
    assert "budget" in {r.factor for r in ex.receipts[:3]}


def test_explanation_is_data_driven_not_templated():
    conn = _load()
    before = explain.explain(conn, _reject(conn, "ev_sunburn_reload"))
    crowd_before = next(r for r in before.receipts if r.factor == "crowd")
    assert any("2/5" in e for e in crowd_before.evidence)

    # Rewrite history: the user now LOVED that massive night (5/5).
    conn.execute("UPDATE outings SET rating = 5 WHERE event_id = 'ev_past_sunburn_arena'")
    conn.commit()

    after = explain.explain(conn, _reject(conn, "ev_sunburn_reload"))
    crowd_after = next(r for r in after.receipts if r.factor == "crowd")
    # the 2/5 receipt for Sunburn Arena is gone — evidence tracks the DB, not a template
    assert not any("Sunburn Arena" in e and "2/5" in e for e in crowd_after.evidence)
    conn.close()


def test_hard_no_has_its_own_explanation():
    conn = _load()
    ex = explain.explain(conn, _reject(conn, "ev_privee_bollywood"))
    assert ex.hard_no == "bollywood_night"
    assert "dealbreaker" in ex.headline()
    conn.close()
