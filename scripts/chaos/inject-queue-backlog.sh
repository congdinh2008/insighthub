#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# shellcheck source=day4-common.sh
source "$SCRIPT_DIR/day4-common.sh"

STATE_DIR="$SCRIPT_DIR/../../tmp/day4"
STATE_FILE="$STATE_DIR/worker-replicas"
action=${1:-}
day4_require_lab

case "$action" in
  start)
    count=${DAY4_DOCUMENTS:-20}
    [[ "$count" =~ ^[0-9]+$ ]] && ((count >= 11 && count <= 50)) || {
      printf 'DAY4_DOCUMENTS must be 11..50\n' >&2
      exit 2
    }
    [[ ! -e "$STATE_FILE" ]] || {
      printf 'Backlog incident already has saved state\n' >&2
      exit 2
    }
    mkdir -p "$STATE_DIR"
    kubectl --context "$DAY4_KUBE_CONTEXT" -n "$DAY4_NAMESPACE" get deployment \
      insighthub-ingestion-worker -o jsonpath='{.spec.replicas}' >"$STATE_FILE"
    kubectl --context "$DAY4_KUBE_CONTEXT" -n "$DAY4_NAMESPACE" scale deployment \
      insighthub-ingestion-worker --replicas=0
    current_fixture=
    rollback_backlog() {
      [[ -z "$current_fixture" ]] || rm -f "$current_fixture"
      if [[ -f "$STATE_FILE" ]]; then
        saved_replicas=$(<"$STATE_FILE")
        kubectl --context "$DAY4_KUBE_CONTEXT" -n "$DAY4_NAMESPACE" scale deployment \
          insighthub-ingestion-worker --replicas="$saved_replicas" >/dev/null || true
        rm -f "$STATE_FILE"
      fi
    }
    trap rollback_backlog ERR
    trap 'rollback_backlog; exit 130' INT TERM
    for ((index = 1; index <= count; index++)); do
      current_fixture=$(mktemp /tmp/insighthub-day4-backlog.XXXXXX.txt)
      printf 'InsightHub Day 04 queue incident document %d at %s\n' \
        "$index" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$current_fixture"
      curl -fsS -F "file=@$current_fixture;filename=day4-backlog-$index.txt" \
        "$DAY4_API_URL/documents" >/dev/null
      rm -f "$current_fixture"
      current_fixture=
    done
    trap - ERR INT TERM
    printf 'Worker paused and %d unique documents enqueued\n' "$count"
    ;;
  stop)
    [[ -f "$STATE_FILE" ]] || {
      printf 'No saved worker replica state\n' >&2
      exit 2
    }
    replicas=$(<"$STATE_FILE")
    [[ "$replicas" =~ ^[0-9]+$ ]] || {
      printf 'Invalid saved replica count\n' >&2
      exit 2
    }
    kubectl --context "$DAY4_KUBE_CONTEXT" -n "$DAY4_NAMESPACE" scale deployment \
      insighthub-ingestion-worker --replicas="$replicas"
    rm -f "$STATE_FILE"
    printf 'Worker restored to %s replicas\n' "$replicas"
    ;;
  *)
    printf 'Usage: %s start|stop\n' "$0" >&2
    exit 2
    ;;
esac
