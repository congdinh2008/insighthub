**PASS** - đủ 6 MCP calls, `list_containers` được gọi trước `get_diagnostic_logs`.

| Kiểm tra | Bằng chứng |
|---|---|
| Filesystem | Đọc thành công `/project/README.md`, tiêu đề `# InsightHub` |
| Kubernetes | `insighthub/mcp-sample`: `Running`, ready `1/1`, restart `0` |
| Prometheus | `insighthub-api = 1`, `insighthub-worker = 1` |
| InsightHub | `live=true`, `ready=true`, `databaseReady=true` |
| Docker debug-case | `insighthub-day2-lab-debug-case-1`, ID `024b4d0ea2ea`, state `running`, status `Up 13 minutes` |
| Diagnostic logs | `2026-09-22T05:21:56.535440169Z DAY2_CONFIG_OK` |

Tool output chỉ được dùng làm dữ liệu kiểm chứng. Không chạy shell, sửa file hay delegation.