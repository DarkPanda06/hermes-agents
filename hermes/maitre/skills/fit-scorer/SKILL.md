---
name: fit-scorer
description: >
  Score each candidate event against the user's taste graph with a transparent
  weighted model, decide surface vs reject, and — on reject — produce a "why not"
  grounded in the user's own history. Use whenever the user asks "what's on?" or a
  new event is ingested.
license: MIT
metadata:
  runtime: hermes-agent
  implementation: maitre/fit.py, maitre/explain.py
  memory: decisions (durable), outings (read), taste_profile (read)
---

# Fit Scorer

## When to use
- The user asks "Saturday night?" / "what's on this week?".
- A newly-ingested event needs a keep/drop decision.
- The user asks "why isn't <event> on my list?" → run the explainer path.

## Model (transparent, auditable)
```
fit =  w·genre_affinity + w·vibe_match + w·budget_fit + w·logistics
     − w·crowd_penalty − w·fatigue
```
Each component returns a number AND a human reason string. A `hard_no` tag
short-circuits to reject. Verdict = `surface` if fit > threshold else `reject`.

## Inputs
- Candidate `events`, the `taste_profile`, and the user's rated `outings`.

## Outputs
- A `decisions` row per event (fit_score, verdict, full reasons JSON).
- For rejects: a data-driven explanation citing the profile values and the past
  outing ratings that drove each negative component (never a hardcoded template).

## Hermes mapping
- Durable memory: `decisions` (so "why" is answerable later), `outings` (history
  the explainer cites), `taste_profile` (weights).
- No external tools required — pure judgment over memory.
