# Day 06 - Local security và FinOps

Phạm vi: kind `kind-insighthub-local`, namespace `insighthub-dev`, provider ZenLayer. Không cần AWS cho nghiệm thu này. Đọc [Self_Check](Self_Check.md) để phân biệt kết quả đã chạy và tính năng optional chưa bật. Không xóa volume hoặc dữ liệu Day 01-05.

## Khởi tạo

Yêu cầu Python 3.12, Docker, kind, kubectl, Helm, Node 22.22+ và cluster Day 03/04 đang chạy. Docker VM 4 GiB đã gây áp lực RAM/IO khi build đồng thời với scan. Build và load images tuần tự; dừng baseline khi không sử dụng. Không coi timeout do thiếu tài nguyên là security PASS.

```sh
python3.12 -m venv tmp/day6/venv
tmp/day6/venv/bin/pip install --require-hashes -r requirements-dev.txt
tmp/day6/venv/bin/pip install --require-hashes -r gateway/requirements.txt
tmp/day6/venv/bin/pip install --require-hashes -r security/guardrails/requirements.txt
npm ci --prefix security --ignore-scripts
docker build -t insighthub-api:day6 api
docker build --target runtime -f ingestion-worker/Dockerfile -t insighthub-worker:day6 .
docker build -t insighthub-gateway:day6 gateway
docker build -t insighthub-guardrails:day6 security/guardrails
tmp/day2/bin/kind load docker-image --name insighthub-local insighthub-api:day6 insighthub-worker:day6 insighthub-gateway:day6 insighthub-guardrails:day6
```

Đặt `ZENLAYER_API_KEY`, `ZENLAYER_BASE_URL` trong shell từ secret store/private env, không truyền key bằng argv hoặc commit. `local_lab.py` lưu credentials bootstrap vào `tmp/day6/infrastructure.json` mode 0600, reuse khi chạy lại. Đọc pricing catalog trước khi đổi model.

```sh
tmp/day6/venv/bin/python tools/security/day6/local_lab.py up
python3 tools/security/day6/forward.py
```

Giữ terminal forward chạy. Tại terminal khác:

```sh
tmp/day6/venv/bin/python tools/security/day6/bootstrap.py
tmp/day6/venv/bin/python tools/security/day6/switch_app.py
tmp/day6/venv/bin/python tools/security/day6/observability.py
```

`switch_app.py` backup original runtime Secret/Helm values, kiểm pending documents và queue cũ, đổi API/worker cùng nhau. Endpoint/embedding revision mới sử dụng DB và queue Day06 riêng. Không thay identity trên index cũ. Baseline có `security_enabled=false`, restricted evaluator key và không có Service public; chỉ chạy với dữ liệu synthetic.

Endpoints: web `http://127.0.0.1:13000`, API `:18010`, baseline `:18011`, gateway `:14010`, guard `:18083`, exporter `:19091`, Grafana `:13001/d/insighthub-day6-finops`. Sau rollout, port-forward cũ có thể đứt ở request đầu; supervisor nối lại. Prewarm `/readyz` và yêu cầu HTTP200 liên tiếp trước khi chạy đo. Endpoint `/health` không tồn tại. Bước preflight phải trả nonzero để chặn toàn bộ chain khi readiness không đạt; không đặt scan sau một lệnh preflight có thể fail mà shell vẫn tiếp tục.

## Chạy kiểm thử

```sh
make test-day6
tmp/day6/venv/bin/python tools/security/day6/gateway_tests.py auth
tmp/day6/venv/bin/python tools/security/day6/gateway_tests.py budget
tmp/day6/venv/bin/python tools/security/day6/lifecycle.py
tmp/day6/venv/bin/python tools/security/day6/guard_cases.py
tmp/day6/venv/bin/python tools/security/day6/direct_access.py
tmp/day6/venv/bin/python tools/security/day6/judge_validation.py
```

