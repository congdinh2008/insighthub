# Day 04 AI prompts

## Prompt 1 - Research requirements and current architecture

**Host:** ChatGPT-Codex  
**Version / Model / Auth mode:** Codex desktop, GPT-5, authenticated workspace session  
**Context / Evidence:** `Running-Project-Specification-Student.md`, `AGENTS.md`, Day 01-03 source/evidence, Day 04 lab guide and verifier contract  
**Time:** 2026-09-23, Asia/Ho_Chi_Minh

**Prompt:**

> Inspect the merged InsightHub architecture and Day 04 source of truth. Map every Must-have and acceptance item to existing code, missing work and evidence. Keep the target at rubric L3. Explicitly exclude Should-have/Nice-to-have and Day 05-06 features. Do not implement until the plan is reviewable.

**Why it worked:** It forced requirement-to-source traceability before implementation and exposed queue metric, real token/cost and namespace gaps.

**What I changed:** I kept the existing `insighthub-dev` namespace, chose local-first telemetry and rejected Sift, SLO expansion and MLOps hands-on as outside the assigned scope.

## Prompt 2 - Implement telemetry and anomaly contracts

**Host:** ChatGPT-Codex  
**Version / Model / Auth mode:** Codex desktop, GPT-5, authenticated workspace session  
**Context / Evidence:** reviewed Day 04 plan, application metrics, Helm chart, ARQ queue semantics and Prometheus verifier requirements  
**Time:** 2026-09-23, Asia/Ho_Chi_Minh

**Prompt:**

> Implement only the approved Day 04 observability scope. Reuse Day 03 Helm and Day 02 read-only MCP foundations. Add bounded-label HTTP duration, provider/model token and reviewed-price metrics, independent PostgreSQL/Redis exporters, ServiceMonitors, exactly nine query panels, canonical one-hour anomaly-band rules and tests, resource limits and 15-day retention. Preserve the application contract and keep monitoring opt-in.

**Why it worked:** The constraints tied every code change to a Day 04 requirement and protected Day 03 rendering when monitoring is disabled.

**What I changed:** I modelled ARQ queue depth as Redis sorted-set size, preserved unknown when Redis scrape is missing, separated API cost estimate from billing and used Kubernetes sources for web/resource telemetry.

## Prompt 3 - Design bounded incidents and evidence-first RCA

**Host:** ChatGPT-Codex  
**Version / Model / Auth mode:** Codex desktop, GPT-5, authenticated workspace session  
**Context / Evidence:** anomaly rules, Kubernetes topology, existing MCP permission boundary and Day 04 RCA verifier schema  
**Time:** 2026-09-23, Asia/Ho_Chi_Minh

**Prompt:**

> Add three recoverable lab scenarios for LLM latency, queue backlog and server error burst. Every mutation must validate the selected lab, preserve prior state and have an explicit stop path. AI/MCP investigation stays read-only. Define the RCA JSON and evidence workflow so every metric citation can be matched to live Prometheus at its exact timestamp. Do not create placeholder RCA results.

**Why it worked:** It separated mutation by the operator from read-only diagnosis and prevented generated or stale telemetry from being treated as runtime evidence.

**What I changed:** I used a bounded provider proxy for latency/error, saved/restored worker replicas for queue backlog and left three RCA artifacts absent until the incidents are actually executed.
