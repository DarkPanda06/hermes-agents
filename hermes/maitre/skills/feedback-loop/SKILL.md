---
name: feedback-loop
description: >
  Apply a rated outing back into the taste graph — reinforce matched genre/vibe
  affinities on a good review and nudge crowd_tolerance on a run of good nights —
  then report the weight deltas. Use after the user reviews an event they attended.
license: MIT
metadata:
  runtime: hermes-agent
  implementation: maitre/feedback.py
  memory: taste_profile (write), outings (write), decisions (re-derived)
---

# Feedback Loop

## When to use
- The user reviews an outing ("last night was 5/5" / "2/5, too loud").

## Behaviour
1. Persist the outing (rating, vibe_match, would_repeat, notes) — durable history
   the explainer will later cite.
2. On a strong review (>= 4): boost the matched genre & vibe affinities toward 1.0
   by a fraction of the remaining headroom; nudge `crowd_tolerance` up a capped
   amount (never into "massive-friendly" territory).
3. Emit the deltas (e.g. `genre·jazz 0.92 → 0.95`, `crowd_tolerance 0.20 → 0.26`).

## Outputs
- Mutated `taste_profile`; a new `outings` row; a human-readable delta list.
- Downstream effect: a previously-borderline event can now cross the bar — the
  compounding proof.

## Hermes mapping
- Durable memory writes to `taste_profile` and `outings` — this is where the agent
  "gets sharper after every outing".
