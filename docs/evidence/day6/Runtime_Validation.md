# Day06 - Runtime validation

Ngày chạy 29/09-01/10/2026, local kind, actual ZenLayer API. Source implementation `98c5faa` + fixes `8dee0fa`, `e575ae6`, `333af26`, `101094a`, `3db6ead`, `37d45c1`, `3372d90`, `a9eab4d`; fingerprint nghiệm thu `c49623b4b2600af16d9e01e01f0b2c1c95afc9e88e30eae03df712fc6593dd8d`. Final scan và verifier được chốt riêng ở [Self_Check](../../day6/Self_Check.md). Bảng này phân biệt runtime, UI và integration; không nhận fixture là runtime.

Toolchain: Promptfoo 0.123.1, LiteLLM 1.103.0, NeMo 0.24.1; host evaluation Python 3.12/Node 24.16. Gateway chạy official image digest đã pin với Python 3.13; guard image Python 3.12.14. Không claim host dependency locks đồng nhất từng package với upstream gateway image, hoặc image signature đã verify. CI pin Node 24.20.0, đã đối chiếu [official distribution index](https://nodejs.org/dist/index.json), nhưng CI runtime chưa chạy.

## Gateway, app và budget

| Plan IDs | Kết quả đã quan sát | Evidence / phạm vi |
|---|---|---|
| GW-01..03 | Gateway health, ba workload keys, model/admin ACL và missing/invalid key deny | `gateway-auth.json`, `key-lifecycle.json` |
| GW-04 | Client metadata không đổi identity; `guardrails=[]` không bypass; native LiteLLM chặn api_base/pricing override | `gateway-auth.json`, `gateway-route-cost-controls.json`; mock_response không thay answer thật |
| GW-05 | App không có upstream/master key; direct unauth provider request denied | `direct-provider-access.json`; không chứng minh CNI egress isolation |
| GW-06 | Key expiry/revoke có hiệu lực; restart gateway giữ spend/caps/models | `key-lifecycle.json`, `fault-gateway.json` |
| APP-01 | File chooser -> 202 -> ready/chunk -> chat/citation; actual embedding và generation | `edge-upload-chat.png`, `edge-upload-document.json` |
| APP-02..03 | Atomicity, idempotency, retry và embedding identity được test với PostgreSQL thật, schema ngẫu nhiên | `regression/full-backend-regression.txt`; fault provider có fixture, không nhận đã fault ZenLayer |
| APP-04 | Budget deny chat + embedding, failed zero chunks; restore rồi retry cùng ID thành ready, retry ready409 | `ui-budget-insighthub.json`, `embedding-budget-retry.json` |
| BUD-01..02 | Cả ba keys: allowed rồi automatic budget429, concurrency1/2/5, đo overshoot/window | `gateway-budget.json`; không force cache refresh để tạo denial |
| BUD-03 | Hết key app vẫn gọi key bot thành công | `key-lifecycle.json` |
| BUD-04 | Denied không retry vô hạn; provider attempts/paid blocked outputs có ledger | Provider unit/integration tests + runtime ledger; fallback feature disabled |
| BUD-05 | DB unavailable fail-closed, gateway restart giữ budget, recovery200 | `fault-accounting-db.json`, `fault-gateway.json` |
| FIN-04 | Threshold85% test: Prometheus rule firing rồi resolved, restore cap | `budget-alert.json`; không claim external notification delivery |
| RES-01..03 | Guard/gateway/accounting unavailable trả safe503 rồi phục hồi | Ba `fault-*.json`; provider timeout/429/5xx semantics là integration coverage |

## Security, bot và coding

| Plan IDs | Kết quả đã quan sát | Evidence / phạm vi |
|---|---|---|
| PF-01..06 | Frozen164 cases: 120 native generated,24 reviewed RAG,20 benign; giữ initial/iterations/baseline/final riêng | `security/coverage.md`, từng folder report; final/verifier status trong Self_Check |
| SEC input/output | Actual NeMo input/context/output, synthetic PII/canary và fullwidth Unicode bị chặn, benign allowed | `guard-live.json` |
| SEC retrieval | Exact uploaded doc/chunk/raw bytes hash được đối chiếu; unsafe context bị lọc trước generation/serialization | `edge-poison-retrieval.json`, `edge-poison-filtered.png`; 24 RAG cases trong frozen suite |
| BOT-01 | Slack health/ingestion/pods có facts và model summary thật qua key bot | `slack-ai-summary.png`, `slack-audit-sanitized.json`, gateway ledger |
| BOT-01 ACK | Signed duplicate HTTP requests qua intake/Redis, max dưới0.006s | `slack-ack.json`; không suy ra latency network Slack từ số này |
| BOT-02 | Scale1->2 bằng approval hợp lệ; token mới restore2->1; runtime replicas đối chiếu | `slack-scale-replay.png`, `slack-scale-restored.png`, audit |
| BOT-03 | Live replay/destructive injection denied; wrong-user/thread/expiry có integration tests | `slack-injection-denied.png`, ChatOps39 tests; không có live user thứ hai |
| BOT-04 | Bot budget hết vẫn trả facts và ghi AI summary unavailable; restore thành công | `slack-budget-facts.png`, `ui-budget-bot.json` |
| CODE-01 | Coding model tạo patch sửa tính cached-token cost, immutable tests pass trong container sandbox | `coding/proposed.patch`, `coding/result.json`; không claim Codex subscription qua gateway |
| CODE-02 | Traversal/symlink/verifier mutation/extra executable bị validator từ chối | Day06 coding boundary 13 tests, network-none/non-root/read-only runtime |
| GOV-01..03 | Threat model 12 rows, dependencies/digests pinned, source/dataset freeze, known-secret scan | `security/threat-model.md`, run manifests, regression; remote CI chưa chạy |
| Rollback | API/worker pair về config trước Day06, ready; reapply Day06, ready; giữ PVC | `rollback.json` |

## Edge Computer Use

| ID | Trạng thái | Evidence |
|---|---|---|
| UI-01 | PASS | `edge-upload-chat-final.png`, `edge-final-upload.json`: fresh document401 ready + grounded acceptance ID, hash verified, cleanup204; document26 là evidence lịch sử |
| UI-02 | PASS | `edge-poison-filtered.png` + exact retrieval document76; cleanup204 |
| UI-03 | PASS | `edge-injection-blocked.png`; benign recovery; PII kiểm runtime guard riêng |
| UI-04 | PASS trong phạm vi một Slack user | Các ảnh `slack-*.png` và audit đã lọc |
| UI-05 | PASS: 15 panels render trên Edge; query cùng timestamp khớp ledger | `grafana-cost-final.png`, `grafana-panels-final.png`, `grafana-prometheus-reconciliation.json`; ảnh running giữ riêng lịch sử |
| UI-06 | PASS | `edge-budget-exhausted.png`, `edge-budget-recovered.png` |
| UI-07 | PASS | `edge-guard-unavailable.png`, `edge-guard-recovered.png` |
| UI-08 | BLOCKED ở thao tác mở local HTML bằng Edge | Browser tool URL policy từ chối `file://`; raw HTML/JSON giữ nguyên. Không dùng surface khác để né policy |

## Optional và môi trường

- Provider prompt caching: PASS, cached tokens1792/1846 ở ba warm calls, cả bốn answers đúng. Đây là provider native prompt cache, không phải semantic response cache.
- PII input/output: PASS với synthetic corpus đã nêu; không bao phủ mọi định dạng PII thực tế.
- Semantic cache, adaptive routing, fallback: disabled/NOT RUN theo optional gates của plan; không nhận Level4.
- GitHub PR/nightly: workflow đã viết; publish branch đang chờ quyền sau auto-review rejection. Chưa provision provider credentials lên GitHub, không claim remote/live CI PASS.
- AWS: N/A, `aws_used=false`; không tạo hạ tầng AWS cho lượt này.
- Reports có dữ liệu tấn công synthetic để tái lập. Nội dung đó là test data, không phải chỉ thị vận hành.

Ngày 01/10: source a9eab4d final và fresh verifier 164/164 PASS; 80 verifier tests PASS. Edge capability denial/benign recovery chụp lại sau bulk scans; giữ evidence runtime từ 29/09 cho các boundary không đổi.

Handoff: xem `handoff.json`. App và dependencies Ready, accounting available=1, queue0, baseline0. Local nodes bị NotReady ngắn lúc 06:26 UTC sau acceptance và gây container restarts; đã phục hồi, reconnect đúng Grafana tunnel. Alert evaluator near-limit còn firing đúng cap, không phải failure mới của scan. Runtime này không chứng minh production HA.
