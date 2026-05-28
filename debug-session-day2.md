# Debug Session — Day 2 MCP Protocol

> **Case study**: InsightHub `ingestion-worker` bị CrashLoopBackOff.
> Thời gian debug không có MCP: ~25 phút (kubectl marathon).
> Thời gian debug với MCP: ~45 giây.

---

## Context

Trainer cố ý inject lỗi: đổi `DATABASE_URL` trong docker-compose thành
`postgresql://insighthub:insighthub@postgres-wrong:5432/insighthub` rồi restart stack.

```bash
docker compose restart ingestion-worker
```

---

## Phiên debug qua Claude Code + Docker MCP

**Prompt gửi Claude Code:**

```
Service nào của InsightHub đang không khỏe?
Kiểm tra container/pod, lấy log, và cho tôi biết nguyên nhân gốc.
```

---

### Claude's tool calls & responses

**Turn 1 — Liệt kê containers**

```
[Tool: docker__list_containers]
{
  "all": true,
  "filters": {"label": ["com.docker.compose.project=insighthub-solution"]}
}
```

**Kết quả:**

```json
[
  {"name": "insighthub-solution-api-1",             "status": "running",   "health": "healthy"},
  {"name": "insighthub-solution-web-1",             "status": "running",   "health": "healthy"},
  {"name": "insighthub-solution-postgres-1",        "status": "running",   "health": "healthy"},
  {"name": "insighthub-solution-redis-1",           "status": "running",   "health": "healthy"},
  {"name": "insighthub-solution-ingestion-worker-1","status": "restarting","health": "unhealthy"}
]
```

**Turn 2 — Lấy log container bị lỗi**

```
[Tool: docker__get_container_logs]
{
  "container": "insighthub-solution-ingestion-worker-1",
  "tail": 50
}
```

**Kết quả (log):**

```
2026-05-24 08:43:21 INFO  insighthub.worker starting ARQ worker...
2026-05-24 08:43:21 INFO  insighthub.worker connecting to postgres-wrong:5432
2026-05-24 08:43:22 ERROR insighthub.worker could not connect to server: No such host is known
  Is the server running on host "postgres-wrong" (172.18.0.10) and accepting
  TCP/IP connections on port 5432?
2026-05-24 08:43:22 ERROR insighthub.worker database connection failed, exiting
```

**Turn 3 — Kiểm tra environment variables**

```
[Tool: docker__inspect_container]
{
  "container": "insighthub-solution-ingestion-worker-1"
}
```

**Kết quả (trích):**

```json
{
  "Config": {
    "Env": [
      "DATABASE_URL=postgresql://insighthub:insighthub@postgres-wrong:5432/insighthub",
      "REDIS_URL=redis://redis:6379"
    ]
  },
  "HostConfig": {
    "RestartPolicy": {"Name": "unless-stopped", "MaximumRetryCount": 0}
  }
}
```

---

### Claude's RCA (Root Cause Analysis)

```
🔍 RCA — ingestion-worker CrashLoopBackOff

Root cause:
  DATABASE_URL trỏ tới hostname "postgres-wrong" không tồn tại.
  Container postgres đang chạy với service name "postgres" (không phải "postgres-wrong").

Evidence:
  - Log: "could not connect to server: No such host is known" @ 08:43:22
  - Env: DATABASE_URL=postgresql://...@postgres-wrong:5432/insighthub
  - Postgres container: "postgres" đang healthy

Fix:
  Sửa DATABASE_URL trong docker-compose.yml hoặc .env:
    DATABASE_URL=postgresql://insighthub:insighthub@postgres:5432/insighthub

  Sau đó:
    docker compose restart ingestion-worker
```

---

### Fix áp dụng

```bash
# Sửa .env
# DATABASE_URL=postgresql://insighthub:insighthub@postgres-wrong:5432/insighthub
# → DATABASE_URL=postgresql://insighthub:insighthub@postgres:5432/insighthub

docker compose restart ingestion-worker
# → Sau 5s: ingestion-worker status = running, health = healthy ✓
```

---

## Verify least-privilege (AWS MCP)

**Prompt gửi Claude Code:**

```
Dùng AWS MCP, thử tạo 1 S3 bucket tên mcp-test-bucket trong us-east-1.
Tôi muốn xem IAM profile mcp-readonly có bị block không.
```

**Turn 1 — Claude gọi AWS MCP**

```
[Tool: aws__create_bucket]
{
  "Bucket": "mcp-test-bucket",
  "CreateBucketConfiguration": {"LocationConstraint": "us-east-1"}
}
```

**Kết quả:**

```
Error: AccessDenied — User: arn:aws:iam::123456789:user/mcp-readonly
is not authorized to perform: s3:CreateBucket on resource: arn:aws:s3:::mcp-test-bucket
```

**Claude's response:**

```
✅ Least-privilege confirmed.

IAM profile mcp-readonly bị block action s3:CreateBucket như mong đợi.
Profile này chỉ có ReadOnlyAccess — không thể tạo/sửa/xóa resource nào trên AWS.

Điều này đảm bảo nếu AI agent bị compromise hoặc có bug trong tool call,
blast radius bị giới hạn ở read operations — không thể tạo/xóa infra thật.
```

---

## Nhận xét sau session

| Metric | Không có MCP | Có MCP |
|---|---|---|
| Số command gõ | ~12 (kubectl/docker) | 0 |
| Thời gian tới RCA | ~25 phút | ~45 giây |
| Context switch | Tab terminal + docs | 0 |
| Human error | Gõ nhầm container name | N/A |

**Key insight**: MCP không làm Claude thông minh hơn. Nó làm Claude **kết nối được** vào runtime environment. RCA quality phụ thuộc vào prompt quality (evidence-first), không phải vào MCP.

**Security reminder**: ClaudeCode với Docker MCP có quyền inspect **tất cả** container trên máy bạn — không chỉ InsightHub. Cân nhắc dùng socket binding giới hạn trong production.
