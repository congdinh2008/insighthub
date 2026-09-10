# Day 1 prompt log

## 2026-09-10 — Chặng 1: Redis local

Thực hiện final review Day 1 trước commit. Được sửa lỗi Day 1 phát hiện trong quá trình review và chạy test, nhưng không commit/push, không cài package hệ thống và không sửa nội dung Day 2–7.
1. Review toàn bộ diff Day 1 như reviewer độc lập:
   - kiểm tra correctness, race condition, payload lifecycle, retry semantics;
   - kiểm tra worker Dockerfile/entry point thực sự được Compose sử dụng;
   - kiểm tra không có hai implementation ingestion bị lệch;
   - kiểm tra log không lộ nội dung tài liệu hoặc lỗi nhạy cảm.
2. Review feature retry:
   - failed-only;
   - pending/ready bị từ chối;
   - nonexistent ID;
   - payload missing/hash mismatch/pipeline mismatch;
   - enqueue failure và timeout;
   - replay/idempotency;
   - thêm hoặc xác nhận test mô phỏng lỗi tạm thời lần đầu, sau đó retry cùng document ID thành công và document đạt ready, không tạo chunks trùng.
     Runtime whitespace vẫn failed là expected behavior của invalid input, không được trình bày như recovery thành công.
3. Kiểm tra prompt log:
   - ai-prompts/day1.md có ít nhất ba prompt thực tế;
   - mỗi prompt có mục tiêu, constraints, phản hồi AI, quyết định review, file thay đổi, test/bằng chứng và giới hạn;
   - không bịa prompt hoặc kết quả;
   - cho biết chính xác số prompt được ghi.
4. Chạy kiểm tra trong môi trường hiện có, ưu tiên container, không cài package hệ thống:
   - make test-backend;
   - verifier regression;
   - pytest Day 1/backend theo cách tương đương trong API container nếu host thiếu pytest;
   - ruff và mypy nếu dependency đã có;
   - runtime upload/chat/retry;
   - python3 scripts/verify.py day1 --evidence-dir evidence.
5. Với verifier Day 1:
   - đọc error thực tế;
   - tạo/cập nhật evidence đúng verification contract từ source và runtime hiện tại;
   - không sửa verifier, không giả hash hoặc PASS;
   - nếu vẫn INCOMPLETE, chỉ rõ artifact, dependency hoặc test scenario nào còn thiếu.
6. Kiểm tra phạm vi Git:
   - không sửa Day 2 chỉ để test_wrappers_portable_outside_repo pass;
   - phân biệt lỗi Day 2 có sẵn với lỗi Day 1;
   - backup docker-compose.yml.before-day1.bak không đưa vào commit;
   - evidence cần nộp nhưng đang bị ignore phải được liệt kê riêng, không tự force-add;
   - quét hardcoded secret mà không in giá trị.
7. Trả kết quả cuối bằng bảng từng Must-have Day 1: PASS/PARTIAL/INCOMPLETE, bằng chứng và file/test hỗ trợ. Liệt kê chính xác file nên commit và file không nên commit.
Không được chỉ dựa vào kết quả lần chạy trước; ghi thời điểm và kết quả của lần kiểm tra này.
Giải thích: 
các lỗi mà codex đã giải quyết trước đó chưa tối ưu, nên bắt no phải review lại và theo 1 số rule nhất định đã đề ra từ trước
## 2026-09-10 — Chặng 2: 
Tạm dừng mọi chỉnh sửa. Tôi muốn kiểm tra phạm vi thay đổi vì repo chứa nội dung cả 7 Day.
Chỉ đọc, không sửa, không revert, không commit/push.
1. Dùng git status, git diff và git diff --cached để kiểm tra cả file tracked và untracked. Không in secret.
2. Liệt kê từng file đã thay đổi, thay đổi chính, lý do cần cho Day 1 và bằng chứng từ diff. Không mặc định mọi thay đổi đều do bạn tạo.
3. Phân loại:
   - Cần cho async Day 1: API ingestion/queue/config/lifecycle, worker, Compose, dependency lock và test liên quan.
   - Hồ sơ Day 1: AGENTS.md, prompt log, tài liệu học và evidence.
   - Ngoài phạm vi hoặc chưa rõ lý do.
4. Đặc biệt kiểm tra có sửa web, chatops-bot, observability, security, tools/mcp, .github/workflows, tài liệu Day 2–7, Terraform/Helm hoặc infra/db/init.sql không. Nếu có, giải thích cụ thể; không tự khôi phục.
5. Phân biệt thay đổi logic với thay đổi xuống dòng CRLF/LF; phát hiện việc format hoặc normalize hàng loạt.
6. Đề xuất danh sách file được phép sửa cho chặng tiếp theo. Sau khi thống nhất, chỉ sửa danh sách đó; nếu cần mở rộng phải giải thích trước.
Báo cáo ngắn bằng bảng: file → thay đổi → liên quan Day 1 → cần review.
Giải thích:
sau khi làm 1 đoạn thì em sợ codex sẽ xâm thực toàn bộ tài nguyên của folder nên em đã kêu nó quét lại toàn bộ xem nó có thay đổi gì khác ngoài cái mục em đã giao ngay từ đầu hay không

## 2026-09-10 — Chặng 3: 
oàn tất nộp bài Day 1: final audit, commit, push và tạo Pull Request. Tôi đồng ý bỏ qua Ruff và Mypy; ghi rõ hai kiểm tra này chưa chạy, không tuyên bố PASS.
Được phép thực hiện Git commit, push branch day1-refactor lên origin và tạo PR vào main của repo Crozn1812/insighthub_devops. Không merge PR.
Trước khi commit:
1. Xác nhận đang ở branch day1-refactor và origin là:
   https://github.com/Crozn1812/insighthub_devops.git
