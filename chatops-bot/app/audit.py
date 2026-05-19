"""
InsightHub ChatOps Bot — Audit log (SKELETON)

Mọi tool call của bot PHẢI được ghi audit. Đây là yêu cầu bảo mật cốt lõi:
khi AI agent có quyền chạm vào hạ tầng, phải có dấu vết kiểm toán.

TODO Day 5: hoàn thiện theo gợi ý dưới.
"""
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("chatops-bot.audit")


def log_tool_call(
    user: str,
    tool: str,
    args: dict,
    result_summary: str,
    approved: bool = True,
) -> None:
    """
    Ghi 1 dòng audit cho mỗi tool call.

    TODO Day 5:
    - Ghi ra file hoặc stdout dạng structured JSON (mỗi dòng 1 record).
    - Trong production thật: đẩy sang log aggregator (Loki...).
    - Trường tối thiểu: timestamp, user, tool, args, kết quả, approved.

    Ví dụ record:
      {"ts": "...", "user": "U123", "tool": "kubectl_get_pods",
       "args": {...}, "result": "5 pods Running", "approved": true}
    """
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": user,
        "tool": tool,
        "args": args,
        "result": result_summary,
        "approved": approved,
    }
    # TODO: thay bằng ghi file / gửi log aggregator
    logger.info("AUDIT %s", json.dumps(record, ensure_ascii=False))
