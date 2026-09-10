# Ingestion worker — Day 1

Đây là container worker độc lập. Entry point `worker.py` chỉ import
`app.worker.WorkerSettings`; pipeline `process_document()` vẫn có đúng một bản tại
`api/app/services/ingestion.py`. Vì vậy API test và worker production dùng chung
row lock, content hash, pipeline identity và transaction.

`requirements.txt` tham chiếu lock có hash tại `api/requirements.txt`. Dockerfile
build từ root repository, chạy non-root UID 1001 và dùng payload volume chỉ đọc.
Compose chạy `arq ingestion_worker.worker.WorkerSettings`.

Worker nhận document ID từ Redis, đọc `/app/payloads/<id>.payload`, gọi pipeline
và log JSON `ingestion_completed` sau khi DB commit `ready`.
