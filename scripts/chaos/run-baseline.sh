#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# shellcheck source=day4-common.sh
source "$SCRIPT_DIR/day4-common.sh"

duration=${DAY4_BASELINE_SECONDS:-4500}
interval=${DAY4_BASELINE_INTERVAL_SECONDS:-10}
[[ "$duration" =~ ^[0-9]+$ ]] && ((duration >= 4200 && duration <= 7200)) || {
  printf 'DAY4_BASELINE_SECONDS must be 4200..7200\n' >&2
  exit 2
}
[[ "$interval" =~ ^[0-9]+$ ]] && ((interval >= 5 && interval <= 60)) || {
  printf 'DAY4_BASELINE_INTERVAL_SECONDS must be 5..60\n' >&2
  exit 2
}
day4_require_lab

started=$(date +%s)
deadline=$((started + duration))
index=0
while (( $(date +%s) < deadline )); do
  index=$((index + 1))
  day4_chat_load 1 0
  curl -fsS "$DAY4_API_URL/healthz" >/dev/null
  sleep "$interval"
done
printf 'Baseline workload complete: requests=%d duration_seconds=%d\n' "$index" "$duration"
