# Ingestion worker

`POST /documents` validates the upload envelope, commits a pending document with
its payload digest/pipeline identity, enqueues an ARQ job and returns HTTP 202.
`worker.process_document` runs the shared atomic extract/chunk/embed/pgvector
pipeline in a thread, then emits a JSON `ingestion_completed` event.
The shared implementation remains in `api/app/services/ingestion.py` so worker,
retrieval and regression tests use the same settings and vector validation.

## Run

From the repository root:

```sh
docker compose up --build -d --wait
docker compose logs ingestion-worker
curl -sS -w '\nHTTP %{http_code}; upload %{time_total}s\n' -F 'file=@sample-docs/so-tay-van-hanh.md' http://localhost:8000/documents
curl -sS http://localhost:8000/documents
```

Poll the returned document ID until ready/failed, with a 30-second deadline.
Measure acceptance below one second on the fixed local fixture workload; real
provider latency is a separate measurement. `make smoke` verifies upload/chat.

API and worker inherit the same Compose environment (including
`REDIS_URL=redis://redis:6379` and all embedding settings). The worker image uses
Python 3.12 and the shared hashed API requirements, including psycopg 3 rather
than introducing a second driver. Its build context is the repository root.

## Retry and failure contract

- Four attempts total: initial execution plus three retries delayed 1, 2, 4 seconds.
- Retryable provider/internal failures leave status pending and zero chunks.
- Success atomically sets ready, chunk_count and clears error_code.
- Invalid content fails without retry; exhaustion records failed and a safe code.
- Repeated processing of the same ID/bytes/pipeline is a no-op after success.
- Changed payload/pipeline or deleted IDs are rejected without overwriting data.
- Empty files and invalid upload envelopes still fail immediately (400/413/422).
  Invalid extracted text/provider failures after acceptance appear in GET /documents.
- Redis enqueue failure returns queue_unavailable/503 and marks pending metadata
  failed when DB is reachable; an ambiguous timeout never overwrites ready data.
- Redis uses AOF with appendfsync always and a persistent volume. Jobs retain bytes
  for at most seven days until execution. ARQ argument/result logging is disabled;
  application logs include IDs, attempts and safe codes only.
- PostgreSQL and Redis do not share a transaction: process death between DB commit
  and enqueue can leave pending metadata; queue expiry or a prolonged DB outage
  also needs operator reconciliation. This refactor does not claim an outbox or
  guaranteed recovery across that gap, and does not change the DB schema.

## Tests

`make test-backend` runs unittest with PostgreSQL and Redis running, mounting the
worker source. Integration tests own a random DB schema and unique Redis queue;
no production schema is truncated and no real AI provider is billed.

Local unit checks after installing API requirements and pytest:

```sh
python -m pytest api/tests/ -xvs
```

For the complete suite set RUN_DB_TESTS=1, TEST_DATABASE_URL and REDIS_URL to lab
services and keep both API and worker on PYTHONPATH (pytest.ini handles source
paths from the root). Database tests are opt-in; skipped tests are not evidence
of successful integration. The same suite includes real Redis/ARQ execution,
retry exhaustion/recovery, atomicity, identity conflicts and chat regression.

`python scripts/verify.py day1 --evidence-dir evidence` remains a separate partial
milestone verifier and requires the additional artifacts described in
`scripts/VERIFICATION_CONTRACT.md`.
