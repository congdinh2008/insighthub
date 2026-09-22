# Day 02 - Debug container exited qua MCP

## Tình huống và mục tiêu

Ca fault injection có kiểm soát trong Compose project `insighthub-day2-lab`, Docker Desktop local, ngày 22/09/2026. Service `debug-case` chỉ thuộc profile `day2-debug`; đây không phải bug của application Day 01. Mục tiêu: dùng Docker MCP read-only để đọc trạng thái và log, lập RCA, để operator sửa đúng cấu hình, sau đó xác minh recovery qua MCP.

Host được kiểm chứng là Codex CLI 0.154.0 với model mặc định. Docker operations chạy qua Docker MCP Gateway 0.43.3 và Docker CLI 29.7.2 đã pin. Model chỉ có ba tool đọc và không có quyền restart hoặc recreate container.

## Evidence và RCA

`docker-operations.list_containers` trả container `insighthub-day2-lab-debug-case-1`, ID `492abb66db87`, trạng thái `Exited (78)`. `docker-operations.get_diagnostic_logs` trả:

```text
2026-09-22T05:20:05.994740546Z DAY2_CONFIG_MISSING: DAY2_REQUIRED_VALUE must be configured
```

| Giả thuyết | Đối chiếu | Kết luận |
|---|---|---|
| Thiếu hoặc sai env bắt buộc | Log nêu đúng biến; `docker-compose.day2.yml` exit 78 khi giá trị khác `configured`; `.env.example` để trống cho fault injection | Root cause |
| Image hoặc entrypoint không chạy | Entrypoint đã sinh log và trả đúng exit code của nhánh validation | Loại trừ |
| Worker hoặc database làm container thoát | `debug-case` không phụ thuộc hai service này; năm service application vẫn healthy | Loại trừ |

Model chỉ kết luận biến bị thiếu từ output MCP. Operator đọc source reviewable để xác định giá trị hợp lệ. [Host debug trace](docs/evidence/day2/host-debug-trace.json) và [host debug summary](docs/evidence/day2/host-debug-summary.md) lưu phiên chẩn đoán.

## Remediation

```bash
DAY2_REQUIRED_VALUE=configured COMPOSE_PROJECT_NAME=insighthub-day2-lab \
  docker compose --env-file tools/mcp/day2/.env.example \
  -f docker-compose.yml -f docker-compose.day2.yml --profile day2-debug \
  up -d --force-recreate debug-case
python3 tools/mcp/day2/host_check.py --debug-only --recovery
```

Recreate là bắt buộc vì `docker restart` không nạp env mới. Mutation do operator thực hiện ngoài MCP read-only.

## Retest

MCP trả container mới `024b4d0ea2ea`, `State: running`, và log:

```text
2026-09-22T05:21:56.535440169Z DAY2_CONFIG_OK
```

[Recovery trace](docs/evidence/day2/host-recovery-trace.json) và [recovery summary](docs/evidence/day2/host-recovery-summary.md) xác nhận cả hai tool call thành công. Acceptance cuối gọi lại đủ năm MCP trên trạng thái healthy và PASS 6/6 calls trong [host trace](docs/evidence/day2/host-trace.json).

## Kết quả học tập

- Phân biệt container status với root cause trong log.
- Liên kết evidence runtime với cấu hình reviewable.
- Giữ chẩn đoán read-only và tách remediation sang operator.
- Xác minh recovery bằng output MCP thay vì chỉ dựa vào exit code của lệnh recreate.
