#!/usr/bin/env bash
# InsightHub — Smoke test cho v1 (Day 1 async refactor)
# Chạy SAU khi `docker compose up` đã chạy xong.
# Kiểm tra pipeline RAG end-to-end: health → upload (202) → poll ready → chat.

set -u

API="http://localhost:8000"
WEB="http://localhost:3000"
PASS=0
FAIL=0

green(){ printf "\033[32m%s\033[0m\n" "$1"; }
red(){ printf "\033[31m%s\033[0m\n" "$1"; }

echo "=== InsightHub v1 Smoke Test ==="
echo

# 1. API health
echo "[1] API liveness..."
if curl -sf "$API/healthz" >/dev/null; then
  green "    PASS — API sống"
  PASS=$((PASS+1))
else
  red "    FAIL — API không phản hồi $API/healthz"
  FAIL=$((FAIL+1))
fi

# 2. API readiness (DB)
echo "[2] API readiness (DB)..."
if curl -sf "$API/readyz" >/dev/null; then
  green "    PASS — DB sẵn sàng"
  PASS=$((PASS+1))
else
  red "    FAIL — DB chưa sẵn sàng"
  FAIL=$((FAIL+1))
fi

# 3. Web health
echo "[3] Web health..."
if curl -sf "$WEB/api/health" >/dev/null; then
  green "    PASS — Web sống"
  PASS=$((PASS+1))
else
  red "    FAIL — Web không phản hồi"
  FAIL=$((FAIL+1))
fi

# 4. Upload + async ingest (v1: 202 → poll until ready)
echo "[4] Upload tài liệu mẫu (async v1)..."
UPLOAD=$(curl -sf -X POST "$API/documents" \
  -F "file=@sample-docs/so-tay-van-hanh.md" 2>/dev/null)
DOC_ID=$(echo "$UPLOAD" | grep -o '"id":[0-9]*' | grep -o '[0-9]*' | head -1)
if echo "$UPLOAD" | grep -qE '"status":"(pending|ready)"' && [ -n "$DOC_ID" ]; then
  green "    PASS — Upload → 202 (async), document id=$DOC_ID"
  PASS=$((PASS+1))
  # Poll status until ready (max 30s)
  echo "[4b] Polling worker status (max 30s)..."
  STATUS="pending"
  for i in $(seq 1 15); do
    sleep 2
    STATUS=$(curl -sf "$API/documents" 2>/dev/null | \
      python3 -c "import sys,json; docs=json.load(sys.stdin); \
        d=[x for x in docs if str(x.get('id',''))==\"$DOC_ID\"]; \
        print(d[0].get('status','') if d else '')" 2>/dev/null)
    [ "$STATUS" = "ready" ] && break
  done
  if [ "$STATUS" = "ready" ]; then
    green "    PASS — Worker processed → status=ready"
    PASS=$((PASS+1))
  else
    red "    FAIL — Worker timeout, status=$STATUS"
    FAIL=$((FAIL+1))
  fi
else
  red "    FAIL — Upload lỗi. Response: $UPLOAD"
  FAIL=$((FAIL+1))
fi

# 5. Chat query
echo "[5] Truy vấn RAG..."
CHAT=$(curl -sf -X POST "$API/chat" \
  -H "Content-Type: application/json" \
  -d '{"question":"InsightHub có mấy thành phần chính?"}' 2>/dev/null)
if echo "$CHAT" | grep -q '"answer"'; then
  green "    PASS — Chat trả về câu trả lời"
  PASS=$((PASS+1))
else
  red "    FAIL — Chat lỗi. Response: $CHAT"
  FAIL=$((FAIL+1))
fi

# 6. Metrics endpoint
echo "[6] Prometheus metrics..."
if curl -sf "$API/metrics" | grep -q "insighthub_"; then
  green "    PASS — /metrics expose số liệu"
  PASS=$((PASS+1))
else
  red "    FAIL — /metrics không có dữ liệu"
  FAIL=$((FAIL+1))
fi

echo
echo "=== Kết quả: $PASS PASS / $FAIL FAIL ==="
[ "$FAIL" -eq 0 ] && green "InsightHub v1 hoạt động đầy đủ." || red "Có lỗi — xem log: docker compose logs"
exit "$FAIL"
