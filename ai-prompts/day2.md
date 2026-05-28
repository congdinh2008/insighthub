# Day 2 AI Prompts — MCP Protocol Integration

> Chứng minh AI-augmented workflow cho Day 2.
> Mỗi prompt ghi rõ: context, constraint, lý do chọn cách tiếp cận, điều chỉnh sau review.

---

## Prompt 1 — Phân tích và cấu hình .mcp.json

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-24 08:00

**Prompt**:
```
Đọc .mcp.json.template trong repo InsightHub.
Tôi cần cấu hình 5 MCP server cho Claude Code:
  1. Filesystem — chỉ cho phép thư mục InsightHub, không cấp $HOME
  2. Docker — dùng Docker Desktop MCP Gateway (không dùng npm package không chính thức)
  3. Kubernetes — read-only, ServiceAccount riêng, không dùng kubeconfig cluster-admin
  4. Prometheus — chuẩn bị cho Day 4 observability
  5. AWS — IAM profile mcp-readonly (ReadOnlyAccess), dùng uvx vì awslabs publish Python

Ràng buộc (Constraint-first):
- Pinned versions — KHÔNG @latest hoặc @main trong bất kỳ args nào
- Credentials qua env field trong .mcp.json, KHÔNG hardcode vào args
- Filesystem allow-list phải là thư mục project, không được là /, $HOME, hay /home/user
- Docker MCP: dùng `docker mcp gateway run` (Docker Desktop official, không cần version pin)
- AWS MCP: dùng uvx vì các package awslabs là Python, không phải npm

Trình bày cấu hình JSON đề xuất kèm giải thích từng field.
```

**Agent output (tóm tắt)**:
- Đề xuất đúng 5 server với pinned versions từ npm/PyPI
- Docker dùng `"command": "docker", "args": ["mcp", "gateway", "run"]` — không có version pin issue
- Chỉ ra rằng path trong args của filesystem server phải là đường dẫn tuyệt đối literal

**Điều chỉnh sau review**:
- ✅ Pinned versions cho tất cả npm packages
- ✅ Docker Desktop gateway approach — không dùng community package không stable
- ❌ Agent đề xuất dùng `$HOME` cho kubeconfig path → reject, dùng đường dẫn tuyệt đối rõ ràng
- ✅ `FASTMCP_LOG_LEVEL=ERROR` cho AWS MCP — giảm noise logs

**Lý do prompt hoạt động**:
- Numbered list server rõ ràng → agent không hallucinate thêm server
- Nêu reason mỗi decision ("không dùng npm package không chính thức") → agent giải thích thay vì tự quyết
- Constraint-first rõ ràng → agent không dùng @latest dù đó là "dễ nhất"

---

## Prompt 2 — Tạo K8s RBAC cho ServiceAccount mcp-readonly

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-24 08:30

**Prompt**:
```
Tạo K8s RBAC YAML cho ServiceAccount mcp-readonly dùng với kubernetes-mcp-server.

Context:
- Namespace: insighthub
- Kubernetes MCP server dùng --read-only flag nhưng vẫn cần RBAC đúng để list/get resources
- Day 4: cần list HPA để query queue depth, scaling status
- Day 5: ChatOps bot query pod status, logs — không cần write verb

Yêu cầu:
1. ServiceAccount trong namespace insighthub
2. ClusterRole với verbs: get, list, watch ONLY — không có create/update/delete/patch
3. ClusterRoleBinding binding ServiceAccount → ClusterRole
4. Resources cần cover: pods, pods/log, deployments, services, events, nodes,
   configmaps, ingresses, jobs, HPA, PVC/PV (cho observability)
5. Sau đó viết script bash tạo kubeconfig riêng từ ServiceAccount token

Ràng buộc:
- Chỉ ClusterRole — không dùng Role namespace-scoped (vì MCP cần xem cross-namespace để debug)
- Không có verb exec, proxy (không cần AI exec vào pod)
- Không có secret read (credentials leak risk)
```

**Agent output**:
- 3 YAML files: serviceaccount.yaml, clusterrole.yaml, clusterrolebinding.yaml
- Bash script tạo kubeconfig từ ServiceAccount token (xử lý cả K8s < 1.24 và ≥ 1.24)
- Đặt trong `infra/k8s/mcp-readonly/`

