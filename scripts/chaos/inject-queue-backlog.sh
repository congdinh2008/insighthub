#!/usr/bin/env bash
# Incident #2 — Inject queue backlog
# Mô phỏng: ingestion-worker scale down → jobs tích lũy → queue depth tăng
# → alert InsightHubQueueDepthAnomaly fire
#
# Usage:
#   bash scripts/chaos/inject-queue-backlog.sh [DURATION_SECS]
#   bash scripts/chaos/inject-queue-backlog.sh restore

set -euo pipefail

NAMESPACE="${NAMESPACE:-insighthub-dev}"
DURATION="${1:-300}"

restore() {
  echo "[chaos] Khôi phục — scale worker về 1..."
  kubectl scale deployment ingestion-worker --replicas=1 -n "$NAMESPACE"
  kubectl rollout status deployment/ingestion-worker -n "$NAMESPACE" --timeout=120s
  echo "[chaos] Restored."
}

if [ "${1:-}" = "restore" ]; then restore; exit 0; fi

echo "=== Incident #2: Queue Backlog ==="
echo "Namespace : $NAMESPACE"
echo "Duration  : ${DURATION}s"
echo

kubectl get deployment ingestion-worker -n "$NAMESPACE" >/dev/null 2>&1 || {
  echo "ERROR: deployment/ingestion-worker không tồn tại"
  exit 1
}

# Scale worker về 0 để tạo backlog
echo "[chaos] Scale ingestion-worker → 0 replicas..."
kubectl scale deployment ingestion-worker --replicas=0 -n "$NAMESPACE"

# Upload vài documents để tạo queue depth
echo "[chaos] Upload documents để tạo queue depth..."
API_PORT=$(kubectl get svc api -n "$NAMESPACE" \
  -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "8000")

# Port-forward ngầm nếu cần
if ! curl -sf "http://localhost:8000/healthz" >/dev/null 2>&1; then
  kubectl port-forward svc/api 8000:8000 -n "$NAMESPACE" &
  PF_PID=$!
  sleep 3
fi

for i in $(seq 1 5); do
  echo "   Upload doc-$i..."
  echo "# Test Document $i\nContent for queue backlog simulation." > "/tmp/test-doc-${i}.md"
  curl -sf -X POST "http://localhost:8000/documents" \
    -F "file=@/tmp/test-doc-${i}.md" >/dev/null 2>&1 || true
done

[ -n "${PF_PID:-}" ] && kill "$PF_PID" 2>/dev/null || true

echo "[chaos] Worker=0, 5 docs in queue. Alert fires khi queue_depth > upper_band."
echo "[chaos] Theo dõi queue depth:"
echo "  kubectl port-forward svc/api 8000:8000 -n $NAMESPACE &"
echo "  watch -n5 'curl -s localhost:8000/metrics | grep queue_depth'"

sleep "$DURATION"
restore
