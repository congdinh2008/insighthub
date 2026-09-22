# Day 03: Provision and deploy InsightHub with Terraform and GitHub Actions

## Result

Adds a reproducible Day 03 infrastructure path for the existing five-component InsightHub workflow. Terraform defines the AWS network, EKS, private encrypted RDS/ElastiCache, ECR, Secrets Manager and IRSA. Helm deploys web, API and ingestion worker, and GitHub Actions gates a source-bound saved plan through formatting, lint, security, policy, cost review and protected apply.

The minimum AWS lab was deployed in `ap-southeast-1`, verified through CloudFront HTTPS with automated smoke and Microsoft Edge, and destroyed immediately after acceptance.

## Review focus

- Bootstrap/core/platform/edge state ownership and S3 native lockfile.
- Exact GitHub Environment OIDC subjects and separate plan/apply policies.
- RDS/Redis network scope, encryption and lifecycle.
- Application-secret scope and IRSA ServiceAccount binding.
- Saved-plan checksum, clean source binding, Infracost comment and manual approval.
- Dependency-ordered teardown and direct AWS inventory.

## Validation

- Terraform fmt and validate: bootstrap/core/platform/edge PASS.
- TFLint: 0 errors, 0 warnings.
- Checkov: 301 passed, 0 failed, 13 documented skips.
- Conftest: real plan and valid fixture PASS; unsafe fixture rejected.
- Day 03 tests: 5 passed.
- GitHub OIDC pipeline and protected apply: PASS.
- EKS: API 2/2, web 1/1 and worker 1/1 Ready.
- Public smoke: health 200, upload 202, Ready polling, chat/citations and metrics PASS.
- Microsoft Edge: HTTPS load, document list, fixture answer, citations and console PASS.
- Fresh no-drift plan before cleanup: 0 add, 0 change, 0 destroy.
- Teardown: edge, ALB, EKS, RDS, Redis, ECR, VPC, bootstrap and remote state removed; KMS keys scheduled for AWS-required deletion window.