**Điều chỉnh sau review**:
- ✅ Không có verb `exec` và `proxy` — chính xác như yêu cầu
- ✅ Không có `secrets` trong resources — tốt cho security
- ✅ `metrics.k8s.io` included cho Day 4
- ❌ Agent thêm `pods/exec` "để debug tiện hơn" → review: reject hoàn toàn — AI exec vào pod là unnecessary privilege

**Security note sau review**:
Tôi đã test `kubectl auth can-i exec pods --as=system:serviceaccount:insighthub:mcp-readonly` → `no` ✓
Đây là verify quan trọng nhất — AI không cần exec quyền, chỉ cần đọc log.

**Lý do prompt hoạt động**:
- Nêu rõ "Không có create/update/delete/patch" → agent không "thêm tiện" unauthorized verb
- "Không có verb exec, proxy" rõ ràng → agent không thêm vì "debug tiện hơn"
- Cross-reference Day 4/5 → agent thêm HPA resources mà không cần nhắc lại

---

## Prompt 3 — Debug session InsightHub qua MCP (case study)

**Tool**: Claude Code (claude-sonnet-4-6) — sử dụng Docker MCP + K8s MCP
**Time**: 2026-05-24 09:00
**Thiết lập**: Trainer inject lỗi: DATABASE_URL → hostname sai `postgres-wrong`

**Prompt**:
```
Service nào của InsightHub đang không khỏe?
Kiểm tra container/pod, lấy log, và cho tôi biết nguyên nhân gốc.
```

**Tool calls agent thực hiện**:
1. `docker__list_containers` → thấy `ingestion-worker` status `restarting`
2. `docker__get_container_logs` (tail=50) → thấy "No such host: postgres-wrong"
3. `docker__inspect_container` → thấy `DATABASE_URL=...@postgres-wrong:5432/...`

**RCA agent trả về**:
```
Root cause: DATABASE_URL trỏ hostname postgres-wrong không tồn tại.
Postgres service name trong compose là "postgres" (không phải "postgres-wrong").
Fix: sửa DATABASE_URL → @postgres:5432 và restart worker.
```

**Điều chỉnh sau review**:
- ✅ Agent chỉ READ — không tự sửa file hay restart service (đúng behavior)
- ✅ Cite evidence cụ thể: log line + env var — không hallucinate
- Thêm verify: sau fix, poll `/api/documents` status → "ready" trong 30s ✓

**Lý do prompt ngắn mà hoạt động**:
- MCP đã cung cấp đủ context (container list, logs, env vars) → agent không cần guess
- Prompt không cần specify tool nào dùng — agent tự chọn tool phù hợp
- "Cho tôi biết nguyên nhân gốc" → agent trả RCA, không chỉ liệt kê facts

**Thời gian thực tế**:
- Không có MCP: ~25 phút (12 kubectl/docker command thủ công)
- Có MCP: ~45 giây (1 natural language query → 3 tool calls → RCA)

---

## Prompt 4 — Verify least-privilege: AWS MCP write action test

**Tool**: Claude Code (claude-sonnet-4-6) — sử dụng AWS MCP
**Time**: 2026-05-24 09:20

**Prompt**:
```
Dùng AWS MCP, thử tạo 1 S3 bucket tên mcp-test-bucket trong us-east-1.
Tôi muốn xem IAM profile mcp-readonly có bị block không.
Sau đó liệt kê các EC2 instance đang running để verify read access hoạt động.
```

**Kết quả**:
1. `s3:CreateBucket` → AccessDenied ✓ (least-privilege hoạt động)
2. `ec2:DescribeInstances` → trả danh sách instances ✓ (read access hoạt động)

**Điều chỉnh sau review**:
- ✅ Agent thực thi cả 2 actions theo đúng prompt
- ✅ Kết quả chứng minh: write bị block, read cho phép — policy hoạt động đúng
- Thêm vào debug-session-day2.md như bằng chứng least-privilege

**Bài học**:
Verify least-privilege bằng cách **chủ động test write action** quan trọng hơn chỉ đọc policy document.
"Trust but verify" — không tin vào policy description, test thật.
