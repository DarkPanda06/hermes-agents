# CLAUDE.md — Rules of Engagement (READ FIRST, EVERY SESSION)

You are building a hackathon-application monorepo containing TWO demo agents on the
Hermes Agent (Nous Research) runtime. Deadline: tomorrow morning. A reviewer will
spend ~90 seconds here. Optimize for DEMO-READY, not feature-complete.

## Prime directives (in priority order)
1. **A runnable demo beats everything.** `make demo-maitre` and `make demo-delphi`
   must run, deterministically, with ZERO API keys, against seeded local data.
2. **Applause moments first.** Build in the exact task order in each BUILD_PLAN.md.
   If time runs out, later tasks are stubs — that is acceptable and expected.
3. **Never fake data silently.** Seeded/cached data is fine and labeled as such.
   Stubbed features must be listed in README "What's real vs. stubbed".
4. **Hermes-native where cheap, graceful fallback where not.** Prefer real Hermes
   Agent skill manifests (agentskills.io format), Hermes cron configs, and Hermes
   memory-tool usage. BUT: if hermes-agent install/integration blocks you for more
   than 30 minutes, implement the same logic as plain Python modules with a
   `hermes/` directory containing the skill manifests + a HERMES_INTEGRATION.md
   explaining the mapping. Do not burn the night fighting an install.
5. **Commit after every completed task** with message `[maitre|delphi|core] task N: <name>`.
   Working tree must never be >1 task away from a green demo.

## Repo structure (create exactly this)
```
├── CLAUDE.md
├── README.md                  (fill from README_SKELETON.md at the END)
├── Makefile                   (demo-maitre, demo-delphi, test)
├── core/                      (shared: sqlite helpers, schemas, alert formatting)
├── maitre/                    (see maitre/BUILD_PLAN.md)
├── delphi/                    (see delphi/BUILD_PLAN.md)
├── demo/                      (demo entrypoints, scripted deterministic runs)
└── hermes/                    (skill manifests, cron configs, integration notes)
```

## Hard constraints
- Python 3.11+, stdlib + minimal deps (requests, rich, pydantic ok). SQLite only.
- No network calls inside `make demo-*`. Fetch scripts that hit real APIs live in
  `scripts/fetch_*.py`, are run manually, and cache JSON into `*/data/`.
- Every agent decision must print its REASONING (the "why"/"why not" strings are
  the product, not decoration).
- Output formatting: use `rich` for terminal demo output — the demo IS the terminal.
- Tests: one smoke test per applause moment (rejection fires; arb math correct on
  a known fixture; bot-doctor repairs the broken parser fixture). `make test` green.

## What NOT to do
- No web UI. No Docker. No auth. No live Telegram bot (print the message payloads
  that WOULD be sent, formatted as Telegram-style messages).
- No speculative features from the PRDs (group mode, execution, payments, v2 anything).
- Do not refactor working code near the end of the run. Freeze and polish README.

## Definition of done (check before stopping)
- [ ] `make demo-maitre` runs clean start-to-finish (< 60s)
- [ ] `make demo-delphi` runs clean start-to-finish (< 60s)
- [ ] `make test` green
- [ ] README.md filled from skeleton incl. real vs. stubbed section
- [ ] hermes/ contains skill manifests + cron configs (real or mapping doc)