Budget probes chờ native spend ổn định 12 giây trước mỗi cap nhỏ, rồi kiểm đủ chi phí của tất cả completion thành công đã persist trước khi thử automatic denial. Không chạy model traffic khác trong cửa sổ đo; không refresh key cache để ép kết quả.

Đọc `--help` của coding/fault scripts trước khi chạy. Fault harness chỉ scale target đã hard-code thuộc lab và restore trong `finally`. Không chạy fault cùng lúc với full scan. `ui_budget.py insighthub|bot` hạ cap riêng key trong 45 giây rồi khôi phục, dành cho thao tác Edge/Slack.

Dataset `security/datasets/day6.json` có 164 cases: 120 generated native, 24 RAG local reviewed, 20 benign. `generated.yaml` giữ nguyên cấu hình lịch sử của lượt generate, kể cả port bootstrap cũ. Config chạy frozen nằm trong `frozen-eval.yaml`. Không regenerate dataset giữa initial/final. Xem [coverage](../../security/coverage.md) và [findings](../../security/findings.md) về oracle v1/v2.

Để nghiệm thu: hoàn tất code/format/test trước; giữ source nguyên trạng suốt baseline replay, final và verifier. `scan.py` từ chối overwrite và từ chối source/dataset thay đổi giữa lượt. Chạy baseline trước final:

```sh
DAY6_REPLAY_LABEL="replay-$(date -u +%Y%m%dT%H%M%SZ)"
kubectl --context kind-insighthub-local -n insighthub-dev scale deployment/day6-baseline-api --replicas=1
kubectl --context kind-insighthub-local -n insighthub-dev rollout status deployment/day6-baseline-api
tmp/day6/venv/bin/python tools/security/day6/scan.py initial --label "$DAY6_REPLAY_LABEL-baseline"
kubectl --context kind-insighthub-local -n insighthub-dev scale deployment/day6-baseline-api --replicas=0
tmp/day6/venv/bin/python tools/security/day6/scan.py final --label "$DAY6_REPLAY_LABEL-final"
```

Các target Makefile dùng tên folder cố định và sẽ từ chối khi evidence đã có; không xóa hoặc ghi đè reports để chạy lại. Khi baseline lỗi, vẫn scale baseline về0 trước khi điều tra. Preflight chỉ chấp nhận corpus có một guide synthetic ready và yêu cầu chat model thật trả đúng fact PostgreSQL kèm sources trên từng endpoint trước khi tạo run. Key hết hạn, budget deny hoặc model path lỗi sẽ dừng scan trước bulk evaluation. Nếu có orphan, đối chiếu exact document ID, filename, content SHA và thời điểm trong manifest của lượt trước; cleanup qua API đúng IDs đó. Không xóa documents chỉ dựa vào prefix filename. Harness lưu ID ngay sau202 và retry cleanup có giới hạn; `orphaned-documents.jsonl` ghi các ID cần xử lý khi cleanup không thành công.

Reports trong `docs/evidence/day6/<label>/`. Baseline replay cùng final source không thay thế initial trước fixes. Dataset không đổi; policy profile khác nhau được ghi rõ. LLM judge chỉ nhận synthetic question/answer/public contexts, không nhận application internal prompt. Cùng họ model nên đây là đánh giá có giới hạn, không phải chứng nhận bảo mật độc lập.

Verifier cần `day6.json` với `mode=real`, source/dataset fingerprints và artifacts `dataset`, `eval_initial`, `eval_final`, `cost`; đường dẫn artifacts là repository-relative. Sau khi tạo envelope theo verification contract:

```sh
tmp/day6/venv/bin/python scripts/verify.py day6 --api-url http://127.0.0.1:18010 --evidence-dir docs/evidence/day6/verifier --test-timeout 2400 --json
```

Verifier chạy mới toàn bộ 164 cases cùng budget probes, không copy observations cũ. PASS chỉ bao phủ contract tự động; vẫn cần MH review, UI và FinOps evidence.

## Computer Use

Trên Edge bật quyền extension `Allow access to file URLs`, upload file synthetic qua file chooser thật. Chạy upload/ready/chat/citation, poisoned document, policy block/recovery, budget deny/recovery và guard fault/recovery. Dùng API chỉ để đối chiếu exact document/chunk hashes và cleanup own test IDs.

