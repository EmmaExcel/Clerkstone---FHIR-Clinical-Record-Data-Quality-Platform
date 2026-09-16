# Java 17 is keg-only under Homebrew; expose it for Synthea / the validator.
JAVA_HOME ?= /opt/homebrew/opt/openjdk@17
export JAVA_HOME
export PATH := $(JAVA_HOME)/bin:$(PATH)

PYTHON ?= uv run python
UV ?= uv
DC ?= docker compose

.PHONY: help dev test lint type synth corrupt load migrate run rebuild-projections verify-audit check-secrets demo up down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies (uv sync)
	$(UV) sync

up: ## Start infrastructure (Postgres) via docker compose
	$(DC) up -d db

down: ## Stop docker compose services
	$(DC) down

dev: ## Run the API in development mode
	$(UV) run uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000

run: dev ## Alias for dev

migrate: ## Apply Alembic migrations
	cd backend && $(UV) run alembic upgrade head

synth: ## Generate the synthetic dataset (Synthea -> UK-ised FHIR bundles)
	$(UV) run python scripts/synthesise.py

corrupt: ## Apply the deterministic defect-corruption harness
	$(UV) run python scripts/corrupt.py

load: ## Load generated fixtures into the API/DB
	$(UV) run python scripts/load.py

rebuild-projections: ## Rebuild relational projections from FHIR resources
	$(UV) run python scripts/rebuild_projections.py

verify-audit: ## Verify the audit-log hash chain integrity
	$(UV) run python scripts/verify_audit.py

test: ## Run the backend test suite
	$(UV) run pytest -q

test-cov: ## Run tests with coverage
	$(UV) run pytest --cov=app --cov-report=term-missing

lint: ## Run ruff
	$(UV) run ruff check backend scripts

type: ## Run mypy
	$(UV) run mypy backend/app

check-secrets: ## Scan for committed secrets (gitleaks)
	gitleaks detect --source . --no-banner

demo: synth corrupt load ## One-shot: build dataset and load it
