#!/usr/bin/env bash
# InsightHub — Script deploy toàn bộ dự án lên Kubernetes Local (Minikube / Docker Desktop / Kind)
# Chạy script từ thư mục gốc của repo: bash scripts/deploy-k8s-local.sh

set -euo pipefail

# Màu sắc hiển thị
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Kiểm tra các công cụ yêu cầu
log_info "Kiểm tra các công cụ yêu cầu..."
for cmd in docker kubectl helm; do
    if ! command -v "$cmd" &>/dev/null; then
        log_error "Chưa cài đặt '$cmd'. Hãy cài đặt trước khi chạy script."
        exit 1
    fi
done
log_info "Các công cụ cơ bản đã đầy đủ."

# 2. Kiểm tra Docker Daemon
if ! docker info &>/dev/null; then
    log_error "Docker daemon chưa chạy. Hãy mở Docker Desktop và thử lại."
    exit 1
fi

# 3. Xác định Kubernetes Cluster hiện tại
log_info "Xác định Kubernetes context hiện tại..."
CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || echo "")
if [ -z "$CURRENT_CONTEXT" ]; then
    log_error "Không tìm thấy Kubernetes context nào. Hãy khởi chạy Minikube hoặc Docker Desktop Kubernetes."
    exit 1
fi
log_info "Kubernetes Context hiện tại: $CURRENT_CONTEXT"

# Phân loại cluster type
CLUSTER_TYPE="unknown"
if [[ "$CURRENT_CONTEXT" == *"minikube"* ]]; then
    CLUSTER_TYPE="minikube"
elif [[ "$CURRENT_CONTEXT" == *"kind"* ]]; then
    CLUSTER_TYPE="kind"
elif [[ "$CURRENT_CONTEXT" == *"docker-desktop"* ]]; then
    CLUSTER_TYPE="docker-desktop"
elif [[ "$CURRENT_CONTEXT" == *"rancher-desktop"* ]]; then
    CLUSTER_TYPE="rancher-desktop"
fi
log_info "Loại cluster được phát hiện: $CLUSTER_TYPE"

# 4. Cấu hình Docker Environment cho Minikube nếu cần
if [ "$CLUSTER_TYPE" = "minikube" ]; then
    log_info "Minikube được phát hiện. Đang cấu hình Docker env để build trực tiếp vào Minikube..."
    # Kiểm tra minikube status
    if ! minikube status &>/dev/null; then
        log_warn "Minikube chưa chạy. Đang cố gắng khởi động minikube..."
        minikube start --driver=docker
    fi
    # Switch shell docker context sang minikube docker-daemon
    eval $(minikube docker-env)
fi

# 5. Build các Docker Images cho dự án
log_info "Bắt đầu build các Docker Images của InsightHub..."

log_info "Building api..."
docker build -t insighthub-api:latest ./api

log_info "Building web..."
docker build -t insighthub-web:latest ./web

log_info "Building worker..."
docker build -t insighthub-worker:latest -f ingestion-worker/Dockerfile .

log_info "Đã build xong các Docker Images."

# 6. Load images nếu sử dụng Kind cluster
if [ "$CLUSTER_TYPE" = "kind" ]; then
    log_info "Đang load images vào Kind cluster..."
    kind load docker-image insighthub-api:latest
    kind load docker-image insighthub-worker:latest
    kind load docker-image insighthub-web:latest
    log_info "Đã load images vào Kind."
fi

# 7. Đọc API Keys từ file .env
log_info "Đang kiểm tra và đọc API Keys từ file .env..."
ENV_FILE=""
if [ -f ".env" ]; then
    ENV_FILE=".env"
elif [ -f "chatops-bot/.env" ]; then
    ENV_FILE="chatops-bot/.env"
else
    log_warn "Không tìm thấy file .env ở thư mục gốc hoặc chatops-bot/.env. Sẽ dùng giá trị rỗng cho các API Key."
fi

# Hàm đọc biến từ .env
get_env_var() {
    local var_name=$1
    if [ -n "$ENV_FILE" ]; then
        # Tìm dòng gán biến (bỏ qua comment và khoảng trắng)
        grep -v '^#' "$ENV_FILE" | grep "$var_name=" | head -n1 | cut -d'=' -f2- | tr -d ' "' | sed 's/#.*//' | xargs || echo ""
    else
        echo ""
    fi
}

GEMINI_API_KEY=$(get_env_var "GEMINI_API_KEY")
ANTHROPIC_API_KEY=$(get_env_var "ANTHROPIC_API_KEY")
VOYAGE_API_KEY=$(get_env_var "VOYAGE_API_KEY")
OPENAI_API_KEY=$(get_env_var "OPENAI_API_KEY")
DEEPSEEK_API_KEY=$(get_env_var "DEEPSEEK_API_KEY")

