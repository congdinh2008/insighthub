#!/usr/bin/env bash
set -euo pipefail

DAY4_KUBE_CONTEXT=${DAY4_KUBE_CONTEXT:-kind-insighthub-local}
DAY4_NAMESPACE=${DAY4_NAMESPACE:-insighthub-dev}
DAY4_API_URL=${DAY4_API_URL:-http://127.0.0.1:18000}

day4_require_lab() {
  local actual
  actual=$(kubectl config current-context)
  if [[ "$actual" != "$DAY4_KUBE_CONTEXT" ]]; then
    printf 'Refusing context %s; expected %s\n' "$actual" "$DAY4_KUBE_CONTEXT" >&2
    exit 2
  fi
  kubectl --context "$DAY4_KUBE_CONTEXT" get namespace "$DAY4_NAMESPACE" >/dev/null
  kubectl --context "$DAY4_KUBE_CONTEXT" -n "$DAY4_NAMESPACE" \
    get deployment insighthub-api >/dev/null
}

day4_set_fault_mode() {
  local mode=$1
  kubectl --context "$DAY4_KUBE_CONTEXT" -n "$DAY4_NAMESPACE" patch configmap \
    insighthub-provider-fault --type merge \
    -p "{\"data\":{\"mode\":\"$mode\"}}" >/dev/null

  local attempt observed
  for attempt in {1..45}; do
    observed=$(kubectl --context "$DAY4_KUBE_CONTEXT" -n "$DAY4_NAMESPACE" exec \
      deployment/insighthub-provider-fault-proxy -- cat /fault-config/mode 2>/dev/null || true)
    if [[ "$observed" == "$mode" ]]; then
      printf 'Fault mode is now %s\n' "$mode"
      return
    fi
    sleep 2
  done
  printf 'Timed out waiting for projected fault configuration\n' >&2
  exit 1
}

day4_chat_load() {
  local requests=$1
  local pause_seconds=$2
  local index code
  for ((index = 1; index <= requests; index++)); do
    code=$(curl -sS -o /tmp/insighthub-day4-chat-response.json -w '%{http_code}' \
      -H 'Content-Type: application/json' \
      -d "{\"question\":\"Day 04 telemetry request $index\"}" \
      "$DAY4_API_URL/chat")
    printf 'request=%d status=%s\n' "$index" "$code"
    sleep "$pause_seconds"
  done
}
