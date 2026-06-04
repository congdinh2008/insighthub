# InsightHub — Threat Model (Day 6)

STRIDE + OWASP LLM Top 10 (2025) threat model cho InsightHub RAG notebook.
Phạm vi: web (Next.js) → api (FastAPI `/chat`, `/documents`) → ingestion-worker →
postgres/pgvector → LLM provider (Gemini/Anthropic/Bedrock qua LiteLLM gateway).

## Threat Register

| # | Threat | OWASP LLM | STRIDE | Component | Likelihood | Impact | Mitigation | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Direct Prompt Injection via `/chat` API | LLM01 | Spoofing | Chat endpoint | HIGH | HIGH | Input validation + system prompt hardening + guardrail deny-list ("ignore previous instructions") | Mitigated |
| 2 | Indirect Prompt Injection via poisoned RAG documents | LLM01 | Tampering | Ingestion pipeline (demo: `sample-docs/huong-dan-nguoi-moi.md`) | HIGH | HIGH | Document sanitization trước embedding + output validation rail | Mitigated |
| 3 | Insecure Output Handling rendered in web frontend | LLM02 | Tampering (XSS/Injection) | Next.js web dashboard | LOW | MEDIUM | CSP headers + audit `dangerouslySetInnerHTML` + output sanitization | Open |
| 4 | PII Leakage from RAG context | LLM02 / LLM06 | Information Disclosure | pgvector retrieval | MEDIUM | HIGH | PII detection pre-embedding + Bedrock `sensitiveInformationPolicy` ANONYMIZE | Mitigated |
| 5 | Excessive Agency / unauthorized tool use | LLM06 | Elevation of Privilege | LLM response handler | MEDIUM | HIGH | Guardrail `PROMPT_ATTACK` filter + output schema validation + no tool execution | Mitigated |
| 6 | Excessive Permissions (MCP + ChatOps bot RBAC) | LLM08 | Elevation of Privilege | MCP servers / bot service account | MEDIUM | HIGH | K8s `mcp-readonly` ClusterRole + AWS IAM `mcp-readonly` ReadOnlyAccess only | Mitigated |
| 7 | Overreliance on AI output without validation | LLM09 | Repudiation | Chat answer consumers | MEDIUM | MEDIUM | Mandatory `[nguồn: file]` citation + "không tìm thấy" fallback + human review | Open |
| 8 | System Prompt Exfiltration | LLM07 | Information Disclosure | API `/chat` endpoint | MEDIUM | MEDIUM | `cache_control` ephemeral system block + guardrail word deny-list | Mitigated |
| 9 | RAG Document Exfiltration | LLM06 | Information Disclosure | Vector DB retrieval | MEDIUM | HIGH | Access control on `/documents` + chunk-level authorization | Open |
| 10 | LLM Supply Chain Risk (provider compromise) | LLM05 | Tampering | External API deps (Gemini/Anthropic) | LOW | HIGH | LiteLLM gateway + model pinning + fallback routing | Mitigated |
| 11 | Data exfiltration via RAG poisoning payload | LLM01 / LLM06 | Information Disclosure | Ingestion → retrieval loop | MEDIUM | HIGH | Promptfoo `rag-poisoning` plugin in CI + input rail | Mitigated |
| 12 | API key leakage in logs / responses | LLM02 | Information Disclosure | api + worker logging | MEDIUM | HIGH | Env-var secrets only + guardrail `AWS_ACCESS_KEY`/`AWS_SECRET_KEY` BLOCK | Mitigated |
| 13 | Cost-based DoS (token exhaustion) | LLM10 | Denial of Service | LLM provider billing | MEDIUM | HIGH | LiteLLM virtual-key `max_budget` caps + `num_retries` limit + rate limiting | Mitigated |

## Notes

- **Likelihood/Impact** scale: LOW / MEDIUM / HIGH.
- **Status `Open`** items are tracked for the next hardening iteration (frontend CSP,
  `/documents` chunk-level authz, overreliance UX guardrails).
- Guardrail enforcement details: `security/bedrock-guardrail.json` and
  `security/nemo-config/config.yaml`.
- Red-team evidence: `security/red-team-report.html` (initial) →
  `security/red-team-final.html` (post-fix).
