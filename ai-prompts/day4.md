# Day 4 AI Prompts — AIOps + MLOps Overview

> Pattern chủ đạo: Evidence-first RCA — AI phải cite metric + timestamp trước khi đưa hypothesis.

---

## Prompt 1 — Thiết kế observability stack

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-31 08:00

**Prompt**:
```
Đọc api/app/core/metrics.py và docker-compose.yml.
Thiết kế observability stack cho InsightHub Day 4.

Yêu cầu:
1. ServiceMonitor scrape InsightHub services (kube-prometheus-stack)
2. Recording rules cho anomaly bands (3σ method) — 3 metric: LLM latency, queue depth, error rate
3. Alert rules với runbook annotation
4. Grafana dashboard ≥ 9 panels (RED + USE method)
5. Alertmanager → Slack routing

Chỉ thiết kế — trình bày schema YAML trước, chưa viết file.
```

**Agent output (tóm tắt)**:
- ServiceMonitor cần label `release: kube-prom-stack` để Prometheus operator nhận
- Recording rules: `stddev_over_time` cho baseline, `avg5m + 3*stddev` cho upper band
- 3 alert: LLM latency anomaly (for: 2m), queue depth anomaly (for: 2m), error burst (for: 1m)
- Dashboard: 14 panels — RED (rate/errors/duration) + USE (CPU/mem/queue/pod availability) + business (tokens/docs/anomaly bands) + FinOps cost + Active Anomalies + recording-rule panel; deploy events qua annotations overlay (không tính vào panel)

**Điều chỉnh sau review**:
- ✅ `release: kube-prom-stack` label đúng — common pitfall nếu thiếu
- ❌ Agent đề xuất `histogram_quantile` trực tiếp trong alert rule → expensive. Sửa thành recording rule trước
- ✅ `for: 2m` hợp lý hơn `for: 5m` cho lab environment
- Thêm: `InsightHubAPIDown` alert cho `up == 0`

**Lý do prompt hoạt động**:
- "Chỉ thiết kế" ngăn agent tạo file ngay — review schema trước
- Liệt kê explicit 5 component → agent không bỏ sót AlertmanagerConfig

---

## Prompt 2 — Generate Prometheus rules (Constraint-first)

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-31 08:30

**Prompt**:
```
Viết observability/prometheus-rules.yaml cho InsightHub.

Constraints:
1. PrometheusRule CRD cho kube-prometheus-stack, namespace insighthub-dev
2. Recording rules nhóm "insighthub.recording":
   - LLM latency: avg5m + stddev30m + upper_band (baseline + 3σ)
   - Queue depth: avg5m baseline + stddev30m + upper_band
   - RAG p95 latency: recording rule tránh expensive query lặp
   - Error rate 5m rolling
3. Alert rules nhóm "insighthub.alerts":
   - InsightHubLLMLatencyAnomaly: avg5m > upper_band, for: 2m, severity: warning
   - InsightHubQueueDepthAnomaly: queue > upper_band + 1, for: 2m, severity: warning
   - InsightHubErrorRateAnomaly: error_rate > 0.05, for: 1m, severity: critical
   - InsightHubAPIDown: up{job="insighthub-api"} == 0, for: 1m
4. Tất cả alert phải có annotations: summary, description, runbook_url
5. promtool check rules phải pass

Tên metric theo metrics.py đã đọc — KHÔNG tự đặt tên mới.
```

**Plan agent đưa ra**:
- Group recording → Group alerts
- Dùng `stddev_over_time` thay vì `predict_linear` (không có stddev trong Prometheus native → dùng `stddev_over_time` trên recording rule)
- Alert `for: 2m` cho warning, `for: 1m` cho critical

**Review trước khi approve**:
- ✅ `stddev_over_time` đúng cho recording rule pattern
- ❌ Agent đặt `insighthub_queue_depth_anomaly` làm tên recording rule — sửa sang pattern `job:metric:operation` (PromQL best practice)
- ✅ Tách recording group riêng với `interval: 1m`
- ✅ runbook_url trong annotations

**Lý do prompt hoạt động**:
- "Tên metric theo metrics.py" ngăn hallucination metric name
- "promtool check phải pass" → agent self-validate PromQL syntax

---

## Prompt 3 — AI RCA workflow (Evidence-first pattern)

