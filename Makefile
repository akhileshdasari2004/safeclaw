.PHONY: help install dev backend-dev backend-test migrate seed docker-up docker-down lint

help:
	@echo "SafeClaw — available targets:"
	@echo "  make install      Install all dependencies"
	@echo "  make dev          Run frontend + backend (requires docker-up)"
	@echo "  make backend-dev  Run FastAPI with reload"
	@echo "  make backend-test Run pytest"
	@echo "  make migrate      Run Alembic migrations"
	@echo "  make seed         Seed development data"
	@echo "  make docker-up    Start Postgres + services"
	@echo "  make docker-down  Stop Docker services"
	@echo "  make lint         Lint backend + frontend"

install:
	npm install
	cd apps/backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt

dev:
	npm run dev

backend-dev:
	cd apps/backend && . .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backend-test:
	cd apps/backend && . .venv/bin/activate && pytest -v

migrate:
	cd apps/backend && . .venv/bin/activate && alembic upgrade head

seed:
	cd apps/backend && . .venv/bin/activate && python scripts/seed.py

docker-up:
	docker compose -f infrastructure/docker/docker-compose.yml up -d

docker-down:
	docker compose -f infrastructure/docker/docker-compose.yml down

lint:
	cd apps/backend && . .venv/bin/activate && ruff check app tests && mypy app --ignore-missing-imports
	npm run lint -w @safeclaw/frontend
