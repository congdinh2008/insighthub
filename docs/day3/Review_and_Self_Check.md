# Day 03 - Review and Self-Check

## Requirement review

| ID | Implementation | Evidence |
|---|---|---|
| MH1 | Core files plus reusable network, EKS, database, cache and registry modules | Terraform validation and AWS apply PASS |
| MH2 | KMS-encrypted S3 backend with native `use_lockfile` | Remote init, saved plan and state operations PASS |
| MH3 | Platform namespace `insighthub-dev` | Terraform state and live EKS namespace verified before teardown |
| MH4 | RDS PostgreSQL 16, encrypted, TLS, private | PostgreSQL 16.10 runtime inventory PASS |
| MH5 | ElastiCache Redis 7, private data subnets, TLS and encryption | Redis 7.1 runtime inventory PASS |
| MH6 | IRSA role and annotated ServiceAccount | Live ServiceAccount and secret consumption PASS |
| MH7 | `.github/workflows/iac.yml` | Workflow source and GitHub execution verified |
| MH8 | fmt, lint, scan, policy, plan, cost and protected apply | All required jobs verified |
| MH9 | Green PR pipeline | Runs 35743383750 and 35748659389 PASS |
| MH10 | Helm deployment of web, API and worker | API 2/2, web 1/1, worker 1/1 Ready |
| MH11 | Upload-to-chat smoke | HTTPS upload 202, Ready polling and chat 200 PASS |
| MH12 | TFLint zero warning | CI PASS |
| MH13 | Checkov no failed check | 301 passed, 0 failed |
| MH14 | Standard and lab tags | AWS tag inventory verified before teardown |
| SH1 | Rego policy and positive/negative fixtures | Valid plan accepted; unsafe fixture rejected |
| SH2 | Infracost PR comment | Regional plan estimate and PR comment generated |
| SH3 | Dev/staging variables and Helm values | Render and validation PASS; only dev was applied |
| SH4 | AI-reviewed plan explanation | PR comment records actions, risks, cost and decision |
| SH5 | Protected apply environment | GitHub Environment and OIDC subject verified |

## Review findings

- The source-bound reviewed plan is stored privately with a checksum and is applied without regeneration.
- The source fingerprint is captured before Terraform creates transient plan files, keeping CI provenance deterministic.
- GitHub plan and apply roles use exact Environment OIDC subjects and no long-lived AWS key.
- The application IRSA policy identifies one Secrets Manager ARN and one KMS key.
- RDS and Redis are private and encrypted; public traffic enters only through the temporary CloudFront and ALB path.
- Minimum lab sizing used two `t3.medium` EKS nodes, one `db.t4g.micro` RDS instance and one `cache.t4g.micro` Redis node.
- Teardown ran immediately after acceptance; direct AWS inventory verified cleanup instead of relying only on Terraform state.

## Self-check answers

1. **SPEC sections:** objective, scope, inputs, architecture, ownership, security/policy, pipeline contract and measurable acceptance.
2. **3-Layer Defense:** AI-assisted generation proposes source; human review checks intent, trust, network, lifecycle and cost; automated TFLint, Checkov and Conftest gates verify the reviewed plan before apply.
3. **Tool roles:** TFLint checks Terraform/provider conventions; Checkov checks known IaC security controls; Conftest enforces InsightHub-specific rules over plan JSON.
4. **OIDC:** GitHub exchanges a short-lived token whose audience and exact Environment subject are checked by AWS. No reusable AWS access key is stored in GitHub.
5. **Cost:** core estimate is `$244.288/month` or about `$0.334641/hour`; a 3.1-hour lab is approximately `$1.04` before usage-based ALB, transfer, NAT traffic, log and request charges.
6. **Tags:** live Terraform-managed resources exposed the required project, environment, owner, cost center, managed-by and lab cleanup tags. Provider-managed child resources were checked separately.
7. **Managed RDS:** Day 03 requires private encrypted PostgreSQL with managed backup, maintenance and lifecycle controls outside pod scheduling. StatefulSet PostgreSQL remains appropriate only for reproducible local verification.
