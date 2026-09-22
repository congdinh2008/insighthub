# Day 03 - Execution Report

Observed at: `2026-09-22T12:31:00Z` to `2026-09-22T15:48:00Z`
Branch: `day3-terraform`
AWS account: `241459378947`
AWS region: `ap-southeast-1`
Runtime mode: EKS with fixture LLM and embedding providers

## Verified results

| Gate | Result |
|---|---|
| Terraform fmt and validate | PASS for bootstrap, core, platform and edge |
| TFLint recursive | PASS, 0 errors and 0 warnings |
| Checkov | PASS, 301 checks passed, 0 failed, 13 documented resource-specific skips |
| Conftest | PASS for the real plan and valid fixture; unsafe fixture rejected |
| Day 03 tests | PASS, 5 tests |
| GitHub OIDC pipeline | PASS, separate plan/apply roles and protected apply environment |
| Reviewed-plan integrity | PASS, S3 object checksum matched before apply |
| Infracost | PASS, report and PR comment generated from the reviewed regional plan |
| EKS runtime | PASS, API 2/2, web 1/1 and ingestion worker 1/1 Ready with zero restarts |
| Managed data | PASS, private encrypted RDS PostgreSQL 16.10 and Redis 7.1 with TLS |
| IRSA and secret | PASS, annotated ServiceAccount and exact application-secret IAM resource |
| Public HTTPS smoke | PASS through CloudFront and ALB |
| Microsoft Edge | PASS for document list, RAG question, fixture answer, citations and console health |
| Fresh no-drift plan | PASS, 0 add, 0 change, 0 destroy before teardown |
| Cloud cleanup | PASS, billable Day 03 resources removed after testing |

Full deployment and AWS smoke run: [GitHub Actions 35743383750](https://github.com/congdinh2008/insighthub/actions/runs/35743383750).

Final source verification and Infracost PR run: [GitHub Actions 35748659389](https://github.com/congdinh2008/insighthub/actions/runs/35748659389).

## Runtime acceptance

- EKS cluster `insighthub-dev` ran Kubernetes 1.34 with private and CIDR-restricted public API access, secrets encryption and all five control-plane log types.
- Namespace `insighthub-dev` contained two API pods, one web pod, one ingestion-worker pod and a successful database migration job.
- RDS used PostgreSQL 16.10, `db.t4g.micro`, private data subnets, storage encryption, TLS enforcement and one-day lab backup retention.
- ElastiCache used Redis 7.1, `cache.t4g.micro`, one lab node, private data subnets, at-rest encryption and in-transit encryption.
- The application role allowed `GetSecretValue` only for `insighthub/dev/application`; the running pods mounted and consumed that secret successfully.
- Automated HTTPS smoke returned health 200, upload 202, a Ready document with one chunk, chat 200 with answer and citations, and Prometheus metrics 200.

## Cost review

Infracost estimated the Terraform core at `$244.288/month` for continuous 730-hour operation, or approximately `$0.334641/hour`. Main monthly drivers were the EKS node group `$84.288`, EKS control plane `$73`, NAT Gateway `$43.07`, RDS `$21.01` and ElastiCache `$17.52`.

The core lab ran for approximately 3.1 hours, giving a normalized core estimate of about `$1.04`. ALB/LCU, CloudFront requests and transfer, NAT traffic, ECR storage, logs and provider billing rounding are usage-based additions. The AWS bill is authoritative because cost data is delayed.

## Teardown evidence

- Terraform edge destroy: 1 CloudFront distribution removed.
- Ingress deletion: AWS Load Balancer Controller removed the ALB before EKS deletion.
- Terraform core destroy: 64 resources removed and remote core state emptied.
- Direct inventory returned no EKS cluster, RDS instance or snapshot, ElastiCache group, ALB, CloudFront distribution, ECR repository, flow log or project security group.
- Application secret entered its seven-day Secrets Manager recovery window.
- Five core KMS keys and the bootstrap state key entered `PendingDeletion` with deletion date `2026-09-29`; AWS does not permit immediate deletion.
- Bootstrap state bucket, GitHub OIDC provider, plan/apply roles, project policies and service-linked roles were removed last.

## Scope review

Day 03 delivered only the required infrastructure, policy gates, CI/CD, Helm deployment, HTTPS runtime and teardown workflow. Day 04 observability dashboards, Day 05 ChatOps and Day 06 security gateway work were not added.
