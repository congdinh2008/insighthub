COMPOSE ?= docker compose
PYTHON ?= python3
NPM ?= npm
NODE ?= node
API_URL ?= http://localhost:8000
WEB_URL ?= http://localhost:3000
COMPOSE_PROJECT_NAME ?= insighthub-do2603
TEST_IMAGE ?= $(COMPOSE_PROJECT_NAME)-tests:day1
TEST_DATABASE_URL ?= postgresql://insighthub:insighthub@postgres:5432/insighthub
export COMPOSE_PROJECT_NAME
TEST_RUN = docker run --rm --network $(COMPOSE_PROJECT_NAME)_default -v "$(CURDIR):/workspace:ro" -w /workspace -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/workspace/api:/workspace/api/tests:/workspace/ingestion-worker -e RAG_MODE=fixture -e LLM_PROVIDER=fixture -e EMBEDDING_PROVIDER=fixture -e DATABASE_URL="$(TEST_DATABASE_URL)" -e REDIS_URL=redis://redis:6379/0 -e RUN_DB_TESTS=1 -e TEST_SCHEMA_PATH=/workspace/infra/db/init.sql $(TEST_IMAGE)

.PHONY: up down build test-image test test-backend test-worker test-day1 test-verifiers test-mcp smoke tools lint typecheck ci
up:
	$(COMPOSE) up --build -d --wait
down:
	$(COMPOSE) --profile ollama down
build:
	$(COMPOSE) build
test-image:
	docker build --target test -f ingestion-worker/Dockerfile -t $(TEST_IMAGE) .
test-backend:
	$(TEST_RUN) python -m pytest api/tests -xvs -p no:cacheprovider
test-worker:
	$(TEST_RUN) python -m pytest ingestion-worker/tests -v -p no:cacheprovider
test-day1:
	INSIGHTHUB_API_URL="$(API_URL)" INSIGHTHUB_WEB_URL="$(WEB_URL)" $(PYTHON) -m pytest tests/milestones/day1 -v -p no:cacheprovider
test-verifiers:
	$(PYTHON) -m unittest discover -s tests -p 'test_verify*.py' -v
tools:
	$(NPM) ci --prefix tools/mcp --ignore-scripts
test-mcp:
	$(NPM) --prefix tools/mcp test
	$(NODE) tools/mcp/smoke.mjs
smoke:
	$(PYTHON) scripts/verify.py smoke --api-url "$(API_URL)" --web-url "$(WEB_URL)"
lint:
	$(PYTHON) -m ruff check api/app ingestion-worker/worker.py ingestion-worker/tests tests/milestones/day1
	$(PYTHON) -m ruff format --check api/app ingestion-worker/worker.py ingestion-worker/tests tests/milestones/day1
typecheck:
	$(PYTHON) -m mypy --strict api/app ingestion-worker/worker.py
test: test-verifiers test-backend test-worker test-day1 test-mcp
ci:
	$(MAKE) up
	$(MAKE) test-image
	$(MAKE) test
	$(MAKE) lint typecheck smoke
