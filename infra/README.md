# InsightHub Infrastructure

Day 03 infrastructure solution for the DO2603 running project. Read [SPEC.md](SPEC.md) before changing Terraform.

## Roots

| Path | Ownership |
|---|---|
| `bootstrap/` | KMS, private S3 state/plan storage, GitHub OIDC and plan/apply roles |
| `./` | VPC, EKS, RDS, ElastiCache, ECR, application secret and IRSA roles |
| `platform/` | EKS namespace, application ServiceAccount and namespaced RBAC |
| `modules/` | Reusable network, EKS, database, cache and registry modules |
| `policies/` | Conftest rules plus safe and unsafe plan fixtures |

The roots use separate state keys. Bootstrap runs first with a short-lived administrative session. Core runs through the reviewed GitHub plan/apply roles. Platform runs only after the EKS API is reachable.

## Local quality gates

```sh
make tools-day3
make test-day3
```

`terraform init -backend=false` validates source without creating cloud resources. See [Day 03 Runbook](../docs/day3/Runbook.md) for required cloud inputs, controlled apply, acceptance and teardown.

Do not commit `.terraform/`, state, saved plans, plan JSON, kubeconfig, credentials or runtime secrets. A local PASS proves the source and policy gates only; it does not prove EKS, RDS, OIDC, HTTPS or GitHub Actions ran.
