# ChatOps - bắt buộc Day 5

Starter trả501 và health ready=false để không nhận event trước auth. Học viên triển khai Slack bot LIVE đủ3 intents (health, ingestion count, pods lỗi), tái sử dụng MCP K8s/Prometheus Day2, signature/replay, permissions/approval và audit, tests/screencast.

Transport double là unit test; không thay Slack App kết nối thật. HTTP signature kiểm tra trước challenge; ACK<3s tách khỏi AI reply bằng queue/dedup/retry. Socket Mode có thể bổ sung, giữ mục tiêu/tests bảo mật của spec. [Spec mục 9](../Running-Project-Specification-Student.md).
