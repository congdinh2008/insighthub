#!/usr/bin/env bash
set -euo pipefail

alertmanager_url=${DAY4_ALERTMANAGER_URL:-http://127.0.0.1:19093}
starts_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ends_at=$(date -u -v+5M +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '+5 minutes' +%Y-%m-%dT%H:%M:%SZ)

curl -fsS -H 'Content-Type: application/json' -X POST \
  -d "[{\"labels\":{\"alertname\":\"InsightHubNotificationTest\",\"project\":\"insighthub\",\"severity\":\"info\"},\"annotations\":{\"summary\":\"InsightHub Day 04 Alertmanager to Slack test\"},\"startsAt\":\"$starts_at\",\"endsAt\":\"$ends_at\"}]" \
  "$alertmanager_url/api/v2/alerts"
printf 'Test alert submitted at %s; verify delivery in #alerts\n' "$starts_at"
