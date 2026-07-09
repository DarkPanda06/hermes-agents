---
name: plan-composer
description: >
  Turn a surfaced-and-chosen event into an actionable plan: a Telegram-style
  confirmation, a calendar hold, and a logistics packet (leave-by time, travel,
  budget note, table hold). Use when the user books one of the surfaced options.
license: MIT
metadata:
  runtime: hermes-agent
  implementation: maitre/notify.py
  memory: events (read), taste_profile (read)
---

# Plan Composer

## When to use
- The user books one of the surfaced options ("book option 1").

## Inputs
- The chosen `event` row and the `taste_profile` (home_area, budget cap).

## Outputs (payloads, not live sends in the demo)
- **Telegram confirmation** — Markdown message with venue/time/price/link.
- **Calendar hold** — ICS-shaped payload (summary, dtstart/dtend, location).
- **Logistics packet** — leave-by time, cab estimate from home_area, doors,
  budget note vs the monthly cap, table-hold guidance.

## Hermes mapping
- Tools in production: Telegram send, Google/CalDAV calendar insert. In the demo
  these are printed as the exact payloads that WOULD be sent (no network).
- Durable memory: reads `events`/`taste_profile`; writes nothing (idempotent).
