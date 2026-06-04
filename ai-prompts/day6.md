# Day 6 AI Prompts — Security, Governance & FinOps

## Prompt 1 — Promptfoo Config for OWASP LLM Top 10 Red Team

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-06-05 09:00

**Prompt**:
```
Goal: Generate promptfoo red team configuration targeting OWASP LLM Top 10 v2025 for InsightHub RAG.

Constraints:
- 8 test cases covering: prompt injection, indirect injection, SSRF via embedding, 
  training data poisoning, supply chain attack, output hijacking, model disagreement, 
  jailbreak detection
- For each test: malicious input, expected safe output, failure condition
- Config file: security/promptfooconfig.yaml (YAML format)
- Tests must run against live InsightHub API (not mocked)
- Timeout 30s per test
- Include base test cases (happy path) + adversarial variants
- Output MUST include: tests, providers (gemini/anthropic config), assertions

Example test structure:
- Input: prompt injection string
- Expected: model refusal OR safe response
- Metadata: threat category, severity (critical/high/medium)

Return: PLAN showing test matrix, then generate promptfoo config.
```

**Why it worked**:
- Explicit OWASP Top 10 list forced coverage — prevents agent from creating vague "security tests"
- "Run against live API" constraint ensured config is actionable, not theoretical
- "8 test cases" numeric requirement prevented under-specification
- Including happy path + adversarial pairs balances false positives/negatives

**What I changed**:
- Agent initially had tests inherit provider config — moved to explicit provider section for clarity
- Added `assert` blocks for semantic assertions (e.g., "output should not contain 'SYSTEM OVERRIDE'")
- Structured test metadata with tags (threat_type: indirect_injection) for analytics later

---

## Prompt 2 — STRIDE Threat Model for InsightHub

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-06-05 09:30

**Prompt**:
```
Goal: Create comprehensive STRIDE threat model for InsightHub Day 5 ChatOps bot + RAG integration.

Constraints:
- 8 threats minimum: 1 per STRIDE category + 2 elevated risk combinations
- For each threat: description, data flow, impact, existing controls, recommended mitigations
- Output format: markdown table + narrative sections
- Threats must be specific to InsightHub architecture (RAG + bot + K8s)
- Include: attack vectors, entry points, affected components
- Mitigations must be actionable (not vague)
- File: security/threat-model.md

STRIDE categories:
- Spoofing: identity misrepresentation (Slack user identity)
- Tampering: data modification (chunk store, audit log)
- Repudiation: action denial (audit trails defeat this)
- Information Disclosure: data leakage (embedding vectors, RAG context)
- Denial of Service: availability attacks (token limits, queue depth)
- Elevation of Privilege: unauthorized actions (bot permissions, K8s RBAC)

Return: PLAN showing threat list + impact matrix, then generate threat model.
```

**Why it worked**:
- "8 threats minimum" and "specific to InsightHub" prevented generic boilerplate
- "Actionable mitigations" forced details (not just "add security")
- STRIDE structure ensures systematic coverage
- "Data flow, impact, existing controls" provides decision-making info for Day 6 lab

**What I changed**:
- Agent grouped threats by component (RAG → K8s → Slack) for easier prioritization
- Added "existing controls" section to highlight what Day 1–5 already built (signature verify, RBAC)
- Mapped each threat to OWASP LLM Top 10 + CWE for compliance context

---

## Prompt 3 — NeMo Guardrails Config for Input/Output Protection

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-06-05 10:00

**Prompt**:
```
Goal: Implement NeMo Guardrails configuration for InsightHub to defend against 
prompt injection, prompt leakage, and harmful outputs.

Constraints:
- Config path: security/nemo-config/
- Structure: colang files (NeMo's domain language) + YAML rail specs
- Input rails: block/sanitize messages containing:
  1. Common prompt injection patterns ("ignore instructions", "system override", etc.)
  2. PII exposure patterns (Slack tokens, API keys, secrets)
  3. Command injection strings (kubectl/shell metacharacters)
- Output rails: block Claude response if it:
  1. Exposes internal system prompts
  2. Contains raw API credentials
  3. Acknowledges override requests ("I will now ignore...")
  4. Returns raw K8s YAML with secrets
- Integration point: api/app/guardrails.py wraps LLM call
- Mode: detection first (log violations), blocking optional

Files to generate: rails.colang, rail_spec.yaml, integration.py

Return: PLAN showing rail hierarchy, then generate config + wrapper.
```

**Why it worked**:
- "Detection first, blocking optional" prevented over-blocking that breaks user experience
- Explicit patterns (PII, injection, command) gave agent concrete targets
- "Three input rails + three output rails" ensured coverage without bloat
- Integration point clarified agent should generate wrapper, not just config

**What I changed**:
- Agent generated overly strict input rail → refined to warn on injection patterns rather than block
- Added `confidence_score` to rails for audit (log which rail triggered)
- Included fallback: if guardrail fails to load, API continues (graceful degradation)

---

## Prompt 4 — LiteLLM Gateway + Virtual Keys + Budget Caps Setup

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-06-05 10:30

**Prompt**:
```
Goal: Configure LiteLLM proxy gateway for InsightHub to enforce budget caps, 
virtual API keys, rate limiting, and cost tracking.

Constraints:
- Gateway runs on port 4000, routes requests to Anthropic / Gemini / Ollama
- Virtual keys: 3 keys for Day 6 lab (student1, student2, student3)
  - Each key has daily spend cap ($5)
  - Each key tied to specific model (student1→gemini, student2→anthropic, student3→ollama)
- Rate limits: 100 requests/min per key, 500 tokens/min per key
- Cost tracking: log every request with (timestamp, key, model, tokens_in, tokens_out, cost)
- Config format: litellm-config.yaml (YAML) + .env for secrets
- Health endpoint: GET /health → {status, uptime, active_keys}
- Cost dashboard endpoint: GET /dashboard/costs → JSON with daily breakdown
- Fallback: if spend cap hit, return 429 (too many requests) with clear message
- Tests: offline unit tests for key validation + cap enforcement (no live API calls)

Return: PLAN showing gateway architecture, then generate config + wrapper classes.
```

**Why it worked**:
- "Virtual keys + daily spend cap" forced agent to implement multi-tenancy, not global caps
- "Offline unit tests" prevented tests from requiring live LiteLLM instance
- "Health + cost dashboard endpoints" made gateway observable
- "Graceful fallback" (429 instead of 500) ensured user experience clear

**What I changed**:
- Agent initially used rate_limiter lib that required Redis → simplified to in-memory tracking (sufficient for Day 6)
- Added `virtual_key_to_model_mapping` dict for clarity vs. agent's initial string parsing
- Structured cost_log as NDJSON (one request per line) matching audit log pattern from Day 5
- Config includes `.env.example` showing which secrets to set (ANTHROPIC_API_KEY, etc.)

---

## Day 6 Workflow Summary

Four prompts above implement the **"Defense in Depth"** pattern:

1. **Promptfoo** (Prompt 1): Discover vulnerabilities via red team
2. **Threat Model** (Prompt 2): Understand system-wide risks
3. **NeMo Guardrails** (Prompt 3): Deploy guardrails at I/O boundary
4. **LiteLLM** (Prompt 4): Control cost + rate limit + audit trail

Each prompt was designed with:
- **Concrete constraints** (avoid vague "make it secure")
- **File paths** (know exactly where output goes)
- **Integration points** (show how pieces connect)
- **Test strategies** (verify offline before production)

This mirrors real Day 6 lab: students run promptfoo → find injection → fix with guardrails → verify with LiteLLM budget → check audit logs.