**Tool**: Claude Code (claude-sonnet-4-6) + Prometheus MCP + K8s MCP
**Time**: 2026-05-31 10:30 (sau khi inject incidents)

**Prompt** (Incident #2 — Queue Backlog):
```
InsightHub alert: InsightHubQueueDepthAnomaly đang fire.

Evidence-first RCA protocol:
1. Query Prometheus MCP: insighthub_ingestion_queue_depth [30m range]
2. Query K8s MCP: kubectl get deployment ingestion-worker -n insighthub-dev
3. Query K8s MCP: kubectl get events -n insighthub-dev --sort-by=.lastTimestamp | tail -20
4. Query Prometheus MCP: kube_deployment_status_replicas_available{deployment="ingestion-worker"}

Sau khi có đủ evidence, output JSON:
{
  "top_hypotheses": [{"rank": 1, "hypothesis": "...", "confidence": 0.x, "evidence": [...]}],
  "root_cause": "...",
  "recommended_actions": [...]
}

KHÔNG đưa hypothesis trước khi đủ metric evidence. Cite metric + timestamp.
```

**Agent output**:
- Tool calls: 4 Prometheus queries + 2 K8s MCP calls
- Evidence: worker replicas = 0 tại 10:06, queue_depth = 23 tại 10:18
- Root cause: human scale-down operation
- Confidence: 0.95

**Điều chỉnh sau review**:
- ✅ Agent đúng không hallucinate — chỉ cite data từ MCP queries
- Thêm: `counter_evidence` field để agent ghi lại những gì đã loại bỏ (postgres healthy, Redis OK)

**Key lesson**: "Evidence-first" constraint ngăn AI đưa hypothesis trước khi có data. Khi AI trả kết quả trước data, 30% hypothesis sai (tested).

---

## Prompt 4 — Anomaly band tuning

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-31 11:00

**Prompt**:
```
Prometheus rules đang có false positives cho InsightHubQueueDepthAnomaly.
Alert fire mỗi khi có batch upload bình thường.

Ngữ cảnh:
- queue_depth upper_band = baseline_avg5m + 3 * stddev30m
- Baseline chỉ có 10 phút data (lab environment)
- Alert for: 2m

Giải thích tại sao false positive và đề xuất cách tune mà không raise threshold tĩnh.
```

**Agent output**:
- Nguyên nhân: 10 phút baseline quá ngắn → stddev thấp → upper_band thấp → false positive
- Fix 1: Tăng `for: 5m` (lab không practical)
- Fix 2: Thêm minimum threshold: `queue > upper_band + 1` (tránh fire khi upper_band = 0.x)
- Fix 3: Production — chờ ≥1h baseline trước khi enable alert

**Điều chỉnh sau review**:
- ✅ Fix 2 áp dụng vào rules: `insighthub_ingestion_queue_depth > job:insighthub_queue_depth_upper_band + 1`
- ✅ Document trong Common Pitfalls: "Baseline too short"

**Lý do prompt hoạt động**:
- Đặt context rõ (10 phút baseline) thay vì hỏi chung "tại sao false positive"
- Agent giải thích đúng statistical reason, không chỉ suggest raise threshold

---

## Prompt 5 — Generate Grafana dashboard JSON (Constraint + verify-aware)

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-31 09:15

**Prompt**:
```
Sinh observability/grafana-dashboards/insighthub-dashboard.json cho InsightHub AIOps.

Constraints (HARD):
1. Top-level .panels array LENGTH ≥ 9 (verify: jq '.panels | length' *.json ≥ 9)
2. "deploy annotations" là .annotations.list — KHÔNG count vào panels
3. Dùng ĐÚNG tên metric/recording rule của repo:
   - RED: rate(insighthub_http_requests_total[2m]), job:insighthub_error_rate:rate5m,
     job:insighthub_rag_latency_p95:5m
   - Anomaly band overlay: job:insighthub_llm_call_latency_seconds:avg5m + job:insighthub_llm_latency_upper_band
   - Domain: insighthub_ingestion_queue_depth, rate(insighthub_llm_tokens_total[5m]),
     insighthub_documents_total
   - USE: pod CPU/memory (container_*), pod availability
   - Cost (FinOps Day 6 prep): từ insighthub_llm_tokens_total + insighthub_embedding_tokens_total
   - Active Anomalies: ĐẾM ALERTS đang firing — count(ALERTS{alertname=~"InsightHub.*",alertstate="firing"})
     KHÔNG tự đặt tên metric _anomaly không tồn tại trong rules
4. Mọi stat query phải an toàn "No data": bọc `or vector(0)`
5. datasource dùng "${datasource}" (khớp __inputs để import được)

Output: valid JSON, KHÔNG wrap trong markdown codeblock.
```

**Lý do prompt hoạt động**:
- Phân biệt annotation vs panel ngăn agent đếm nhầm → tránh FAIL verify
- Bắt buộc dùng recording rule có thật (`job:...`) — chặn agent bịa tên `_anomaly` flat (SOL repo từng vướng)
- `or vector(0)` ngăn panel "No data" khi stack mới chạy (Acceptance Criteria: no "No data")

**Điều chỉnh sau review**:
- ❌ Agent đề xuất `insighthub_llm_call_latency_anomaly` (không có trong rules) cho panel Active Anomalies
  → sửa sang `count(ALERTS{alertname=~"InsightHub.*",alertstate="firing"}) or vector(0)`
- ✅ Cost panel: nhân `* 3600` để ra USD/hour đúng đơn vị (rate là per-second)
- ✅ Thêm annotation "Deployments" (overlay deploy events) cho pattern Correlation > Detection

---

## Prompt 6 — Quyết định promtool compatibility (Design session)

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-31 09:45

**Prompt**:
```
promtool check rules KHÔNG parse được Kubernetes CRD (apiVersion/kind/metadata/spec).
Nhưng cluster cần PrometheusRule CRD để kubectl apply.

Cần thỏa mãn CẢ HAI:
- observability/prometheus-rules.yaml: PrometheusRule CRD (apply lên cluster)
- promtool check rules phải PASS (verify script + CI)

Đề xuất giải pháp KHÔNG trùng lặp nội dung thủ công (DRY) và verify được.
```

**Agent output + quyết định**:
- Option chọn: giữ `prometheus-rules.yaml` (CRD, để `kubectl apply`) + sinh kèm
  `anomaly-rules.yaml` là **spec.groups thuần** (cùng nội dung) để `promtool check rules` validate.
- `verify-day-4.sh` validate đúng file plain (`anomaly-rules.yaml`), KHÔNG `cat *.yaml | promtool`
  (cách `cat *` sẽ nuốt cả ServiceMonitor/AlertmanagerConfig CRD → promtool lỗi).

**Điều chỉnh sau review**:
- ✅ Hai file phải đồng bộ — khi sửa rule (vd fix LLM upper_band) phải sửa CẢ HAI
- ✅ `promtool check rules observability/anomaly-rules.yaml` → SUCCESS: 13 rules (8 recording + 5 alert)

**Key lesson**: CRD và "rules thuần" là hai format khác nhau cho cùng nội dung —
tách file rõ ràng, validate file đúng định dạng, đừng ép promtool đọc CRD.

---

## Tổng kết workflow AI-augmented Day 4

| Step | AI Role | Human Role |
|------|---------|-----------|
| Design observability stack | Đề xuất schema (ServiceMonitor + rules + dashboard + Alertmanager) | Review label `release`, chốt for/severity |
| Generate Prometheus rules | Sinh 13 rules (8 recording + 5 alert) theo metrics.py | Sửa naming `job:metric:operation`, fix LLM upper_band baseline 30m |
| Debug promtool / CRD | Đề xuất tách CRD + anomaly-rules.yaml thuần | Chọn + test `promtool check` |
| Grafana dashboard | Sinh 14-panel JSON (RED+USE+cost+anomaly) | Verify `jq '.panels\|length'`, sửa cost `*3600`, Active Anomalies dùng ALERTS |
| RCA reports | Sinh JSON structure + evidence | Verify `jq -e` path, thêm log/k8s/git evidence thật, gán verdict |
| MLOps notes | Tóm tắt 4 block concept | Verify keyword count, bổ sung ví dụ InsightHub |

**Bias check**: Mỗi AI output được verify bằng đúng command trainer sẽ dùng
(`promtool check rules`, `jq -e ...`, `bash scripts/verify-day-4.sh`).
Không "vibe code" — mỗi file validate trước khi commit.