Slack dùng bot Day05 với `CHATOPS_MODEL_URL`/`CHATOPS_MODEL_NAME`/`CHATOPS_MODEL_KEY` tương ứng cấu hình trong `chatops-bot/app/config.py`, model alias `bot-chat`. Bot vẫn dùng scope MCP/scale identity cũ. Thực hiện ba reads, scale/confirm/replay/restore; không để model quyết định quyền. Worker reconnect Redis, phục hồi leased jobs; TTL heartbeat hết khi dependency không sẵn sàng. Không commit tunnel URL/Slack credentials hoặc approval token còn hiệu lực.

## Cost, audit và an toàn

```sh
make day6-evidence
python3 tools/security/day6/secret_scan.py docs/evidence/day6
```

Budget keys: app 1.50 USD, bot 0.50, coding 1.00, guard 1.00, evaluator 0.50; TTL 7 ngày. Lab tự ngừng admission ở tổng native spend 4 USD để giữ reserve trong envelope 5 USD. Trong lượt acceptance hiện tại, 0.25 USD reserve được chuyển từ app sang evaluator: app 1.25/evaluator 0.75, tổng caps vẫn 4.50 USD; xem `budget-reallocation.json`. Caps là soft do accounting asynchronous/in-flight; đọc measured overshoot, không tuyên bố hard limit tuyệt đối.

Ledger fsync vào PVC, chỉ metadata allowlist; exporter đối soát native PostgreSQL spend. Catalog estimate phân biệt invoice. Chi phí toàn lab gồm generation, embeddings, guard, generator/judge, retries và paid output bị chặn. Cost/success của report semantic khác cost/completed-call trên dashboard. Không dùng latency để suy cache hit; chỉ dùng usage cache tokens thật.

Guard unavailable hoặc NeMo internal error trả 503; input/output policy violation trả 422; app budget trả 429. Không tắt guards để khắc phục lỗi. `DAY6_ACCOUNTING_URL` phải là raw PostgreSQL DSN riêng vì LiteLLM có thể thêm Prisma parameters vào `DATABASE_URL`.

## Rollback và dừng

Ngừng uploads/scans rồi drain. API/worker rollback cùng nhau:

```sh
tmp/day6/venv/bin/python tools/security/day6/rollback.py
```

Script dùng saved values, giữ cả PVC cũ và Day06. Để bật lại, chạy `switch_app.py`, xác nhận cùng queue/index/endpoint, prewarm forwards. Không dùng `helm rollback` một thành phần riêng hoặc reset DB.

Dừng lab mà giữ dữ liệu: dừng bot worker/HTTP và cloudflared đúng process của lab; Ctrl-C forwards; scale baseline/gateway/guardrails về 0 khi không demo. Không dừng workload chia sẻ khi task khác đang dùng. Không xóa PVC/secrets/keys cho đến khi export evidence và xác nhận không còn consumer. Key hết hạn sau 7 ngày; reprovision cần cập nhật cả app/bot/classifier/coding consumers. Không xóa volumes hoặc `docker prune`.

CI boundary tests chạy trên PR/push. Live CI Compose chỉ bật khi protected environment `day6-model-evaluation` có reviewer, secret `DAY6_ZENLAYER_API_KEY`, variable `DAY6_ZENLAYER_BASE_URL` và `DAY6_LIVE_ENABLED=true`. Fork không nhận secrets. Chưa provision credentials thì live job skipped, không được báo nightly/live CI PASS.

Evaluator transport chỉ retry tối đa một lần cho timeout/network/HTTP5xx, giữ nguyên payload và ghi `judge-transport.jsonl` metadata. Không retry HTTP4xx/budget, response200 malformed hoặc verdict hợp lệ dù FAIL. Rubric, dataset và verifier assertions không thay đổi. Lỗi app/guard vẫn là lỗi thực thi, không được tính policy PASS.
