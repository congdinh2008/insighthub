# Day 5 AI Prompts — ChatOps Bot & Incident Response

## Prompt 1 — Architecture + Signature Verification

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-06-04 09:30

**Prompt**:
```
Goal: Implement Slack signature verification for ChatOps bot FastAPI app.

Constraints:
- Must read raw body BEFORE json.loads (Slack requires raw bytes for HMAC)
- Reject requests with X-Slack-Request-Timestamp older than 5 minutes (replay defense)
- Use hmac.compare_digest (constant-time, not ==)
- Raise HTTPException(401) not 403 on failure
- Export the function (not private) so tests can import it directly

Pattern to follow: existing api/app/main.py uses FastAPI + BackgroundTasks

Return: PLAN first (steps + which headers to read), then implement.
```

**Why it worked**:
- "Constraints-first" forced the agent to address the raw-body timing issue (most common pitfall)
- "Reject > 5 minutes" made replay defense explicit — otherwise agent would skip it
- "Export for testing" guided the agent toward a testable design

**What I changed**:
- Reviewed PLAN: confirmed raw body must be read with `await request.body()` before passing to verifier
- Rejected agent's initial proposal to use `request.json()` — would fail HMAC since FastAPI already parsed body
- Approved revised function signature `verify_slack_signature(headers, body, signing_secret)`

---

## Prompt 2 — 3-Tier Permission System

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-06-04 10:00

**Prompt**:
```
Goal: Implement 3-tier permission system for ChatOps bot.

Constraints:
- Tier 1 READ: auto-allowed (health checks, status queries, pod list)
- Tier 2 WRITE: require confirmation token (scale, restart, stop, start)
- Tier 3 DESTRUCTIVE: always deny, no override (delete, drop, terminate, destroy)
- Token TTL = 60 seconds, stored in memory dict
- Token is one-time-use (consumed on validation)
- classify_intent() must use keyword matching, not LLM (fast, deterministic)

Return: PLAN showing keyword lists and token lifecycle, then implement.
```

**Why it worked**:
- Explicit 3-tier definition prevented the agent from inventing a 2-tier or 5-tier system
- "One-time-use" was critical — agent initially forgot to pop token after validation
- "Keyword matching, not LLM" prevented over-engineering with Claude calls just for classification

**What I changed**:
- Agent initially used `time.time()` for TTL — switched to `time.monotonic()` (not affected by clock adjustments)
- Added explicit `_DESTRUCTIVE_KEYWORDS` tuple for clarity

---

## Prompt 3 — Claude Tool-Calling Handler

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-06-04 10:30

**Prompt**:
```
Goal: Implement multi-turn Claude tool-calling loop in handler.py.

Constraints:
- Must respond < 3 seconds in Slack — all LLM work in BackgroundTask
- Max 5 tool-calling rounds to prevent infinite loops
- Every tool call MUST be logged to audit before returning
- Tool execution errors return {"error": str(e)} — never raise, always degrade gracefully
- Anthropic client is injectable (parameter) for offline testing
- http_client is injectable for K8s/Prometheus tools (testability)
- Import only from app.audit, app.permissions, app.tools — no circular imports

Tools to implement:
1. check_api_health — HTTP GET to InsightHub API
2. get_ingest_count_today — Prometheus API query
3. get_failing_pods — kubectl get pods -o json subprocess call

Return: PLAN showing loop iteration structure, then implement handler.py.
```

**Why it worked**:
- "Max 5 rounds" prevented the agent from implementing an unbounded while loop
- "Injectable client" was critical — without it, tests would need a live Anthropic API key
- Listing exact tools forced the agent to implement exactly 3, not invent extras

**What I changed**:
- Agent initially used `hasattr(b, 'text')` check — confirmed this is correct for SDK content blocks
- Added explicit `tool_uses = [b for b in response.content if b.type == "tool_use"]` clarity
- Verified `response.content` is a list of content blocks (not a generator) before iterating

---

## Prompt 4 — Offline Test Suite Design

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-06-04 11:00

**Prompt**:
```
Goal: Write pytest test suite for ChatOps bot that runs 100% offline.

Constraints:
- No live Slack/Anthropic/K8s/Prometheus calls (trainer CI has no credentials)
- Test signature verification directly (not through HTTP endpoint in conftest)
- Test all 3 permission tiers independently
- Test audit log writes NDJSON with correct fields (ts, user, tool)
- Mock Anthropic client for handler tests (inject via parameter)
- Use tmp_path fixture for audit log isolation
- asyncio_mode = auto in pytest.ini (avoid per-test markers)

Files to create: conftest.py, test_signature.py, test_permissions.py, test_audit.py, test_handler.py

Return: PLAN showing test organization, then implement all 5 files.
```

**Why it worked**:
- "100% offline" constraint was the key design driver — shaped the entire test architecture
- Listing all 5 files upfront prevented the agent from stopping at 2 test files
- "tmp_path for audit isolation" prevented test pollution of real chatops-audit.log

**What I changed**:
- Added `autouse=True` to `isolated_audit_log` fixture so every test automatically gets isolation
- Agent initially used `pytest.mark.asyncio` per-test — replaced with `asyncio_mode = auto` in pytest.ini
- Verified all 36 tests pass: `pytest -v` → 36 passed in 0.45s
