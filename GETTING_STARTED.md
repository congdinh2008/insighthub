# Khởi động InsightHub DO2603

## 1. Môi trường
Docker Engine/Desktop có Compose v2, Git và Python 3.11+ cho verifier. Build ứng dụng dùng Python 3.12 và Node 24 LTS trong container, không cần cài Node trên host. Bắt đầu fixture trên máy có khoảng 4 GB RAM dành cho Docker; đây là ngân sách thử nghiệm, đo thực tế bằng `docker stats --no-stream`. Model local cần thêm RAM theo model/quantization.

```bash
cp .env.example .env
docker compose config --quiet
docker compose up --build -d --wait
python3 scripts/verify.py setup
python3 scripts/verify.py smoke
```

Nếu trùng port, sửa API_PORT/WEB_PORT trong .env rồi truyền URL tương ứng vào verifier:
```bash
python3 scripts/verify.py smoke --api-url http://localhost:18000 --web-url http://localhost:13000
```
Không chạy `docker compose config` có nội dung lên log công khai khi đã điền secret. Dùng `--quiet`.

## 2. Contract starter
| Hành động | Endpoint | Kỳ vọng |
|---|---|---|
| Liveness và cấu hình mode | GET /healthz | HTTP 200 khi process sống |
| Readiness DB/schema/index | GET /readyz | 200 sẵn sàng, 503 chưa sẵn sàng |
| Upload .txt/.md/.pdf | POST /documents, multipart field file | 201; sync ingestion trong starter |
| Xem trạng thái | GET /documents | Danh sách chứa id, status, chunk_count |
| Xóa tài liệu của lab | DELETE /documents/{id} | Xóa tài liệu và chunks |
| Hỏi đáp | POST /chat với question | answer, sources và contexts |
| Telemetry | GET /metrics | Prometheus exposition |

Không có endpoint /upload hay /documents/{id}/status trong contract này. Smoke hiểu cả sync 201 và async 202, poll GET /documents tới ready hoặc failed với deadline. Frontend cũng hỗ trợ pending để dùng sau bài Day 1 worker.

## 3. Test baseline
```bash
make test-backend
python3 -m unittest discover -s tests -p 'test_verify*.py' -v
python3 scripts/verify.py
```
Unit-only: docker compose exec api python -m unittest discover -s tests -p 'test_unit*.py' -v. Database integration phải dùng database lab riêng. Cài MCP tools bằng `make tools` trước `make test`. `make test` chạy bộ baseline; Day verifiers chưa hoàn tất là bình thường khi chưa hoàn thiện các task dự án. PASS cấu trúc không đồng nghĩa milestone hoàn thành.

## 4. Chuyển sang real provider
1. Hoàn thành smoke fixture, hiểu generation và embedding tách biệt.
2. Chọn model từ tài liệu nhà cung cấp, kiểm tra account/region, license và giá tại ngày chạy. Ghi model ID, version/digest và ngày vào evidence.
3. Sửa RAG_MODE=real, LLM_PROVIDER và EMBEDDING_PROVIDER. Điền khóa và model tương ứng. Không đưa secret vào Git, prompt, ảnh hay báo cáo.
4. Dùng database/project Compose mới cho embedding space mới. Không trộn fixture với real hoặc hai embedding model, kể cả cùng dimension. Starter khóa identity gồm model/provider/dimension/endpoint/revision; đổi identity cần reindex. Ghi rõ migration và backup nếu dữ liệu có giá trị.
5. Chạy smoke và dataset có expected citations. Lỗi provider phải hiện thành lỗi có kiểm soát, không được tự đổi sang fixture.

OpenAI-compatible gateway: provider=openai, OPENAI_BASE_URL tường minh và key/model thích hợp. Kiểm tra thực tế contract chat/embeddings, timeout, usage và lỗi; nhãn “compatible” không bảo đảm mọi extension. Không có alias Bedrock giả trong starter. Muốn Bedrock phải bổ sung adapter AWS thật, IAM, region, model access và tests.

### Ollama local tùy chọn
Ưu tiên native Ollama trên macOS để dùng Metal; container CPU phù hợp smoke nhỏ trên Linux/Docker, GPU cần cấu hình phù hợp host. Không mặc định tải model 14B.
- Chọn chat model nhỏ vừa RAM, đo latency và đạt dataset trước khi tăng model.
- Embedding adapter starter dùng riêng `mxbai-embed-large`, 1024 chiều. Không dùng reasoning/chat model để embed, không pad/truncate vector tùy ý.
- Với profile container:
```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull mxbai-embed-large
# Pull chat model đã chọn, ghi đúng tên vào OLLAMA_CHAT_MODEL.
docker compose exec ollama ollama list
```
Ghi digest model đã tải; image Ollama được pin 0.33.3 nhưng model tag có thể đổi. Với native macOS, OLLAMA_BASE_URL trong container trỏ endpoint host đã cấu hình, thường http://host.docker.internal:11434; xác minh endpoint và giới hạn truy cập mạng của host.
Không gọi Ollama local là “miễn phí hoàn toàn”: tách phí API khỏi RAM/CPU/GPU, thời gian và điện năng chưa đo.

