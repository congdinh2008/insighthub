# Day 01 - Reproduce and operate

## Khởi động và kiểm tra

Dùng checkout `day1-refactor`, Docker Compose và Python 3.12 cho tooling. Không dùng volume của lớp/lab khác. Lệnh dưới chạy từ root repo; dùng project riêng và đổi ports nếu đã có ứng dụng khác sử dụng.

```bash
export COMPOSE_PROJECT_NAME=insighthub-day1
export API_PORT=18001 WEB_PORT=13001
export API_URL=http://localhost:18001 WEB_URL=http://localhost:13001
python3.12 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements-dev.txt
. .venv/bin/activate
pre-commit install
docker compose config --quiet
docker compose config --services
docker compose up --build -d --wait
make test-image
make test-backend test-worker
make test-day1 lint typecheck test-verifiers
make tools test-mcp
INSIGHTHUB_API_URL="$API_URL" node tools/mcp/smoke.mjs --live
make smoke
pre-commit run --all-files
```

Backend runner mount source read-only, RUN_DB_TESTS=1, tạo và xóa schema test ngẫu nhiên trong database lab. Nó không thêm service mặc định thứ sáu. Runtime worker/image và quality tools dùng hash locks. Nếu đổi project, truyền cùng biến cho tất cả lệnh. `make test-image` cần chạy trước tests lần đầu hoặc khi lockfile đổi.

Web: http://localhost:13001. Swagger: http://localhost:18001/docs. Worker readiness/metrics không publish ra host:

```bash
docker compose exec -T ingestion-worker python -c 'import urllib.request; print(urllib.request.urlopen("http://localhost:8081/readyz").read().decode())'
docker compose exec -T ingestion-worker python -c 'import urllib.request; print(urllib.request.urlopen("http://localhost:8081/metrics").read().decode())'
```

## Phục hồi kết nối và trạng thái

Worker dùng `restart: unless-stopped`. Khi Redis mất kết nối, process thoát với safe JSON event và Docker tự restart; sau khi Redis hoạt động, kiểm worker healthy và document cùng ID ready. Không chạy `start ingestion-worker` trong test automatic recovery. Manual `docker compose stop ingestion-worker` giữ worker dừng cho đến khi operator start lại.

Web thử lại polling sau lỗi API, tối đa 60 lần mỗi chu kỳ. Hết lượt, UI hướng dẫn làm mới trạng thái; nút refresh bắt đầu chu kỳ mới nếu còn pending. Upload lỗi cập nhật failed metadata và giữ thông báo lỗi gốc.

## Upload và retry

```bash
curl -sS -w '\nHTTP=%{http_code} seconds=%{time_total}\n' -F 'file=@sample-docs/so-tay-van-hanh.md' "$API_URL/documents"
curl -sS "$API_URL/documents"
# Chỉ dùng ID failed đã xác minh, đúng file/filename gốc:
curl -sS -F 'file=@sample-docs/so-tay-van-hanh.md' "$API_URL/documents/ID_DA_XAC_MINH/retry"
```

202 nghĩa là queue nhận request, chưa phải ready. Poll GET `/documents`, lấy chính ID nhận về. 409 ở retry có thể do job cũ đang kết thúc: đợi, đọc lại trạng thái và kiểm tra worker; không tạo document mới để giấu lỗi. Nếu mất phản hồi retry/503, đọc trạng thái trước khi gửi lại vì job vẫn có thể đã tới Redis.

## Recovery pending bị mất job

Chỉ áp dụng cho lab sau khi xác minh API chết giữa DB commit và enqueue hoặc payload đã expire. Không chạy mass update pending.

1. Xác định ID và file gốc, kiểm tra JSON worker logs và trạng thái DB. Nếu worker còn chạy job, chờ hoàn tất, không can thiệp.
2. Với một pending bất thường: kiểm tra Redis `arq:job:ingestion:ID`, `arq:in-progress:ingestion:ID` và queue sorted set bằng read-only commands. Kiểm tra process worker và queue name thực tế.
3. Dừng API và worker riêng project để loại race; kiểm tra lại DB/Redis. Nếu job còn tồn tại, khôi phục worker để xử lý, không sửa metadata.
4. Chỉ khi xác nhận không có queued/in-progress job và không có chunks, operator được phép chuyển đúng ID từ pending sang failed, safe code `queue_unavailable`, trong transaction với `WHERE id = ... AND status = 'pending' AND chunk_count = 0`. Kiểm tra affected rows = 1. Không đổi hash/pipeline/embedding identity.
5. Khởi động API/worker, retry qua endpoint với file gốc; xác nhận cùng ID ready và chunk indices không trùng. Lưu lệnh/ID/outcome vào evidence của lượt recovery.

