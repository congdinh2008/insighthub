# Day 03 - AI-Powered IaC & Pipeline

Solution tham khảo DO2603, tiếp nối Day 01-02 trên branch `day3-terraform`.

| Đọc theo thứ tự | Nội dung |
|---|---|
| [Implementation plan](../plans/Day03_Implementation_Plan_v1.0.md) | Scope, steps, expected results and commit strategy |
| [Infrastructure SPEC](../../infra/SPEC.md) | Inputs, topology, ownership, security and acceptance |
| [Prompt pack](../../ai-prompts/day3.md) | Six reusable student prompts from discovery to handoff |
| [Architecture and Decisions](Architecture_and_Decisions.md) | Local/AWS topology and engineering decisions |
| [Runbook](Runbook.md) | Local verification, cloud prerequisites, deploy and teardown |
| [Review and Self-Check](Review_and_Self_Check.md) | Requirement matrix, review findings and answers |
| [Execution Report](../evidence/day3/Execution_Report.md) | Verified local/AWS results, cost and teardown evidence |
| [Browser E2E Report](../evidence/day3/Browser_E2E_Report.md) | Microsoft Edge workflow evidence |
| [PR description](PR_Description.md) | Review-ready description of the final Day 03 change |

The solution was applied to the minimum AWS lab topology, verified through the complete upload-to-chat path in Microsoft Edge and automated smoke tests, then destroyed in dependency order. The execution report links the successful pipelines and records the final cleanup inventory.
