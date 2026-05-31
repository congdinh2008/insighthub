#!/usr/bin/env bash
# Incident #3 — Inject error burst (HTTP 5xx)
# Mô phỏng: database connection lỗi → chat endpoint trả 500 liên tục
# → error rate vượt 5% → alert InsightHubErrorRateAnomaly
#
# Cơ chế: patch env DATABASE_URL thành invalid → API không kết nối được DB
# → mọi request cần DB đều 500
#
# Usage:
#   bash scripts/chaos/inject-error-burst.sh [DURATION_SECS]
#   bash scripts/chaos/inject-error-burst.sh restore

set -euo pipefail

NAMESPACE="${NAMESPACE:-insighthub-dev}"
DURATION="${1:-180}"

# Lưu DATABASE_URL gốc
ORIG_DB_URL=$(kubectl get deployment api -n "$NAMESPACE" \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="DATABASE_URL")].value}' 2>/dev/null \
  || echo "postgresql://insighthub:insighthub@postgres:5432/insighthub")

restore() {
  echo "[chaos] Khôi phục DATABASE_URL..."
  kubectl set env deployment/api "DATABASE_URL=${ORIG_DB_URL}" -n "$NAMESPACE"
  kubectl rollout status deployment/api -n "$NAMESPACE" --timeout=120s
  echo "[chaos] Restored."
}

if [ "${1:-}" = "restore" ]; then restore; exit 0; fi

echo "=== Incident #3: Error Burst (DB Connection Failure) ==="
echo "Namespace : $NAMESPACE"
echo "Duration  : ${DURATION}s"
echo

kubectl get deployment api -n "$NAMESPACE" >/dev/null 2>&1 || {
  echo "ERROR: deployment/api không tồn tại"
  exit 1
}

# Inject bad DATABASE_URL
echo "[chaos] Inject invalid DATABASE_URL..."
kubectl set env deployment/api \
  "DATABASE_URL=postgresql://invalid:invalid@nonexistent-host:5432/insighthub" \
  -n "$NAMESPACE"

kubectl rollout status deployment/api -n "$NAMESPACE" --timeout=120s

echo "[chaos] Injected. Gửi requests để tạo error traffic..."

# Port-forward và spam requests
kubectl port-forward svc/api 8001:8000 -n "$NAMESPACE" &
PF_PID=$!
sleep 3

for i in $(seq 1 20); do
  curl -sf -X POST "http://localhost:8001/chat" \
    -H "Content-Type: application/json" \
    -d '{"question":"test"}' >/dev/null 2>&1 || true
done

kill "$PF_PID" 2>/dev/null || true

echo "[chaos] Error burst injected. Alert fires khi error_rate > 5%."
echo "[chaos] Theo dõi:"
echo "  kubectl logs -f deployment/api -n $NAMESPACE | grep ERROR"

sleep "$DURATION"
restore
