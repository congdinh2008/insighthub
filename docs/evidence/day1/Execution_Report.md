# Day 01 - Execution report

Ngày 17/09/2026. Branch `day1-refactor`, base `0d5b838776a5f1af01d737674d8fc85724c3c60f`. Source/artifact binding tại [evidence envelope](../../../evidence/day1.json). [Plan](../../plans/Day01_Implementation_Plan_v1.0.md), [review/self-check](../../day1/Review_and_Self_Check.md).

## Kết quả nghiệm thu local

- **Ba lỗi recovery đã được sửa và kiểm chứng lại:** worker tự restart khi mất Redis; polling phục hồi sau lỗi API; failed metadata tự xuất hiện sau upload lỗi.
- Local Docker Desktop/macOS, Compose project riêng `insighthub-day1-final-0917`; API 18001, web 13001, bind loopback. Application/providers dùng fixture, Python runtime/tooling 3.12.14, vector 1024, chunk size 800 và overlap 100.
- Năm service Running/healthy. Không thay DB schema, specification hoặc verifier. Web chỉ thay status recovery, giữ layout và tính năng.
- **58 API tests + 71 subtests, 10 worker tests, 6 live HTTP tests, 68 verifier regression tests PASS.** Hai deprecation warnings từ Starlette/AnyIO được giữ trong output; không skip/xfail.
- Ruff check/format, mypy strict 22 modules, pre-commit và Next.js production build PASS. Starter MCP regression/offline/live smoke PASS.
- **11 browser cases PASS**, gồm cả API/Redis outage và polling timeout/manual refresh. Browser thao tác file picker, chat và Swagger thực tế.
- Kiểm thử fixture xác minh pipeline/contract; chưa đánh giá real-model quality hoặc provider latency.

| Gate | Evidence |
|---|---|
| Backend/DB và worker | [backend-worker-tests.txt](backend-worker-tests.txt) |
| Live HTTP | [live-contract-tests.txt](live-contract-tests.txt) |
| Verifier regression | [verifier-regression-tests.txt](verifier-regression-tests.txt) |
| Quality và hooks | [quality-checks.txt](quality-checks.txt), [pre-commit.txt](pre-commit.txt) |
| Starter MCP | [mcp-regression-tests.txt](mcp-regression-tests.txt) |
| Runtime health/services | [compose-status.json](compose-status.json), [compose-services.txt](compose-services.txt) |
| Day 01 verifier | [verifier-day1.json](verifier-day1.json), bounded runtime contract |
| Browser | [11 cases và screenshots](Browser_E2E_Report.md) |

Baseline starter: 48 backend tests, sync smoke HTTP 201 PASS; [test output](baseline-backend.txt), [smoke](baseline-smoke.json). Local acceptance không thay GitHub CI/PR của bài nộp; MH10 vẫn cần PR đúng title trên repository của học viên.

## Latency

Mẫu `sample-docs/so-tay-van-hanh.md`, 1705 bytes, SHA-256 `6872a5a8e97c186006aade5dfb27dc9ff89ace7944eaabdd4366bc0f25d76c7d`. Một warmup riêng và năm lượt đo tuần tự với monotonic clock; application fixture, stack healthy, máy local dùng chung tài nguyên.

| Lượt | Document ID | HTTP | Upload ms | Ready ms từ lúc bắt đầu |
|---|---|---|---|---|
| 1 | 2 | 202 | 8.44 | 117.57 |
| 2 | 3 | 202 | 10.00 | 120.12 |
| 3 | 4 | 202 | 10.24 | 121.02 |
| 4 | 5 | 202 | 7.45 | 118.83 |
| 5 | 6 | 202 | 9.63 | 122.25 |

Cả năm lượt đạt upload <1s và ready <30s. [Measurements đầy đủ](runtime-probe.json). PDF đúng 10 MiB trả 202 trong 194,48 ms và ready trong 310,91 ms; vượt một byte trả 413. PDF biên dùng metadata padding, không đại diện mọi PDF. [Boundary evidence](upload-boundaries.json).

## Recovery, dữ liệu và lifecycle

- **Redis outage khi worker đang chạy:** chỉ start lại Redis; restart count tăng từ 0 lên 1, document ID 7 retry cùng ID ready sau 3.28s. Probe không gọi start worker trong bước này. [Runtime evidence](runtime-probe.json).
- **Browser Redis outage:** document ID 16 failed/queue_unavailable tự hiện; chỉ start Redis, Swagger retry 202 cùng ID, worker tự phục hồi và document ready. [Worker state](worker-recovery.json), [JSON logs](worker-runtime.json).
- **API outage khi pending:** ID 15 tự chuyển ready sau khi API/worker phục hồi; lỗi polling tự xóa, lỗi upload file rỗng vẫn được giữ. Không refresh trang trong bước recovery.
- **Polling limit:** UI dừng sau 60 lần và hướng dẫn refresh; refresh khi vẫn pending bắt đầu chu kỳ mới, tự chuyển ready sau start worker.
- **SIGTERM:** job đã started và chưa completed trước signal; worker drain, exit 0 sau khoảng 1.51s. 381 chunks; trước/sau redelivery đều `381|381|381` cho metadata/count/distinct indices.
- **AOF persistence:** queue giữ job qua Redis restart trong phép thử riêng có operator stop/start worker.
- **Provider retry:** 1/2/4s, nonretryable/exhaustion được kiểm bằng unit và isolated DB tests; không tuyên bố đã gọi real provider trả 429.

Docker restart backoff có thể tăng khi Redis gián đoạn lâu; số đo recovery trên là outage ngắn của lab. DB commit và Redis enqueue không atomic, không claim exactly-once; xem [recovery runbook](../../day1/Runbook.md).

## Phạm vi commit

1. `fix(web): recover document status after request failures` - hai lỗi starter về trạng thái.
2. `feat(ingestion): add resilient async worker and controlled retries` - implementation Day 01 cùng tests/config/CI.
3. `docs(day1): add student solution and verified acceptance evidence` - context, plan, năm prompt, runbook, self-check và bằng chứng cuối.

[Solution guide](../../day1/README.md) và [bộ năm prompt](../../../ai-prompts/day1.md) dùng cho học viên thực hành; học viên ghi kết quả, prompt logs và PR/CI của môi trường mình.
