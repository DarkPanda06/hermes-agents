---
name: taste-intake
description: >
  Ingest events from listings, Instagram flyers, and WhatsApp forwards into the
  canonical event schema, and maintain the user's taste_profile. Use nightly (via
  cron) or on-demand when the user forwards a flyer.
license: MIT
metadata:
  runtime: hermes-agent
  implementation: maitre/loader.py, maitre/scripts/extract_flyer.py
  memory: taste_profile (durable), events (durable)
---

# Taste Intake

## When to use
- The nightly ingest cron fires (`hermes/maitre/cron/nightly-ingest.yaml`).
- The user forwards a flyer image or a WhatsApp text blob.
- The user updates a preference ("I'm broke this month", "no more warehouse parties").

## Inputs
- Raw listings JSON, flyer images, or forwarded text.
- The current `taste_profile` (Hermes durable memory).

## Behaviour
1. For images/forwards, call the vision extraction prompt in
   `maitre/scripts/extract_flyer.py` → one event per flyer in the canonical schema
   (`id, title, venue, area, dt, price_min, price_max, genre_tags, vibe_tags,
   capacity_class, source, url`).
2. Upsert events into the `events` store (dedupe on `id`).
3. Apply any explicit profile edits to `taste_profile` (budget_cap_month,
   crowd_tolerance, hard_nos, affinities).

## Outputs
- New/updated `events` rows.
- Updated `taste_profile`.

## Hermes mapping
- Durable memory: `events`, `taste_profile` tables (SQLite in the demo; Hermes
  memory tool in production).
- Tools: a vision tool for flyer OCR; a fetch tool for listings (see
  `scripts/fetch_*.py`, run out-of-band, never inside the demo).
