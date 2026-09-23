# Day 03 - Microsoft Edge E2E Report

Observed at: `2026-09-22T15:08:00Z`
Browser: Microsoft Edge through Computer Use
URL during test: `https://df54vcp50gmxq.cloudfront.net`
Environment: EKS `insighthub-dev`, fixture provider mode

## Scenario

1. Opened the temporary CloudFront HTTPS endpoint in Microsoft Edge.
2. Confirmed the InsightHub page title and application shell loaded correctly.
3. Confirmed the documents created by the fresh automated upload were `ready` with one chunk.
4. Asked `InsightHub có bao nhiêu thành phần chính sau Day 01?`.
5. Confirmed the answer contained `InsightHub gồm 5 thành phần chính`.
6. Confirmed two verified source citations were rendered.
7. Confirmed the UI displayed a 31 ms fixture latency.
8. Queried Edge console error and warning entries; the result was an empty list.

## Result

PASS for trusted HTTPS load, document-state display, question submission, answer rendering, citations and console health. The same live deployment's upload, ingestion, Ready polling, chat and metrics paths passed the automated public HTTPS smoke test with upload HTTP 202.

The temporary URL was intentionally removed after acceptance testing as required by the short-lived lab cleanup policy.
