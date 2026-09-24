# Day 04 - Nhật ký prompt đã lưu

## Nguồn và giới hạn

Ba mục dưới đây được dịch từ `ai-prompts/day4.md` tại commit `6c9a4c8`, giữ
nội dung và trạng thái ngày 23/09/2026. Đây là bản tóm tắt lịch sử trong
repository, chưa phải transcript nguyên văn đã đối chiếu với phiên host.
[Bộ prompt chuẩn hóa ngày 24/09](day4-templates.md) là mẫu để sử dụng tiếp, không
được ghi nhận là đã chạy.

Metadata chung cho ba mục:

- **Host:** ChatGPT-Codex, theo nhật ký cũ.
- **Phiên bản/model:** nhật ký cũ ghi “Codex desktop, GPT-5”, không kèm
  bằng chứng xác nhận. Giữ là metadata chưa xác minh, không coi là model
  chính xác và không thay bằng model RAG `gpt-5.6-sol`.
- **Auth mode:** log cũ ghi phiên workspace đã đăng nhập, chưa xác minh
  subscription/API cụ thể. Không lưu credential.
- **Thời gian:** 23/09/2026, Asia/Ho_Chi_Minh; log cũ không ghi giờ gửi.

## Nhật ký 1 - Khảo sát yêu cầu và kiến trúc

**Context/Evidence đã ghi:** specification, `AGENTS.md`, source/evidence
Day 01-03, lab guide Day 04 và verification contract.

**Prompt, bản dịch:**

> Kiểm tra kiến trúc InsightHub sau merge và nguồn yêu cầu Day 04. Ánh xạ
> từng Must-have/acceptance tới code hiện có, phần thiếu và evidence.
> Giữ mục tiêu rubric L3, loại Should-have/Nice-to-have và tính năng
> Day 05-06. Chưa triển khai trước khi kế hoạch đủ để review.

**Lý do hiệu quả đã ghi:** Truy vết requirement tới source giúp phát hiện
thiếu queue metric, token/cost thật và khác biệt namespace.

**Điều chỉnh/review đã ghi:** Giữ `insighthub-dev`, telemetry local-first;
loại Sift, SLO mở rộng và MLOps hands-on khỏi phạm vi.

## Nhật ký 2 - Telemetry và anomaly contracts

**Context/Evidence đã ghi:** kế hoạch Day 04 đã review, metrics ứng dụng,
Helm chart, semantics ARQ queue và yêu cầu verifier Prometheus.

**Prompt, bản dịch:**

> Chỉ triển khai observability Day 04 đã duyệt. Tái sử dụng Helm Day 03
> và MCP read-only Day 02. Thêm HTTP duration với labels hữu hạn, token
> theo provider/model và giá đã review, exporters PostgreSQL/Redis độc
> lập, ServiceMonitors, chín query panels, anomaly bands một giờ cùng
> tests, resource limits và retention 15 ngày. Giữ contract ứng dụng và
> để monitoring opt-in.

**Lý do hiệu quả đã ghi:** Gắn thay đổi code với yêu cầu Day 04, giữ chart
Day 03 render được khi không bật monitoring.

**Điều chỉnh/review đã ghi:** Dùng sorted-set size cho ARQ, hướng tới giữ
unknown khi thiếu scrape, tách cost estimate khỏi billing, dùng Kubernetes
metrics cho web/resources. Review 24/09 phát hiện Redis down chưa thực thi
đúng quyết định giữ unknown; xem review Day 04.

## Nhật ký 3 - Thiết kế incident và RCA theo evidence

**Context/Evidence đã ghi:** anomaly rules, topology Kubernetes, ranh giới
quyền MCP và RCA schema của verifier Day 04.

**Prompt, bản dịch:**

> Thêm ba kịch bản lab có thể phục hồi cho LLM latency, queue backlog và
> server error burst. Mỗi mutation phải kiểm tra lab đã chọn, giữ trạng
> thái trước thay đổi và có cách dừng rõ ràng. Điều tra AI/MCP chỉ đọc.
> Định nghĩa RCA JSON và quy trình evidence để mỗi citation khớp mẫu
> Prometheus live tại đúng timestamp. Không tạo RCA placeholder.

**Lý do hiệu quả đã ghi:** Tách mutation của operator khỏi điều tra chỉ đọc,
tránh coi telemetry tự tạo hoặc cũ là runtime evidence.

**Điều chỉnh/review đã ghi:** Dùng bounded proxy cho latency/error,
lưu/restore worker replicas cho backlog; chưa tạo RCA trước khi incident
thực sự chạy. Ba RCA được bổ sung sau đó ở commit `2da93b3`.

## Provenance cần bổ sung

Chưa có transcript/tool-call reference và metadata host đầy đủ để xác nhận
ba bản tóm tắt chính là prompts đã gửi. Bổ sung từ phiên gốc khi có; không
tự dựng timestamp/model hoặc gán kết quả runtime cho prompt mới.
