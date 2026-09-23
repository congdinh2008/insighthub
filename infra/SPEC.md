# InsightHub Day 03 - Infrastructure Specification

## Objective

Provision the AWS infrastructure and Kubernetes platform required by InsightHub v1, then deploy the existing web, API and ingestion worker without changing Day 01 application contracts. The solution is local-first and uses the same Helm chart for kind and EKS.

## Scope

Included:

- VPC across two Availability Zones with public, private and data subnets.
- EKS control plane, managed node group, encrypted Kubernetes secrets and scoped administrator access.
- RDS PostgreSQL 16 with pgvector schema, encryption, TLS enforcement and private access.
- ElastiCache Redis 7 with encryption, TLS and private access. Dev uses one cache node for minimum lab cost; staging keeps two nodes with automatic failover.
- ECR repositories, Secrets Manager, IRSA, namespace and ServiceAccount.
- S3 backend with native lockfile, GitHub OIDC plan/apply roles and private reviewed-plan storage.
- Terraform, TFLint, Checkov, Conftest, Infracost, Helm and GitHub Actions gates.

Excluded:

- Day 04 observability dashboards and alerting.
- Day 05 ChatOps bot.
- Day 06 runtime guardrails and model gateway.
- A permanent production environment or scheduled drift remediation.

## Inputs

| Input | Constraint |
|---|---|
| AWS account and region | Sandbox account; default region `ap-southeast-1` |
| `availability_zone_ids` | Two stable AZ IDs available in the selected account |
| `admin_cidrs` | Reviewed public CIDRs; `0.0.0.0/0` is rejected |
| Owner, cost center, lab ID, expiry | Required for tagging and cleanup |
| GitHub repository and environments | Exact repository, `insighthub-dev-plan`, `insighthub-dev` |
| IAM policy ARNs | Customer-managed plan, apply and AWS Load Balancer Controller policies |
| HTTPS endpoint | CloudFront default certificate for the lab; an owned domain and ACM certificate can replace it later |
| Provider secret JSON | Gemini credentials/models; stored only as a GitHub secret and Secrets Manager value |

## Architecture

```text
Internet -> CloudFront HTTPS -> ALB HTTP -> web/api Deployments on EKS
                         api -> ElastiCache Redis -> ingestion-worker
                         api/worker -> RDS PostgreSQL + pgvector
                         api/worker -> model provider
                         pods -> Secrets Manager through IRSA and CSI
```

RDS and Redis are managed services, so the AWS deployment has three application workloads and five logical InsightHub components. The local chart creates PostgreSQL and Redis StatefulSets to preserve the five-component workflow without claiming cloud equivalence.

## State and ownership

- `infra/bootstrap` owns KMS, state bucket, GitHub OIDC provider and plan/apply roles.
- `infra` owns network, EKS, data services, ECR, application secret and workload IAM roles.
- `infra/platform` owns the EKS namespace, ServiceAccount and namespaced RBAC.
- Helm owns application workloads, Services, HPA, Ingress, CSI mapping and the schema migration Job.
- Core and platform use separate S3 keys with `use_lockfile = true`.
- Saved plans are KMS-encrypted in a private S3 prefix and removed after successful apply.

## Security and policy

- No long-lived AWS key is used by GitHub Actions.
- The OIDC trust policy binds the exact repository and GitHub Environment.
- Plan and apply use separate IAM roles and reviewed customer-managed policies.
- RDS and Redis are reachable only from the EKS node security group.
- Application pods can read only the application secret through IRSA.
- CloudFront provides a browser-trusted `cloudfront.net` HTTPS endpoint when the lab has no domain or ACM certificate. ALB remains the private origin contract of the edge root.
- Checkov exceptions are resource-specific and include their reason in source.
- Conftest rejects missing standard tags, public RDS, disabled RDS encryption and world-open ingress.
- Raw state, plans, credentials, kubeconfig and generated runtime secrets are never committed.

## Pipeline contract

The workflow order is `fmt`, `lint`, `security-scan`, `policy-check`, `plan`, `cost-estimate`, protected `apply`. Application tests and immutable image builds run in parallel with static IaC gates. Apply consumes the exact saved plan, verifies its checksum, deploys the platform, Helm release and edge distribution, then runs the HTTPS upload-to-chat smoke test.

The `insighthub-dev-plan` environment protects read-only cloud planning. The `insighthub-dev` environment requires a reviewer before the apply role can be assumed. Infracost updates the internal pull request comment. The `verification-source` artifact binds the source fingerprint to a deterministic chart archive.

## Acceptance

| Requirement | Measurable result |
|---|---|
| Terraform | fmt, validate for bootstrap/core/platform and TFLint pass |
| Security | Checkov has zero failed checks; Conftest accepts safe and rejects unsafe fixtures |
| State | S3 backend uses encryption and native lockfile |
| AWS plan | Plan contains EKS, private encrypted RDS, private encrypted Redis, IRSA and standard tags |
| Kubernetes | Namespace `insighthub-dev`; web/api/worker Ready; managed DB/cache checked separately |
| HTTPS | CloudFront endpoint presents a trusted certificate and forwards the required upload/chat methods to the ALB origin |
| Runtime | health 200, upload 202, matching document Ready within 30 seconds, chat 200 with citations |
| Evidence | Run URL, source manifest, cost report, sanitized plan summary, browser report and cleanup inventory |

Local validation does not satisfy AWS acceptance. Cloud items remain unverified until the required account, policies, domain, reviewer and runner inputs are supplied and a real deployment is removed after the lab.
