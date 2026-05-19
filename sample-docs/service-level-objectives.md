# InsightHub Service Level Objectives

## Availability

The InsightHub API service targets 99.5% monthly availability. This allows for
approximately 3.6 hours of downtime per month. Planned maintenance windows are
excluded from this calculation and are announced at least 48 hours in advance.

## Latency Targets

The chat endpoint targets a 95th percentile latency of under 5 seconds for a
complete RAG query. This includes both vector retrieval and LLM generation.
The document upload endpoint targets a 95th percentile latency of under 2
seconds for accepting the file, with ingestion happening asynchronously.

## Error Budget

The error budget for InsightHub is 0.5% per month. If the error rate exceeds
this budget, the team freezes new feature deployments and focuses on
reliability improvements until the budget recovers.

## Incident Response

Incidents are classified into three severity levels. Severity 1 means the
service is completely down and requires immediate response within 15 minutes.
Severity 2 means degraded performance and requires response within 1 hour.
Severity 3 means a minor issue and is handled during normal business hours.

## On-Call Rotation

The DevOps team maintains a weekly on-call rotation. The on-call engineer is
responsible for responding to alerts and coordinating incident response. A
handoff meeting happens every Monday morning to transfer context.
