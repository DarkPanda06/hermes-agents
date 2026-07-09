# Hermes Agent integration — Delphi

Delphi's logic is packaged as **Hermes Agent skills** (agentskills.io manifest
format) plus **cron configs** per cadence. Because a live `hermes-agent` install
was out of scope for the demo deadline, this directory follows CLAUDE.md's
**real-or-mapping-doc rule**: the manifests are real and well-formed, and this
document maps each skill 1:1 to the plain-Python module that implements it today.
Nothing here is stubbed logic — it is the *same* code the demo runs, described in
Hermes-native packaging.

## Skill → module mapping

| Hermes skill      | Manifest                          | Python entrypoint                         | Cadence |
|-------------------|-----------------------------------|-------------------------------------------|---------|
| `scanner`         | `skills/scanner/SKILL.md`         | `delphi.loader:load_snapshots`            | 5 min   |
| `arb-partition`   | `skills/arb-partition/SKILL.md`   | `delphi.arb_partition:scan`               | 5 min   |
| `arb-crossvenue`  | `skills/arb-crossvenue/SKILL.md`  | `delphi.arb_crossvenue:scan`              | 15 min  |
| `bot-doctor`      | `skills/bot-doctor/SKILL.md`      | `delphi.bots:heartbeat` + `:repair`       | 10 min  |
| `brief`           | `skills/brief/SKILL.md`           | `delphi.brief:build_brief`                | on-list / daily |

## Memory-tool usage

Delphi persists to a single SQLite file (`delphi/data/delphi.db`, tables
`markets / alerts / ledger / bots`). Under Hermes this maps to the agent
**memory tool**: `markets` and `bots.schema_hash` are the working memory the
scanner/bot-doctor read+write each cadence; `alerts` + `ledger` are the durable
record the `brief`/reporting skills read back (see `ledger.py` — "precision is
measured, not claimed").

## Cron

`cron/delphi.cron` is a standard crontab; `cron/schedule.yaml` is the same
schedule in the Hermes runtime's config shape. Both invoke the skills above at
the cadences in the table. The demo does **not** use cron — it runs the whole
sequence once via `make demo-delphi`.

## What is real vs. mapped

- **Real & runnable today:** every Python entrypoint (tested; see `delphi/tests`).
- **Real manifests:** agentskills.io-format `SKILL.md` + `manifest.yaml` per skill.
- **Mapped (not a live install):** the `hermes-agent` runtime binding. To go live,
  point each manifest's `entrypoint` at the module above and register the cron file.
