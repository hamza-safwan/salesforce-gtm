PYTHON ?= .venv/Scripts/python.exe

.PHONY: test lint generate db-up db-init
test:
	$(PYTHON) -m pytest -m "not integration"
lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
generate:
	$(PYTHON) -m gtmdq.cli generate
db-up:
	docker compose up -d --wait
db-init:
	$(PYTHON) -m gtmdq.cli db-init