2. Chạy lại:
   - docker compose config --quiet
   - docker compose config --services
   - docker compose ps
   - make test-backend
   - milestone pytest với đúng biến môi trường
   - python scripts/verify.py day1 --evidence-dir evidence
   - git diff --check
3. Xác nhận AGENTS.md có đúng 6 section và không quá 200 dòng.
4. Xác nhận ai-prompts/day1.md có ít nhất 3 prompt thực tế và phần giải thích.
5. Quét diff tìm hardcoded secret mà không in giá trị.
6. Xác nhận không có thay đổi Day 2–7 hoặc schema DB.
7. Không stage hoặc commit:
   - docker-compose.yml.before-day1.bak
   - .env
   - .venv/
   - evidence/
   - reports/
   - cache hoặc dữ liệu runtime.
8. Nếu một kiểm tra bắt buộc Day 1 vừa fail, dừng trước commit, sửa lỗi Day 1 trong phạm vi và chạy lại. Không sửa verifier hoặc Day 2 để lấy PASS.
Chia commit rõ ràng, chỉ thuộc Day 1:
Commit 1 — context:
- AGENTS.md
Commit 2 — async implementation:
- .gitattributes
- api/Dockerfile
- api/app/core/config.py
- api/app/core/db.py
- api/app/core/errors.py
- api/app/main.py
- api/app/routers/documents.py
- api/app/services/payloads.py
- api/app/services/queue.py
- api/app/worker.py
- api/requirements.in
- api/requirements.txt
- docker-compose.yml
- ingestion-worker/Dockerfile
- ingestion-worker/requirements.txt
- ingestion-worker/worker.py
- ingestion-worker/README.md
- scripts/smoke-test.sh
- scripts/verify-day-1.sh
- scripts/verify-starter.sh
Commit 3 — tests and documentation:
- api/tests/test_integration.py
- api/tests/test_unit_queue.py
- tests/milestones/day1/test_async_contract.py
- scripts/check_async_ingestion.py
- scripts/check_async_replay.py
- docs/day1-async-ingestion.md
- ai-prompts/day1.md
Trước mỗi commit, kiểm tra danh sách staged bằng git diff --cached --name-only. Nếu một file trong danh sách không tồn tại hoặc không còn thay đổi, không tạo thay đổi giả chỉ để stage.
Dùng commit messages:
1. docs(day1): complete project agent context
2. feat(day1): move ingestion to Redis worker
3. test(day1): verify async ingestion and retry
Sau commit:
1. Kiểm tra git status --short; chỉ backup local được phép còn untracked.
2. Push:
   git push -u origin day1-refactor
3. Kiểm tra GitHub CLI authentication mà không in token.
4. Tạo PR vào branch main, không merge, với title chính xác:
   [Day 1] Refactor ingestion async + Redis queue
PR body cần ghi:
- API upload trả 202 và worker xử lý qua Redis/ARQ.
- Shared payload volume và trạng thái pending/ready/failed.
- Feature retry failed-only và idempotency.
- 5 service healthy.
- Upload fixture dưới 1 giây, ready dưới 30 giây.
- Chat API PASS.
- Backend tests, milestone 6/6 và verifier Day 1 PASS.
- Fixture không đánh giá semantic retrieval.
- Ruff và Mypy chưa chạy.
- Prompt log ở ai-prompts/day1.md.
- Không có secret hoặc schema migration.
Nếu gh chưa cài hoặc chưa đăng nhập:
- vẫn push branch nếu push hoạt động;
- không yêu cầu hoặc in token;
- trả cho tôi URL GitHub Compare để tôi tạo PR trên trình duyệt.
Cuối cùng báo:
- ba commit hash và message;
- kết quả test cuối;
- URL PR;
- xác nhận PR chưa merge;
- file local còn ngoài commit.
Trước khi commit, điều chỉnh ai-prompts/day1.md để giữ ba prompt thực tế dài và bao phủ nhiều vấn đề nhất:
1. Prompt “Hoàn thiện toàn bộ 7/7 yêu cầu Day 1 trên branch day1-refactor...”
2. Prompt “Thực hiện final review Day 1 trước commit...”
3. Prompt “Verifier Day 1 hiện chạy được nhưng báo INCOMPLETE vì thiếu đúng bốn milestone scenarios...”
Giữ nội dung prompt đủ chi tiết để thể hiện mục tiêu, phạm vi, constraints và tiêu chí kiểm tra; không rút thành một câu ngắn và không thêm nội dung chưa từng được yêu cầu.
Sau mỗi prompt phải có:
- Vì sao sử dụng prompt.
- Phản hồi hoặc thay đổi chính do AI thực hiện.
- Điều tôi đã review, chấp nhận hoặc yêu cầu sửa.
- File bị ảnh hưởng.
- Test và bằng chứng thực tế.
- Giới hạn còn lại.
Cập nhật kết quả cuối:
- Backend tests 67/67 PASS.
- Milestone Day 1: 6/6 PASS.
- Verifier Day 1: PASS, runtime_verified=true.
- Fixture không đánh giá chất lượng semantic retrieval.
- Ruff và Mypy chưa chạy theo quyết định của tôi.
Sau khi chỉnh prompt log, tiếp tục final audit, ba commit, push và tạo PR theo yêu cầu trước đó.

Giải thích:
sau đã làm hoàn thành rồi thì em kêu AI kiểm tra lại bài 1 lần nữa trước khi đẩy code lên github