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
