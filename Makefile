# Delphi (delphi branch) — required entrypoints. All substantive code lives under delphi/.
# Windows note: if `make` is absent, use `mingw32-make` (msys2) or run the
# `python -m ...` commands directly (shown per target).

PY ?= python

.PHONY: demo-delphi demo-maitre test load fetch help

help:
	@echo "make demo-delphi   # deterministic offline demo (<60s)"
	@echo "make test          # run the applause-moment smoke tests"
	@echo "make load          # (re)build delphi/data/delphi.db from fixtures"

## Deterministic, offline, zero-API-key demo.  ->  python -m delphi.demo.demo_delphi
demo-delphi:
	$(PY) -m delphi.demo.demo_delphi

## Maitre lives on the `maitre` branch (this is the delphi worktree).
demo-maitre:
	@echo "demo-maitre lives on the 'maitre' branch / worktree — not built on 'delphi'."

## Applause-moment smoke tests.  ->  python -m pytest delphi/tests
test:
	$(PY) -m pytest delphi/tests -q

## Rebuild the SQLite DB from the committed fixtures.
load:
	$(PY) -m delphi.loader

## Manual, network-only cache refresh (NOT used by the demo).
fetch:
	$(PY) -m delphi.scripts.fetch_polymarket
	$(PY) -m delphi.scripts.fetch_kalshi
