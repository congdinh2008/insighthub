# Corpus mô phỏng để kiểm thử RAG
Các tài liệu ở đây là dữ liệu mô phỏng, không phải yêu cầu/SLO hoặc cam kết vận hành của lớp. Kiến trúc có thể mô tả trạng thái mục tiêu sau extension; đối chiếu starter bằng spec active.

| File | Mục đích |
|---|---|
| so-tay-van-hanh.md | Ingest/retrieval cơ bản |
| service-level-objectives.md | Corpus tiếng Anh, SLO giả định cho bài tập |
| huong-dan-nguoi-moi.md | Chứa indirect prompt injection cố ý cho Day6 |

Day6: upload corpus có injection, chứng minh chunk được retrieve, thử câu hỏi phù hợp, quan sát output và boundary quyền. Chạy lại benign sau fix. Tag context hoặc prompt riêng không đủ bảo đảm chống injection; enforce quyền/schema/budget ở tool. Không dùng secret thật.
[Hướng dẫn Day6](../docs/lab-guides/Day6-Security-Governance-FinOps.md).