Runbook này ghi giới hạn non-atomic, chưa được coi là automatic recovery feature. Không cần thực hiện SQL recovery cho bài lab đã có evidence.

## Runtime probes và milestone verifier

Browser fixtures nhỏ nằm trong `tests/milestones/day1/fixtures/`. Tạo file vượt giới hạn ngoài source, rồi dùng file picker trên web và Swagger theo 11 cases trong plan:

```bash
mkdir -p evidence/browser-fixtures
python - <<'PYTHON'
from pathlib import Path
Path("evidence/browser-fixtures/e2e-oversize.txt").write_bytes(b"x" * (10 * 1024 * 1024 + 1))
PYTHON
```

Với E2E-09, giữ nguyên trang pending, dừng API cho tới khi hiện lỗi rồi start lại API/worker. Không refresh trang để chứng minh polling tự phục hồi. Với E2E-11, giữ worker dừng tới khi UI báo hết 60 lần kiểm tra, bấm làm mới rồi start worker; UI phải tự chuyển ready.

Probe dưới kiểm Redis outage khi worker đang chạy và chỉ start lại Redis để xác minh automatic recovery. Nó cũng kiểm SIGTERM, redelivery và AOF persistence với thao tác stop/start riêng; tạo/xóa tài liệu synthetic của nó, cuối cùng khôi phục stack. Chạy trên lab biệt lập khi không có người khác dùng:

```bash
INSIGHTHUB_API_URL="$API_URL" INSIGHTHUB_WEB_URL="$WEB_URL" \
  python tests/milestones/day1/runtime_probe.py --project "$COMPOSE_PROJECT_NAME" \
  --output docs/evidence/day1/runtime-probe.json
```

Envelope `evidence/day1.json` có freshness 24 giờ và phải khớp source/artifacts. Sau khi chạy tests và runtime probe, tạo envelope cho lượt thực hành bằng lệnh sau rồi chạy verifier:

```bash
python - <<'PYTHON'
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, "scripts")
from verify import fingerprint
roles = {
    "refactor": "api/app/routers/documents.py",
    "review": "docs/day1/Review_and_Self_Check.md",
    "worker": "ingestion-worker/worker.py",
    "worker_dockerfile": "ingestion-worker/Dockerfile",
}
data = {
    "schema_version": 1, "day": 1, "mode": "real",
    "application_mode": "fixture",
    "observed_at": datetime.now(timezone.utc).isoformat(),
    "source_sha256": fingerprint(Path.cwd()),
    "artifacts": {role: {"path": name, "sha256": hashlib.sha256(
        Path(name).read_bytes()).hexdigest()} for role, name in roles.items()},
}
Path("evidence").mkdir(exist_ok=True)
Path("evidence/day1.json").write_text(json.dumps(data, indent=2) + "\n")
PYTHON
```

`mode=real` trong envelope chỉ software/runtime thật; application vẫn `RAG_MODE=fixture`. Khi source hoặc artifacts thay đổi, chạy lại các kiểm tra liên quan và tạo envelope mới.

```bash
bash scripts/verify-day-1.sh --compose-project "$COMPOSE_PROJECT_NAME" \
  --api-url "$API_URL" --web-url "$WEB_URL" --evidence-dir evidence \
  --max-upload-seconds 1 --poll-timeout 30 --json
```

Verifier PASS chỉ bounded runtime contract, vẫn trả `milestone_complete=false`. Đọc review matrix, browser evidence, CI/PR và prompt logs để đánh giá toàn bộ bài.

## Dừng lab

```bash
docker compose --profile ollama down
```

Giữ volumes để review/reproduce. Không dùng `--volumes` ở lab này, không prune toàn máy. Không có tài nguyên AWS cần teardown.
