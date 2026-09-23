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

# Day 02 is opt-in; host/cluster acceptance is separate from default CI.
.PHONY: tools-day2 test-day2 test-day2-live test-day2-host
tools-day2: tools
	$(NPM) ci --prefix tools/mcp/day2 --ignore-scripts
	$(PYTHON) tools/mcp/day2/install.py
test-day2:
	$(PYTHON) -m unittest discover -s tests/milestones/day2 -v
	$(PYTHON) -m ruff check tools/mcp/day2 tests/milestones/day2
	$(PYTHON) -m ruff format --check tools/mcp/day2 tests/milestones/day2
test-day2-live:
	$(PYTHON) tests/milestones/day2/live_check.py
test-day2-host:
	$(PYTHON) tools/mcp/day2/host_check.py

# Day 03 is local-first. Cloud plan/apply requires the reviewed AWS inputs in docs/day3/Runbook.md.
.PHONY: tools-day3 fmt-day3 validate-day3 lint-day3 security-day3 policy-day3 helm-day3 test-day3 day3-local-up day3-local-status day3-local-down
tools-day3:
	$(PYTHON) tools/iac/install.py
fmt-day3:
	terraform fmt -check -recursive infra
validate-day3:
	terraform -chdir=infra init -backend=false -input=false
	terraform -chdir=infra validate -no-color
	terraform -chdir=infra/bootstrap init -backend=false -input=false
	terraform -chdir=infra/bootstrap validate -no-color
	terraform -chdir=infra/platform init -backend=false -input=false
	terraform -chdir=infra/platform validate -no-color
	terraform -chdir=infra/edge init -backend=false -input=false
	terraform -chdir=infra/edge validate -no-color
lint-day3:
	tmp/day3/bin/tflint --chdir=infra --init
	tmp/day3/bin/tflint --chdir=infra --recursive
security-day3:
	tmp/day3/bin/checkov -d infra --quiet --compact
policy-day3:
	tmp/day3/venv/bin/pytest tests/milestones/day3/test_policy.py -v -p no:cacheprovider
helm-day3:
	helm lint deploy/helm/insighthub -f deploy/helm/insighthub/values-local.yaml
	helm template insighthub deploy/helm/insighthub -f deploy/helm/insighthub/values-local.yaml >/dev/null
test-day3: fmt-day3 validate-day3 lint-day3 security-day3 policy-day3 helm-day3
	tmp/day3/venv/bin/pytest tests/milestones/day3 -v -p no:cacheprovider
day3-local-up:
	$(PYTHON) tools/iac/local_lab.py up
day3-local-status:
	$(PYTHON) tools/iac/local_lab.py status
day3-local-down:
	$(PYTHON) tools/iac/local_lab.py down
