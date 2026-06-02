#!/usr/bin/env bash
# Incident #1 — Inject LLM latency spike
# Mô phỏng: LLM provider chậm → rag_query_latency tăng vọt → alert InsightHubLLMLatencyAnomaly
#
# Cơ chế: patch deployment api với env LLM_CHAOS_LATENCY_MS
# API code đọc env này trong llm.py để delay thêm trước khi trả response.
# Sau 5 phút alert sẽ fire (InsightHubLLMLatencyAnomaly, for: 2m).
#
# Usage:
#   bash scripts/chaos/inject-llm-latency.sh [DELAY_MS] [DURATION_SECS]
#   bash scripts/chaos/inject-llm-latency.sh 8000 300   # 8s delay, 5 phút
#   bash scripts/chaos/inject-llm-latency.sh restore     # khôi phục

set -euo pipefail

NAMESPACE="${NAMESPACE:-insighthub-dev}"
DELAY_MS="${1:-8000}"
DURATION="${2:-300}"

restore() {
  echo "[chaos] Khôi phục — xóa LLM_CHAOS_LATENCY_MS..."
  kubectl set env deployment/api LLM_CHAOS_LATENCY_MS- -n "$NAMESPACE"
  kubectl rollout status deployment/api -n "$NAMESPACE" --timeout=60s
  echo "[chaos] Restored."
}

if [ "${1:-}" = "restore" ]; then restore; exit 0; fi

echo "=== Incident #1: LLM Latency Spike ==="
echo "Namespace : $NAMESPACE"
echo "Delay     : ${DELAY_MS}ms"
echo "Duration  : ${DURATION}s"
echo

# Kiểm tra kết nối
kubectl get deployment api -n "$NAMESPACE" >/dev/null 2>&1 || {
  echo "ERROR: deployment/api không tồn tại trong namespace $NAMESPACE"
  exit 1
}

# Inject chaos
echo "[chaos] Inject LLM_CHAOS_LATENCY_MS=${DELAY_MS}..."
kubectl set env deployment/api \
  "LLM_CHAOS_LATENCY_MS=${DELAY_MS}" \
  -n "$NAMESPACE"

kubectl rollout status deployment/api -n "$NAMESPACE" --timeout=120s

echo "[chaos] Injected. Alert sẽ fire trong ~2 phút."
echo "[chaos] Theo dõi:"
echo "  kubectl logs -f deployment/api -n $NAMESPACE"
echo "  curl http://localhost:9090/api/v1/alerts"
echo

# Tự động khôi phục sau DURATION giây
echo "[chaos] Tự động restore sau ${DURATION}s..."
sleep "$DURATION"
restore