## 5. Dừng và reset
```bash
docker compose down
```
Dừng/xóa container và network của project, giữ volume tài liệu. Nếu muốn xóa toàn bộ dữ liệu lab của project hiện tại sau khi đã lưu bằng chứng:
```bash
docker compose down --volumes
```
Dừng cả Ollama profile nếu đã bật: `docker compose --profile ollama down`. Không dùng prune toàn máy.
AWS chỉ dùng sau local gate và phải xóa ngay cuối mỗi lượt thực hành theo [guide bắt buộc](docs/Guide_Local_AWS_Cost_DO2603.md).

## Milestone verifier dependencies
Khi bắt đầu nộp bài Day 1-6, tạo venv riêng và cài `python -m pip install --require-hashes -r scripts/requirements-verification.txt`. Baseline verifier regression dùng Python standard library. Chi tiết tên scenario/artifact ở scripts/VERIFICATION_CONTRACT.md.

## Ranh giới starter và milestone
Smoke sync201 chỉ xác minh starter. Day 1 bắt buộc async202/worker; không dùng smoke starter thay verify-day-1. Sau đó tiếp tục đủ task trong spec v3.3; gateway/MCP mẫu/bot skeleton không làm sẵn bài học viên.

## Học liệu trước buổi
Đọc 7 Knowledge Content và 7 Tool Guideline trong gói AI_DevOps_HocLieu_v2.0 DO2603 do mentor cung cấp, theo 00_INDEX.md của gói. Ví dụ ParcelOps luyện công cụ độc lập; bài nộp vẫn là InsightHub theo specification trong repo. Không cần sao chép học liệu vào code base.

## Coding host
Chọn một trong ba: Claude Code, ChatGPT-Codex hoặc Antigravity. Hoàn thiện AGENTS.md và setup context/MCP theo [host guide](docs/Guide_Coding_Host_DO2603.md); không bắt dùng host thứ hai.

## Quy trình mỗi ngày
1. Đọc Day tương ứng trong [specification](Running-Project-Specification-Student.md) và [lab guide](docs/lab-guides/README.md), kiểm tra đầu vào kế thừa ngày trước.
2. Tạo branch `day{N}-<topic>` từ trạng thái đã hoàn thiện ngày trước trong repo của mình; giữ một dự án tích lũy.
3. Viết yêu cầu và constraints trước khi dùng host đã chọn. Review diff, chạy tests; lưu ít nhất 3 prompts cùng quyết định và bằng chứng vào `ai-prompts/day{N}.md`.
4. Chạy verifier của ngày, ghi rõ phần PASS/FAIL/INCOMPLETE; đối chiếu đầy đủ Must-have và rubric. Nộp PR, source và evidence theo mục 4 và submission format của ngày trong specification.
5. Lưu evidence, dừng local khi không dùng; nếu tạo AWS services phải xóa ngay sau lượt thực hành. Ngày sau tái dựng từ code.

## Xử lý sự cố khởi động
| Hiện tượng | Kiểm tra và xử lý |
|---|---|
| Port đã được dùng | Đổi API_PORT/WEB_PORT trong .env và URL truyền cho smoke; không dừng ứng dụng khác tùy tiện. |
| Web mở được nhưng không tải danh sách | `docker compose ps`, `docker compose logs --tail=100 api postgres`, kiểm tra `/readyz`; khôi phục API rồi bấm Làm mới trạng thái. |
| DB thiếu extension/schema hoặc embedding identity không khớp | Kiểm tra image pgvector, `infra/db/init.sql` và cấu hình provider/dimension. Init SQL chỉ chạy trên volume mới; dùng project lab mới hoặc migration/reindex có chủ đích, không xóa dữ liệu có giá trị. |
| Chat báo chưa có tài liệu | Upload mẫu trong `sample-docs/`, xác nhận status ready và chunk_count > 0. File PDF scan không có text cần OCR trước; starter không cung cấp OCR. |
| Provider lỗi hoặc timeout | Kiểm tra key/model/endpoint, quyền model và giới hạn provider; xem log đã che lỗi nhạy cảm. Real mode không tự fallback sang fixture. |
| MCP chưa kết nối | Kiểm tra runtime, đường dẫn tuyệt đối, cấu hình đúng host và transport; dùng Inspector/tools list/call theo host guide. Không tăng quyền chỉ để bỏ lỗi. |
| Verifier ngày chưa đạt trên starter | Đây là các đầu ra học viên phải triển khai. Đọc VERIFICATION_CONTRACT và task của ngày; không bỏ assertion để lấy PASS. |

Khi cần hỗ trợ, gửi lệnh tái hiện, môi trường, expected/actual và log đã loại secret; ghi branch/commit đang chạy. Không gửi .env hoặc API keys.
