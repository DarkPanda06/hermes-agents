"""Smoke test for the feedback loop (Task 5) — the compounding proof.

A 5/5 review of the booked intimate jazz night must (a) move the matched weights,
(b) flip the borderline mid-size jazz event from rejected to surfaced, and
(c) NOT rescue the trending massive EDM event — crowd_tolerance stays 'low'.
"""
from maitre import db, loader, fit, feedback


def _load():
    conn = db.reset(":memory:")
    loader.load_seed(conn)
    return conn


def test_review_moves_the_weights_and_logs_an_outing():
    conn = _load()
    before = db.get_profile(conn)
    deltas = feedback.apply_review(conn, "ev_pianoman_quartet", rating=5, vibe_match=0.96)

    moved = {d.dimension: (d.before, d.after) for d in deltas if d.moved}
    assert "genre · jazz" in moved
    assert moved["genre · jazz"][1] > moved["genre · jazz"][0]
    assert "crowd_tolerance" in moved

    after = db.get_profile(conn)
    assert after["genre_affinities"]["jazz"] > before["genre_affinities"]["jazz"]
    # the outing is persisted (durable memory the explainer can later cite)
    n = conn.execute("SELECT COUNT(*) FROM outings WHERE event_id='ev_pianoman_quartet'").fetchone()[0]
    assert n == 1
    conn.close()


def test_borderline_event_surfaces_after_review():
    conn = _load()
    before = fit.scan(conn, record=False)
    auro_before = next(d for d in before if d.event_id == "ev_auro_revisit")
    assert auro_before.verdict == "reject"          # 57% — just under the bar

    feedback.apply_review(conn, "ev_pianoman_quartet", rating=5, vibe_match=0.96)
    after = fit.scan(conn, record=False)
    auro_after = next(d for d in after if d.event_id == "ev_auro_revisit")

    assert auro_after.verdict == "surface"          # now clears it
    assert auro_after.fit > auro_before.fit
    assert "ev_auro_revisit" in {d.event_id for d in feedback.newly_surfaced(before, after)}
    conn.close()


def test_review_does_not_rescue_the_trending_event():
    conn = _load()
    feedback.apply_review(conn, "ev_pianoman_quartet", rating=5, vibe_match=0.96)
    after = fit.scan(conn, record=False)
    trending = next(d for d in after if d.event_id == "ev_sunburn_reload")
    assert trending.verdict == "reject"
    # crowd_tolerance nudged up but stays firmly 'low'
    prof = db.get_profile(conn)
    assert fit.crowd_tolerance_word(fit.crowd_tolerance_level(prof)) == "low"
    conn.close()


def test_low_rating_does_not_sharpen():
    conn = _load()
    deltas = feedback.apply_review(conn, "ev_pianoman_quartet", rating=2, vibe_match=0.2)
    assert deltas == []   # a bad review logs the outing but moves no weights
    conn.close()
