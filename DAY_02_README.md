# DAY 02 — MCP Protocol Integration
## Hướng dẫn Mentor: Demo & Lab Step-by-Step

> **Đối tượng:** Trainer / Mentor hướng dẫn học viên  
> **Thời lượng:** 2.5 giờ (150 phút)  
> **Ngày:** Day 2 trong Module 7 — AI-Native DevOps  
> **Branch học viên làm việc:** `day2-mcp`

---

## Mục lục

1. [Tổng quan & Mục tiêu](#1-tổng-quan--mục-tiêu)
2. [Chuẩn bị trước buổi (Mentor Checklist)](#2-chuẩn-bị-trước-buổi-mentor-checklist)

---

## 1. Tổng quan & Mục tiêu

### Bức tranh lớn

Day 1 học viên refactor InsightHub thành 5-service async với Redis queue. Họ đã biết dùng Claude Code đọc file local. Vấn đề: **Claude không thể tự kết nối vào cluster, docker engine, hay AWS**. Phải gõ thủ công.

Day 2 giải quyết điều đó bằng **MCP (Model Context Protocol)** — chuẩn kết nối AI agent với tool và data source bên ngoài. Kết quả: debug pod crash từ 25 phút → 45 giây.

### Mục tiêu học viên đạt được cuối Day 2

| # | Mục tiêu | Verify |
|---|---|---|
| 1 | Giải thích kiến trúc MCP: Host/Client/Server, JSON-RPC, transports | Trả lời quiz |
| 2 | Cấu hình ≥ 4 MCP server (filesystem, docker, k8s, prometheus) | `claude mcp list` Connected |
| 3 | Debug InsightHub bằng natural language qua MCP | `debug-session-day2.md` |
| 4 | Áp dụng least-privilege khi cấp quyền cho AI agent | RBAC verify + AWS deny test |

### Artifacts học viên nộp

```
1. .mcp.json         — cấu hình ≥ 4 servers, pinned versions
2. infra/k8s/mcp-readonly/  — ServiceAccount + ClusterRole + ClusterRoleBinding YAML
3. debug-session-day2.md    — log phiên debug InsightHub qua MCP
4. ai-prompts/day2.md       — ≥ 3 prompts có giải thích
```

---

## 2. Chuẩn bị trước buổi (Mentor Checklist)

### 2.1. Kiểm tra environment

```bash
# Verify Claude Code CLI
claude --version        # phải ≥ 1.x

# Verify tools
node --version          # ≥ 20
docker desktop          # chạy và version ≥ 4.40 (Docker MCP Gateway support)
kubectl version         # kết nối được lab cluster hoặc minikube

# Verify uv (cho AWS MCP)
uv --version            # ≥ 0.5
uvx awslabs.aws-api-mcp-server@1.3.38 --help 2>&1 | head -5
```

### 2.2. Chuẩn bị lab cluster

```bash
# Option A: minikube (nếu không có EKS)
minikube start --driver=docker --cpus=2 --memory=4g
kubectl get nodes       # Ready

# Tạo namespace insighthub (cho RBAC ServiceAccount mcp-readonly)
kubectl create namespace insighthub --dry-run=client -o yaml | kubectl apply -f -

# Apply RBAC từ solution repo (demo trước)
kubectl apply -f infra/k8s/mcp-readonly/serviceaccount.yaml
kubectl apply -f infra/k8s/mcp-readonly/clusterrole.yaml
kubectl apply -f infra/k8s/mcp-readonly/clusterrolebinding.yaml

# Deploy InsightHub lên cluster (để có pods để debug)
# Nếu dùng minikube -- phải build image vào docker daemon của minikube:
eval $(minikube docker-env)

# Build TAT CA 3 image (pullPolicy: Never trong values-dev.yaml)
docker build -t insighthub-api:latest    ./api/
docker build -t insighthub-worker:latest -f ./ingestion-worker/Dockerfile .
docker build -t insighthub-web:latest    ./web/

# Deploy vào namespace insighthub-dev (namespace riêng cho workload)
helm upgrade --install insighthub infra/helm/insighthub \
  -f infra/helm/values-dev.yaml \
  -n insighthub-dev --create-namespace
kubectl get pods -n insighthub-dev   # cần có pods running
```

> **Về 2 namespace trong lab này:**
>
> | Namespace | Dùng cho | Tại sao tách? |
> |---|---|---|
> | `insighthub` | ServiceAccount `mcp-readonly` (RBAC) | Demo least-privilege — kubeconfig read-only trỏ vào đây |
> | `insighthub-dev` | Workload thật (api, worker, web, redis, postgres) | Tách biệt app khỏi RBAC object |
>
> **Hệ quả thực tế:** Khi debug workload, luôn thêm `-n insighthub-dev`. Kubeconfig read-only (bước 2.4) mặc định context namespace là `insighthub` — cần override hoặc truyền namespace tường minh khi query pod.



### 2.3. Inject lỗi cố ý cho demo debug (Bước 4)

```bash
# Cách 1: docker compose (nếu demo local)
# Sửa .env: đặt DATABASE_URL=postgresql://insighthub:insighthub@postgres-wrong:5432/insighthub
docker compose up --force-recreate -d ingestion-worker
# → ingestion-worker sẽ crash vì không resolve được host "postgres-wrong"
docker compose ps   # verify ingestion-worker restart loop

# Cách 2: kubectl patch (nếu demo K8s / minikube)
kubectl set env deployment/ingestion-worker \
  DATABASE_URL=postgresql://insighthub:insighthub@postgres-wrong:5432/insighthub \
  -n insighthub-dev
# → worker sẽ CrashLoopBackOff
kubectl get pods -n insighthub-dev   # verify worker crash
```

> **Lưu ý cho Helm 4 / server-side apply:** `kubectl set env` là cách nhanh để inject lỗi demo, nhưng nó làm field `DATABASE_URL` thuộc manager `kubectl-set`. Sau demo, nên revert bằng Helm với `--force-conflicts` như bước 4, không tiếp tục `kubectl set env` để "sửa tay"; nếu không lần `helm upgrade` sau có thể báo conflict ownership.

### 2.4. Tạo kubeconfig read-only cho demo

```bash
# Tạo token cho ServiceAccount mcp-readonly
TOKEN=$(kubectl create token mcp-readonly -n insighthub --duration=8760h)

# Lấy cluster info
CLUSTER_SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
kubectl config view --minify --raw \
  -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' \
  | base64 -d > /tmp/mcp-ca.crt

# Dùng biến $HOME thay vì ~ để tránh lỗi tilde không expand khi dùng --flag=~/path
KUBECONFIG_PATH="$HOME/.kube/mcp-viewer.kubeconfig"
mkdir -p "$HOME/.kube"

# Build kubeconfig
kubectl config set-cluster insighthub-mcp \
  --server="$CLUSTER_SERVER" \
  --certificate-authority=/tmp/mcp-ca.crt \
  --embed-certs=true \
  --kubeconfig="$KUBECONFIG_PATH"

kubectl config set-credentials mcp-readonly \
  --token="$TOKEN" \
  --kubeconfig="$KUBECONFIG_PATH"

kubectl config set-context insighthub-mcp \
  --cluster=insighthub-mcp \
  --user=mcp-readonly \
  --namespace=insighthub \
  --kubeconfig="$KUBECONFIG_PATH"

kubectl config use-context insighthub-mcp \
  --kubeconfig="$KUBECONFIG_PATH"

# ⚠️  Minikube only: CA cert không đạt chuẩn X.509 mới (thiếu SAN), Go 1.21+ từ chối
# khi cert được embed. Bật insecure-skip-tls-verify cho local dev:
kubectl config set-cluster insighthub-mcp \
  --insecure-skip-tls-verify=true \
  --kubeconfig="$KUBECONFIG_PATH"
# Trên EKS thật: không cần bước này — CA cert của EKS đạt chuẩn X.509

# Verify
kubectl --kubeconfig "$KUBECONFIG_PATH" get pods -n insighthub
# → No resources found (hoặc list pods) ✓
kubectl auth can-i delete pods -n insighthub \
  --as=system:serviceaccount:insighthub:mcp-readonly
# → no ✓
kubectl auth can-i get pods -n insighthub \
  --as=system:serviceaccount:insighthub:mcp-readonly
# → yes ✓
```

### 2.5. Setup AWS IAM mcp-readonly (nếu dùng AWS)

```bash
# Tạo IAM user mcp-readonly với policy ReadOnlyAccess
# Sau đó tạo Access Key và config AWS profile
aws configure --profile mcp-readonly
# AWS Access Key ID: ...
# AWS Secret Access Key: ...
# Default region: ap-southeast-1

# Verify
aws --profile mcp-readonly sts get-caller-identity
# → trả về user ARN của mcp-readonly
```

### 2.6. Chuẩn bị .mcp.json hoạt động

```bash
# Copy từ solution và điền đường dẫn thật
cp .mcp.json.template .mcp.json

# Sửa các placeholder:
# /PATH/TO/insighthub → $(pwd)
# /PATH/TO/.kube/mcp-viewer.kubeconfig → $HOME/.kube/mcp-viewer.kubeconfig

# Test từng server
claude mcp list
# → filesystem: ✓ Connected
# → docker: ✓ Connected
# → kubernetes: ✓ Connected
# → prometheus: ✓ Connected
# → aws: ✓ Connected
```

---