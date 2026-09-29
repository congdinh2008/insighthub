# Day 06 architecture and decisions

The application keeps its Day 01-05 business pipeline. Day06 adds a LiteLLM gateway, NeMo IORails service, dedicated accounting PostgreSQL, isolated pgvector database, and a sanitized durable audit ledger. The existing schema and 1024-dimensional vector contract are unchanged. The new provider endpoint/revision gets a new index and queue; old data remains in the original PVC.

Provider: ZenLayer AI, OpenAI-compatible endpoint, `gpt-4.1-mini` and `text-embedding-3-large`. Prices were checked in the authenticated ZenLayer model catalog on 2026-09-29 and are recorded in `gateway/pricing.json` with screenshots. They are catalog estimates, not provider billing statements. DeepSeek was unnecessary for the baseline.

Three workload keys separately authorize app chat/embeddings, bot summaries, and bounded coding patches. Two additional service identities authorize the classifier and evaluation. Workload identity comes from authenticated key aliases, never client metadata. Keys cannot administer the gateway. The master and upstream provider keys stay in the gateway infrastructure secret; application workloads get only their scoped virtual key.

Mandatory LiteLLM CustomLogger pre/post hooks enforce policy for every workload request. This replaces the plan's optional CustomGuardrail integration because client-request guard selection must not disable mandatory policy. Streaming, tools and non-text messages are rejected in this baseline. No model owns a shell or the ChatOps executor.

NeMo Guardrails 0.24.1 uses actual IORails regex and model self-check rails. API input is checked before retrieval; every returned chunk is checked before generation and HTTP serialization; output is checked before release. PII/canary patterns are conservative. Unavailable or malformed checks fail closed. The classifier uses a separate restricted gateway key, avoiding recursion while keeping its cost visible.

LiteLLM 1.103.0 maintains persistent native key budgets. Requests have bounded input/output, rate and concurrency. A live accounting query closes the cached-auth/DB-outage gap and stops admission at 4 USD of the 5 USD local acceptance envelope. Neither this query nor native budgets reserve the full price of in-flight calls: the cap is soft, with measured overshoot. Cost ledger records include paid completions even when output is subsequently denied.

The exporter reads sanitized metadata and native persistent key spend. Prometheus labels contain only bounded workload/model/operation categories. Request IDs, keys, prompts and document text are not metric labels. The Grafana dashboard distinguishes provider-call latency, transport completions and semantic outcomes; transport success is not answer correctness.

The coding workflow is a real gateway model call over two allowlisted synthetic source/test files. The returned patch may change only `task.py`; it cannot change the acceptance test, paths, modes or symlinks. Tests run as non-root in a read-only container with no network, no credentials and bounded resources. The Codex subscription conversation itself is not claimed to route through LiteLLM.

Local kind does not prove production HA, AWS deployment, encrypted secret custody or CNI-enforced egress isolation. No AWS services were needed, so AWS Budgets is N/A. A provider being network-reachable does not imply the application possesses its credentials.