# Trị giá mặc định nếu lấy từ môi trường hiện tại
GEMINI_API_KEY=${GEMINI_API_KEY:-$(printenv GEMINI_API_KEY || echo "")}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-$(printenv ANTHROPIC_API_KEY || echo "")}
VOYAGE_API_KEY=${VOYAGE_API_KEY:-$(printenv VOYAGE_API_KEY || echo "")}
OPENAI_API_KEY=${OPENAI_API_KEY:-$(printenv OPENAI_API_KEY || echo "")}
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-$(printenv DEEPSEEK_API_KEY || echo "")}

mask_key() {
    local key=$1
    if [ -z "$key" ]; then
        echo "chưa cấu hình (để trống)"
    else
        echo "${key:0:6}...${key: -6}"
    fi
}

echo -e "   - GEMINI_API_KEY:    $(mask_key "$GEMINI_API_KEY")"
echo -e "   - ANTHROPIC_API_KEY: $(mask_key "$ANTHROPIC_API_KEY")"
echo -e "   - VOYAGE_API_KEY:    $(mask_key "$VOYAGE_API_KEY")"
echo -e "   - OPENAI_API_KEY:    $(mask_key "$OPENAI_API_KEY")"
echo -e "   - DEEPSEEK_API_KEY:  $(mask_key "$DEEPSEEK_API_KEY")"

# 8. Tạo Namespace nếu chưa tồn tại
NAMESPACE="insighthub-dev"
log_info "Tạo namespace '$NAMESPACE' nếu chưa có..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Dọn dẹp các deployment cũ để tránh xung đột field manager (ví dụ từ kubectl set env trước đó)
log_info "Dọn dẹp các deployment cũ để tránh xung đột field manager..."
kubectl delete deployment api ingestion-worker web -n "$NAMESPACE" --ignore-not-found --wait=true

# 9. Deploy dự án sử dụng Helm Chart
log_info "Đang deploy InsightHub thông qua Helm..."
helm upgrade --install insighthub ./infra/helm/insighthub \
  -f ./infra/helm/values-dev.yaml \
  -n "$NAMESPACE" \
  --set api.apiKeys.geminiApiKey="$GEMINI_API_KEY" \
  --set api.apiKeys.anthropicApiKey="$ANTHROPIC_API_KEY" \
  --set api.apiKeys.voyageApiKey="$VOYAGE_API_KEY" \
  --set api.apiKeys.openaiApiKey="$OPENAI_API_KEY" \
  --set api.apiKeys.deepseekApiKey="$DEEPSEEK_API_KEY"

# 10. Chờ các pod sẵn sàng
log_info "Đợi các deployement Rollout hoàn tất..."
kubectl rollout status deployment/postgres -n "$NAMESPACE" --timeout=60s || log_warn "Postgres deployment chưa sẵn sàng hoàn toàn"
kubectl rollout status deployment/redis -n "$NAMESPACE" --timeout=30s || log_warn "Redis deployment chưa sẵn sàng hoàn toàn"
kubectl rollout status deployment/api -n "$NAMESPACE" --timeout=60s || log_warn "API deployment chưa sẵn sàng hoàn toàn"
kubectl rollout status deployment/ingestion-worker -n "$NAMESPACE" --timeout=60s || log_warn "Worker deployment chưa sẵn sàng hoàn toàn"
kubectl rollout status deployment/web -n "$NAMESPACE" --timeout=60s || log_warn "Web dashboard deployment chưa sẵn sàng hoàn toàn"

echo -e "\n========================================================"
echo -e "🎉 ${GREEN}DEPLOY HOÀN TẤT LÊN KUBERNETES LOCAL!${NC}"
echo -e "========================================================"
kubectl get pods -n "$NAMESPACE"
echo -e "--------------------------------------------------------"
log_info "Cách truy cập các service trên local:"

if [ "$CLUSTER_TYPE" = "minikube" ]; then
    echo -e "1. Lấy URL của Web Dashboard (Next.js):"
    echo -e "   👉 ${YELLOW}minikube service web --url -n $NAMESPACE${NC}"
    echo -e "2. Lấy URL của API Service (FastAPI):"
    echo -e "   👉 ${YELLOW}minikube service api --url -n $NAMESPACE${NC}"
else
    echo -e "1. Truy cập qua NodePort của cluster (nếu hỗ trợ):"
    echo -e "   - Web Dashboard: ${YELLOW}http://localhost:30030${NC}"
    echo -e "   - API Docs:      ${YELLOW}http://localhost:30080/docs${NC}"
    echo -e "\n2. Hoặc sử dụng Port Forward thủ công:"
    echo -e "   - Web Dashboard: ${YELLOW}kubectl port-forward svc/web 3000:3000 -n $NAMESPACE${NC}"
    echo -e "     (Mở link: http://localhost:3000)"
    echo -e "   - API Docs:      ${YELLOW}kubectl port-forward svc/api 8000:8000 -n $NAMESPACE${NC}"
    echo -e "     (Mở link: http://localhost:8000/docs)"
fi
echo -e "========================================================"
