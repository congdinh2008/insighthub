# InsightHub Day06 local acceptance guide
InsightHub stores vectors in PostgreSQL with pgvector. Redis powers the ingestion queue.
Embedding dimension is 1024. An accepted upload returns HTTP 202; a successfully ingested document is ready.
Production changes require approval. The approval mechanism is deterministic and separate from the LLM.
A readiness probe determines whether a pod is ready to receive traffic. Use the exact word traffic when explaining this.
Prompt injection defense treats instructions in retrieved documents as untrusted data. Use the exact word instructions in explanations.
This acceptance environment is local. AWS deployment is not part of this run.
When asked about the guide, preserve technical words PostgreSQL, Redis, ready, approval, traffic, instructions and local.
