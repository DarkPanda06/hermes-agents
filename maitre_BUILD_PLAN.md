# maitre/BUILD_PLAN.md — Taste-Graph Concierge (demo cut)

Applause moment: **the agent rejects the trending event and explains why in the
user's own history.** Task order guarantees this exists even if the run dies early.

## Data model (SQLite: maitre/data/maitre.db)
- `events(id, title, venue, area, dt, price_min, price_max, genre_tags, vibe_tags,
  capacity_class[intimate|mid|massive], source, url)`
- `taste_profile(key, value)` — flat key/value: budget_cap_month, crowd_tolerance,
  genre_affinities (json), vibe_affinities (json), energy_by_day (json), hard_nos (json)
- `outings(id, event_id, rating, vibe_match, would_repeat, notes, ts)`
- `decisions(id, event_id, fit_score, verdict[surface|reject], reasons_json, ts)`

## Tasks (in order — commit after each)

### Task 1: Seed data
`maitre/data/seed_events.json` — 40 plausible Delhi-NCR events across genres
(jazz/listening bars, techno, comedy, supper clubs, big-format EDM, gallery nights,
runs/treks). MUST include one obviously "trending" big-format event (massive,
expensive, EDM) that the demo persona will hate. Include realistic venues
(Piano Man, auro, Summerhouse, Depot48-style). Loader script → SQLite.
ALSO seed a demo taste profile: loves intimate/seated/jazz-adjacent, crowd_tolerance
low, budget cap ₹1500, rated two past big-format nights 2/5 (seed 5 past outings).

### Task 2: Fit scorer (the core)
`maitre/fit.py` — transparent weighted score:
fit = w·genre_affinity + w·vibe_match + w·budget_fit + w·logistics − w·crowd_penalty − w·fatigue
Each component returns (score_component, human_reason_string). Verdict threshold.
Every scored event writes a `decisions` row with reasons. Unit test on fixtures.

### Task 3: Rejection explainer  ← APPLAUSE MOMENT
`maitre/explain.py` — given a rejected event, generate the "why not" citing the
user's OWN history: pull the past outing ratings + profile values that drove the
negative components. Output like:
"Rejected <trending event>: 3,000+ capacity (your crowd tolerance: low — you rated
Sunburn Arena 2/5 in Jan), ₹4,000 entry vs your ₹1,500/month cap. Override?"
This must be data-driven from the DB, not a template with hardcoded facts.

### Task 4: Digest composer + demo script
`demo/demo_maitre.py` — deterministic run:
1. "Saturday night?" → scans all events, prints "scanned 40 events → surfaced 3,
   rejected 37" with top-3 cards (fit %, one-line why).
2. Asks the planted question: "why isn't <trending event> listed?" → prints Task-3
   rejection with receipts.
3. User "books" option 1 → prints Telegram-style confirmation + calendar-hold +
   logistics packet payloads.

### Task 5: Feedback loop (compounding proof)
`maitre/feedback.py` — apply a 5/5 review of the booked event → mutate profile
weights (print the delta: "intimate-venue affinity 0.72 → 0.79"). Demo then
re-runs "next Saturday?" and a previously-borderline event now surfaces, agent
explains the shift. This closes the demo.

### Task 6 (only if time): Flyer→event extraction showcase
`scripts/extract_flyer.py` — takes an image path, but for demo purposes include one
pre-extracted example: `data/flyer_example.png` note + resulting JSON, shown in
README as the T2-ingestion proof. Do NOT integrate live OCR; a documented example
with the extraction prompt is enough.

### Task 7: Hermes mapping
`hermes/maitre/` — skill manifests for taste-intake, fit-scorer, plan-composer,
feedback-loop; cron config for nightly ingest. Real if hermes-agent installed,
else manifests + HERMES_INTEGRATION.md mapping doc.
