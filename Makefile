.PHONY: help install db-start db-reset db-stop seed api web test test-offline lint format types audit eval check

PYTHON ?= python

help:
	@echo "install       Install backend dependencies, including dev tools"
	@echo "db-start      Start local Supabase and apply migrations"
	@echo "db-reset      Rebuild the local database from zero"
	@echo "seed          Load demo data into the database in DATABASE_URL"
	@echo "api           Run the API with reload on port 8000"
	@echo "web           Run the web app on port 5173"
	@echo "test          Run every backend test (needs local Supabase)"
	@echo "test-offline  Run the tests that need no database"
	@echo "lint          Check lint and formatting"
	@echo "format        Apply formatting"
	@echo "types         Run mypy"
	@echo "audit         Check dependencies for known vulnerabilities"
	@echo "check         Run lint, types, tests and audit"

install:
	$(PYTHON) -m pip install -r backend/requirements-dev.txt

db-start:
	npx supabase@latest start -x studio,imgproxy,vector,logflare,mailpit,realtime,edge-runtime,postgres-meta,supavisor

db-reset:
	npx supabase@latest db reset

db-stop:
	npx supabase@latest stop

seed:
	$(PYTHON) backend/scripts/seed.py

api:
	cd backend && $(PYTHON) -m uvicorn app.main:app --reload --port 8000

web:
	cd web && npm run dev

test:
	cd backend && $(PYTHON) -m pytest tests -q --cov=app --cov-report=term

test-offline:
	cd backend && $(PYTHON) -m pytest tests -q -m "not integration"

lint:
	ruff check backend
	ruff format --check backend

format:
	ruff format backend
	ruff check --fix backend

types:
	cd backend && mypy app

audit:
	pip-audit -r backend/requirements.txt

check: lint types test audit
