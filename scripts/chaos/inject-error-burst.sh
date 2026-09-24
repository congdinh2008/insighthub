#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# shellcheck source=day4-common.sh
source "$SCRIPT_DIR/day4-common.sh"

action=${1:-}
day4_require_lab
case "$action" in
  start)
    requests=${DAY4_REQUESTS:-150}
    [[ "$requests" =~ ^[0-9]+$ ]] && ((requests >= 20 && requests <= 300)) || {
      printf 'DAY4_REQUESTS must be 20..300\n' >&2
      exit 2
    }
    day4_set_fault_mode error
    cleanup_fault() {
      day4_set_fault_mode normal || true
    }
    trap cleanup_fault ERR
    trap 'cleanup_fault; exit 130' INT TERM
    day4_chat_load "$requests" 1
    trap - ERR INT TERM
    ;;
  stop)
    day4_set_fault_mode normal
    ;;
  *)
    printf 'Usage: %s start|stop\n' "$0" >&2
    exit 2
    ;;
esac
