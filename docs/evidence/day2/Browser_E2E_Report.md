# Day 02 - Computer Use / Control Browser E2E

Ngày chạy: 22/09/2026. Codex Computer Use điều khiển MCP Inspector 2.7.0, InsightHub và Prometheus UI trên browser local. Năm MCP dùng backend live; ứng dụng RAG dùng fixture theo cấu hình lab.

| Case | Kết quả thực tế | Evidence |
|---|---|---|
| B01 Filesystem | Inspector kết nối `filesystem`; danh sách chỉ có 3 tool đọc; `read_file("/project/README.md")` trả đúng source InsightHub | [Screenshot](inspector-filesystem.png), [profile](toolkit-profile.json) |
| B02 Docker operations | Inspector kết nối `docker-operations`; `get_diagnostic_logs` trả `DAY2_CONFIG_OK` sau recovery | [Screenshot](inspector-docker.png), [recovery trace](host-recovery-trace.json) |
| B03 Kubernetes | Inspector kết nối `kubernetes`; `pods_list_in_namespace("insighthub")` trả `mcp-sample` ở trạng thái `1/1 Running` | [Screenshot](inspector-kubernetes.png) |
| B04 Prometheus MCP | Inspector kết nối `prometheus`; PromQL trả 2 series `insighthub-api` và `insighthub-worker`, cùng giá trị `1` | [Screenshot](inspector-prometheus.png), [live check](live-check.json) |
| B05 InsightHub MCP | Inspector kết nối `insighthub`; `insighthub_health` trả `live=true`, `ready=true`, `databaseReady=true` | [Screenshot](inspector-insighthub.png) |
| B06 Web upload/chat | Upload `so-tay-van-hanh.md` bằng file chooser; tài liệu chuyển `ready`, có 1 chunk; chat trả đoạn fixture và nguồn `so-tay-van-hanh.md` | [Screenshot](web-upload-chat.png) |
| B07 Prometheus UI | Query `up{job=~"insighthub-(api|worker)"}` hiển thị `Result series: 2`; cả hai series bằng `1` | [Screenshot](prometheus-query.png) |
| B08 Browser console | Không có warning hoặc error trong InsightHub và Prometheus UI ở lượt E2E | [Console result](browser-console.json) |

Kết quả: 8/8 browser scenarios PASS. Permission denials được kiểm bằng live SDK và backend authorization trong [probe-all.json](probe-all.json) và [live-check.json](live-check.json), không dùng screenshot thay cho assertion máy kiểm được.
