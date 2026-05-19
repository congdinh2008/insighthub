# Security, Governance, FinOps - bắt buộc Day 6

Học viên hoàn thiện Promptfoo50+ cases, initial/final reports, guardrails runtime, LiteLLM gateway+3 virtual keys/budgets, routing cho app/bot/coding agent, cost dashboard và threat model>=6 threats. [Spec mục10](../Running-Project-Specification-Student.md).

Config skeleton chỉ giúp bắt đầu; cần actual allowed/blocked, indirect injection qua ingestion/retrieval, budget/bypass tests. Dataset/eval tự viết bổ sung, không thay Promptfoo/guardrails/gateway.

Cấu hình hiện tại là scaffold, chưa đủ 50 ca. Ghi coverage mapping cho direct/indirect injection, RAG poisoning, PII và excessive agency. Dùng plugin IDs của bản pin; strategy cũ `prompt-injection` đã đổi thành `jailbreak-templates`. Nguồn: [plugins](https://www.promptfoo.dev/docs/red-team/plugins/), [migration strategy](https://www.promptfoo.dev/docs/red-team/strategies/prompt-injection/). Target HTTP gọi /chat chỉ kiểm tra câu hỏi; poisoning phải đi qua upload/retrieval bằng adapter học viên xây.
