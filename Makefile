<<<<<<< HEAD
# Maitre & Delphi — demo entrypoints. No API keys, no network, ~60s each.
# Override the interpreter if `python` is not Python 3.11+:  make demo-maitre PYTHON=python3
PYTHON ?= python

.PHONY: demo-maitre demo-delphi test test-maitre test-delphi help

help:
	@echo "make demo-maitre   # taste-graph concierge: rejects the trending event with receipts"
	@echo "make demo-delphi   # prediction-market intern (lives on the delphi branch)"
	@echo "make test          # run all smoke tests"

demo-maitre:
	$(PYTHON) -m demo.demo_maitre

demo-delphi:
	@if [ -f demo/demo_delphi.py ]; then \
		$(PYTHON) -m demo.demo_delphi; \
	elif [ -d delphi ]; then \
		$(PYTHON) -m delphi.loader; \
		echo "(delphi demo script not on this branch — ran the loader as a smoke check)"; \
	else \
		echo "delphi is built on the 'delphi' branch; check it out to run this demo."; \
	fi

test: test-maitre test-delphi

test-maitre:
	$(PYTHON) -m pytest maitre/tests -q

test-delphi:
	@if [ -d delphi/tests ]; then \
		$(PYTHON) -m pytest delphi/tests -q; \
	else \
		echo "delphi tests live on the 'delphi' branch — skipping."; \
	fi
=======
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
>>>>>>> delphi
