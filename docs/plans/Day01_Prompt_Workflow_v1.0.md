# Day 01 - Quy trình sử dụng prompt

Bộ [năm prompt Day 01](../../ai-prompts/day1.md) hướng dẫn học viên hoàn thiện solution theo thứ tự kiến trúc, planning, implementation, kiểm thử và nghiệm thu. Mỗi prompt có đầu vào, constraints và một đầu ra để review.

| Bước | Prompt | Việc học viên thực hiện | Điều kiện chuyển bước |
|---|---|---|---|
| 1 | D1-P01 - Architecture/context | Đọc source cùng agent, đối chiếu luồng xử lý và hoàn thiện AGENTS.md | Đúng kiến trúc starter, đủ constraints, context sáu section <=200 dòng |
| 2 | D1-P02 - Planning/review | Review plan, ghi quyết định và chỉnh phạm vi nếu cần | Plan map đủ yêu cầu, files, test cases và expected results |
| 3 | D1-P03 - Implementation | Cho agent thực hiện plan, đọc diff theo từng phần | Async upload/worker/retry có tests chức năng |
| 4 | D1-P04 - Code review/tests | Kiểm findings, yêu cầu sửa, chạy lại checks liên quan | Tests/quality/latency/lifecycle có kết quả đạt |
| 5 | D1-P05 - E2E/submission | Quan sát browser, kiểm evidence và hoàn thiện bài nộp | 11 E2E cases, prompt log, self-check, commits và PR |

## Phân chia công việc

- Architecture và planning có đầu ra riêng để học viên hiểu source trước khi chốt cách sửa.
- Review thiết kế nằm trong D1-P02, review code nằm trong D1-P04.
- Baseline, context và Git setup là bước trong quy trình, không cần prompt riêng.
- Worker quality và controlled retry cùng thuộc implementation Day 01.
- Browser E2E là lượt nghiệm thu riêng vì cần thao tác UI và screenshot evidence.

## Cách ghi prompt log

Ghi host/version/model/auth, thời gian, context và prompt đã sử dụng. Sau mỗi lượt, bổ sung kết quả, Why it worked, What I changed và links evidence. Specification yêu cầu tối thiểu ba prompt có giải thích; học viên chọn các lượt phản ánh được kiến trúc, triển khai và kiểm chứng.

Khi agent đề xuất thay đổi, học viên kiểm tra diff và kết quả trước khi chấp nhận. Lưu quyết định review có liên quan đến bài: invariant cần giữ, finding cần sửa, test chứng minh hoặc phần đề xuất vượt scope.

## Commit và PR

Commit theo thay đổi hoàn chỉnh, dùng Conventional Commits, kèm tests có liên quan. Với solution này, ba nhóm review chính là:

1. `fix(web): recover document status after request failures` - hai lỗi polling/failed metadata của starter, tách để cherry-pick riêng.
2. `feat(ingestion): add resilient async worker and controlled retries` - API, queue/worker, restart recovery, build/config, tests và CI.
3. `docs(day1): add student solution and verified acceptance evidence` - context, plan, prompt pack, runbook, self-check và evidence cuối.

Nếu triển khai theo các thay đổi độc lập nhỏ hơn, có thể tách `refactor`, `feat`, `test` tương ứng. Giữ một mục tiêu kỹ thuật trong mỗi commit, kèm tests có liên quan và kiểm tra thay đổi chạy được.

PR title: `[Day 1] Refactor ingestion async + Redis queue`. Nội dung mô tả thay đổi, cách kiểm thử, evidence và giới hạn kỹ thuật theo [PR description](../day1/PR_Description.md).
