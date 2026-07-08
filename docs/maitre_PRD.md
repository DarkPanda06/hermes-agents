# PRD — Maitre, the taste-graph concierge

## Problem
Event discovery is optimized for the venue, not the person. Feeds surface what's
*trending* (big, loud, sponsored), which is precisely what a person with specific
taste wants least. The user does the filtering — scrolling, discarding, second-
guessing — and still ends up at the wrong ₹4,000 night. The scarce resource isn't
listings; it's *judgment about this specific person*.

## Thesis
**The valuable agent is the one that says no** — and can defend the "no" in the
user's own history. A concierge that rejects 90% of what's out there, with reasons
you recognize as yours, earns the trust to book the other 10% unattended.

## Users
A person with legible, non-mainstream taste (the demo persona: loves intimate,
seated, jazz-adjacent rooms; low crowd tolerance; ₹1,500/month going-out budget).
The sharper their taste, the worse generic feeds serve them, the more they need this.

## What it does
1. **Ingests** events from listings, Instagram flyers, and WhatsApp forwards into
   one schema (nightly cron; flyers via a vision extraction prompt).
2. **Scores** each event against a transparent taste graph — genre, vibe, budget,
   logistics, crowd, fatigue — each component carrying a human reason.
3. **Rejects with receipts.** For anything dropped, it explains *why not* by citing
   the profile values and past outing ratings that drove the negative components —
   "3,000-cap room vs your low tolerance (you rated Sunburn Arena 2/5); ₹3,999 vs
   your ₹1,500 cap; EDM affinity 0.08."
4. **Books what survives** — Telegram confirmation, calendar hold, logistics packet.
5. **Compounds.** Every rated outing writes back into the graph. A great intimate
   jazz night raises jazz/listening affinities and nudges crowd tolerance, so a
   borderline mid-size jazz room that was rejected last week now surfaces — and the
   agent says exactly why it changed its mind.

## Why it wins (the moat)
The taste graph is durable, user-specific memory that gets *more* valuable per
outing. Every decision is auditable (persisted with reasons), so the user can
interrogate any "no" and correct it — which itself feeds the graph. Competitors
show you more; Maitre shows you less, and is right about it.

## Non-goals (this cut)
Group planning, payments/ticketing execution, live OCR at scale, social features.
The demo is deliberately single-user, seeded, and deterministic.

## Success metric
**Rejection precision** — of the events Maitre hides, how many would the user have
also rejected? — and its inverse, regret on surfaced events (rated < 3/5). A good
concierge is measured by what it correctly spared you, not by coverage.

## How the demo proves it
`make demo-maitre` scans 40 events → surfaces 3, rejects 37; answers "why isn't
Sunburn Reload listed?" with history-grounded receipts; books the top pick; then a
5/5 review visibly moves the weights and flips a previously-rejected event to
surfaced. All seeded, deterministic, no network. See the repo README for the
real-vs-stubbed breakdown.
