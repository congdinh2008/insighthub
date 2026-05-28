"""
InsightHub — ARQ WorkerSettings

ARQ đọc class này để biết:
  - functions: danh sách task có thể xử lý
  - redis_settings: kết nối Redis
  - max_jobs, job_timeout, retry_jobs: tuning
"""
import logging
import os

from arq.connections import RedisSettings

from worker.tasks import ingest_document

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

_redis_url = os.getenv("REDIS_URL", "redis://redis:6379")


class WorkerSettings:
    functions = [ingest_document]
    redis_settings = RedisSettings.from_dsn(_redis_url)

    max_jobs = 10
    job_timeout = 300          # 5 phút tối đa mỗi job
    health_check_interval = 30
    retry_jobs = True
    max_tries = 3              # retry tối đa 3 lần (exponential backoff ARQ tự xử lý)
    keep_result = 3600         # giữ kết quả 1 giờ (dùng để debug)
