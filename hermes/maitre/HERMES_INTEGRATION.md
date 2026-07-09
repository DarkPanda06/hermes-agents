# HERMES_INTEGRATION.md — Maitre on the Hermes Agent runtime

This directory holds the Hermes-native artifacts for Maitre: four **skill manifests**
(agentskills.io `SKILL.md` format) and a **cron config**. `hermes-agent` was not
installed during the build (per CLAUDE.md: don't burn the night fighting an install),
so the same logic ships as plain, tested Python modules under `maitre/`. This doc is
the mapping between the two — every skill points at the module that implements it.

## The spine
`cron ingestion → subagents (skills) → durable memory → transparent judgment with receipts`

```
                    ┌─────────────────────────── Hermes durable memory ───────────────────────────┐
                    │  events   taste_profile   outings   decisions        (SQLite in the demo)    │
                    └──────────────────────────────────────────────────────────────────────────────┘
   cron 03:00 ─▶ taste-intake ─▶ events ─▶ fit-scorer ─▶ decisions ─▶ plan-composer ─▶ Telegram/Calendar
                     ▲                          │                           
   user review ─▶ feedback-loop ──▶ taste_profile (weights move) ──────────┘  (compounds next scan)
```

## Skill → module map
| Hermes skill (`skills/<name>/SKILL.md`) | Implemented by | Durable memory touched |
|---|---|---|
| `taste-intake`  | `maitre/loader.py`, `maitre/scripts/extract_flyer.py` | writes `events`, `taste_profile` |
| `fit-scorer`    | `maitre/fit.py`, `maitre/explain.py`                  | writes `decisions`; reads `outings`, `taste_profile` |
| `plan-composer` | `maitre/notify.py`                                    | reads `events`, `taste_profile` |
| `feedback-loop` | `maitre/feedback.py`                                  | writes `taste_profile`, `outings` |

## Cron → job map (`cron/nightly-ingest.yaml`)
| Job | Schedule | Skill | Effect |
|---|---|---|---|
| `nightly-ingest`   | 03:00 daily | taste-intake | ingest + OCR into `events` |
| `nightly-prescore` | 03:15 daily | fit-scorer   | pre-compute `decisions` (instant morning digest) |
| `weekly-digest`    | Sat 10:00   | plan-composer | deliver the weekend top-3 |

## Memory-tool mapping
The four SQLite tables are the demo stand-in for Hermes' durable memory tool:
- **`taste_profile`** — the compounding graph. This is the "memory" that makes the
  agent sharper over time; `feedback-loop` writes here.
- **`outings`** — rated history. The rejection explainer *cites* these rows, so the
  "why not" is grounded in the user's own past, not a template.
- **`decisions`** — every verdict + its reasons, so "why isn't X on my list?" is
  answerable long after the scan.
- **`events`** — the ingested inventory.

## If/when `hermes-agent` is installed
1. Register each `skills/<name>/` directory with the Hermes skill loader.
2. Point the memory tool at the four tables (or migrate them to Hermes' store).
3. Load `cron/nightly-ingest.yaml` into the Hermes scheduler.
No business logic changes — the Python modules already express the exact behaviour
each manifest describes.
