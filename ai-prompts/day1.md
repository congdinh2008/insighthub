# Day 1 AI Prompt Log

## Prompt 1 — Inspect and plan

Read the current ingestion flow and propose a v0 to v1 refactor using ARQ and
Redis. Identify the files to change, data flow, retry behavior, and risks before
editing any files.

Review: The plan must preserve the database schema and reuse the existing
`process_document()` pipeline.

## Prompt 2 — Implement the worker

Implement the approved plan. Create an ARQ worker with `tasks.py` and
`settings.py`, use `REDIS_URL`, and run the existing document processing in the
worker. Keep the API and worker independently scalable.

Review: Worker failures must mark the document as `failed` and allow ARQ to
retry the job. Do not use `pickle` or add a second chunking/embedding pipeline.

## Prompt 3 — Verify the async contract

Review the diff against the Day 1 acceptance criteria. Verify that upload stores
metadata, enqueues `ingest_document`, returns HTTP 202 quickly, and that the
worker eventually changes the document status to `ready`. List any remaining
risks before running tests.

Review: Run compile checks, Docker Compose validation, and the Day 1 verification
script before declaring the refactor complete.