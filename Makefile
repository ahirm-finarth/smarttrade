PY := backend/.venv/bin/python
RUFF := backend/.venv/bin/ruff
ALEMBIC := backend/.venv/bin/alembic -c backend/alembic.ini
SOURCE ?= data/raw

.PHONY: setup setup-backend setup-frontend backend frontend migrate seed check-db check-llm test test-mysql test-e2e lint typecheck build format secrets

setup: setup-backend setup-frontend

setup-backend:
	uv sync --project backend --extra dev --frozen

setup-frontend:
	npm ci --prefix frontend

backend:
	backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

frontend:
	npm --prefix frontend run dev

migrate:
	$(ALEMBIC) upgrade head

seed:
	$(PY) -m app.scripts.seed_demo_data --source "$(SOURCE)"

check-db:
	$(PY) -m app.scripts.check_db

check-llm:
	$(PY) -m app.scripts.check_llm

test:
	backend/.venv/bin/pytest backend/tests

test-mysql:
	SMART_TRADE_MYSQL_TESTS=1 backend/.venv/bin/pytest backend/tests

test-e2e:
	npm --prefix frontend run test:e2e

lint:
	$(RUFF) check backend scripts
	$(RUFF) format --check backend scripts
	npm --prefix frontend run lint

typecheck:
	npm --prefix frontend run typecheck

build:
	npm --prefix frontend run build

format:
	$(RUFF) format backend
	npm --prefix frontend run format

secrets:
	python3 scripts/check_secrets.py

.PHONY: register-demo-documents process-demo-documents evaluate-demo-extraction

register-demo-documents:
	$(PY) -m app.scripts.register_demo_documents

process-demo-documents:
	$(PY) -m app.scripts.process_demo_documents

evaluate-demo-extraction:
	$(PY) -m app.scripts.evaluate_demo_extraction --output reports/local/phase2-evaluation.json

.PHONY: examine-demo-cases evaluate-demo-examination
examine-demo-cases:
	$(PY) -m app.scripts.examine_demo_cases

evaluate-demo-examination:
	$(PY) -m app.scripts.evaluate_demo_examination --output reports/local/phase3-evaluation.json

.PHONY: run-demo-risk evaluate-demo-risk
run-demo-risk:
	$(PY) -m app.scripts.run_demo_risk

evaluate-demo-risk:
	$(PY) -m app.scripts.evaluate_demo_risk --output reports/local/phase4-risk-evaluation.json
