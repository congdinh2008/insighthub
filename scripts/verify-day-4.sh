#!/usr/bin/env bash
# InsightHub — Verify Day 4 (AIOps + MLOps Overview)
set -u
PASS=0; FAIL=0
green(){ printf "\033[32m%s\033[0m\n" "$1"; }
red(){ printf "\033[31m%s\033[0m\n" "$1"; }
ok(){ green "  [PASS] $1"; PASS=$((PASS+1)); }
ng(){ red "  [FAIL] $1"; FAIL=$((FAIL+1)); }

echo "=== InsightHub — Verify Day 4 (AIOps) ==="

# ServiceMonitor
if [ -f observability/servicemonitor.yaml ] || [ -f observability/service-monitor.yaml ]; then
  ok "ServiceMonitor manifest tồn tại"
else
  ng "ServiceMonitor manifest không tồn tại"
fi

# Anomaly rules
if [ -f observability/anomaly-rules.yaml ] || [ -f observability/prometheus-rules.yaml ]; then
  RULES=$(cat observability/anomaly-rules.yaml observability/prometheus-rules.yaml 2>/dev/null)
  if echo "$RULES" | grep -qE "_anomaly|_upper_band|_baseline"; then
    ok "Anomaly band recording rules detected"
  else
    ng "Không thấy anomaly band recording rules"
  fi

  if command -v promtool >/dev/null; then
    # promtool không đọc K8s CRD format — dùng file plain rules (anomaly-rules.yaml)
    RULES_FILE=""
    [ -f observability/anomaly-rules.yaml ] && RULES_FILE="observability/anomaly-rules.yaml"
    [ -z "$RULES_FILE" ] && [ -f observability/prometheus-rules.yaml ] && \
      RULES_FILE="observability/prometheus-rules.yaml"
    if [ -n "$RULES_FILE" ]; then
      promtool check rules "$RULES_FILE" 2>&1 | grep -q "SUCCESS" \
        && ok "promtool check rules SUCCESS" || ng "promtool báo lỗi — kiểm tra PromQL syntax"
    else
      ng "Không tìm thấy rules file để validate"
    fi
  fi
else
  ng "Anomaly rules YAML không tồn tại"
fi

# Grafana dashboard JSON
if [ -d observability/grafana-dashboards ] && ls observability/grafana-dashboards/*.json >/dev/null 2>&1; then
  PANELS=$(jq -r '.panels | length' observability/grafana-dashboards/*.json 2>/dev/null | head -1)
  if [ -n "$PANELS" ] && [ "$PANELS" -ge 9 ]; then
    ok "Grafana dashboard có $PANELS panels (≥9)"
  else
    ng "Grafana dashboard chỉ có $PANELS panels (cần ≥9)"
  fi
else
  ng "Grafana dashboard JSON không tồn tại"
fi

# RCA reports
RCA_COUNT=$(ls rca-reports/incident-*.json 2>/dev/null | wc -l)
if [ "$RCA_COUNT" -ge 3 ]; then
  ok "RCA reports: $RCA_COUNT (≥3)"
  # Check each has evidence cited
  for f in rca-reports/incident-*.json; do
    if jq -e '.top_hypotheses[0].evidence' "$f" >/dev/null 2>&1; then
      ok "$(basename $f) có evidence cited"
    else
      ng "$(basename $f) thiếu evidence trong hypothesis"
    fi
  done
else
  ng "RCA reports: $RCA_COUNT (cần ≥3)"
fi

# MLOps overview notes
if [ -f mlops-overview-notes.md ] || [ -f docs/mlops-overview-notes.md ]; then
  NOTE=$(cat mlops-overview-notes.md docs/mlops-overview-notes.md 2>/dev/null)
  COUNT=$(echo "$NOTE" | grep -cE "Mindset|Lifecycle|Registry|Approval|Drift|Rollback|Ownership")
  if [ "$COUNT" -ge 4 ]; then
    ok "MLOps overview notes — đầy đủ 4 block concept"
  else
    ng "MLOps overview notes thiếu block concept"
  fi
else
  ng "mlops-overview-notes.md không tồn tại"
fi

echo
echo "=== Kết quả: $PASS PASS / $FAIL FAIL ==="
[ "$FAIL" -eq 0 ] && green "✅ Day 4 OK" || { red "❌ Xem Day4-Spec.md"; exit 1; }
