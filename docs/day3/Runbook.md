# Day 03 - Runbook

## 1. Local quality gates

```sh
python3 tools/iac/install.py
make test-day3 PYTHON=tmp/day3/venv/bin/python
```

Expected: Terraform fmt/validate passes for bootstrap/core/platform/edge, TFLint has no warning, Checkov has no failed check, both Conftest fixtures behave as expected, Helm lint/render passes and all Day 03 tests pass.

## 2. Local Kubernetes and smoke

```sh
python3 tools/iac/local_lab.py up
python3 tools/iac/local_lab.py status
kubectl --context kind-insighthub-local -n insighthub-dev port-forward service/insighthub-api 18000:8000
kubectl --context kind-insighthub-local -n insighthub-dev port-forward service/insighthub-web 13000:3000
python3 scripts/verify.py smoke --api-url http://127.0.0.1:18000 --web-url http://127.0.0.1:13000 --json
```

Expected: web, API, ingestion worker, PostgreSQL and Redis are Ready. Smoke receives health 200, upload 202, the uploaded document becomes Ready within 30 seconds and chat returns an answer with citations.

Use Microsoft Edge at `http://127.0.0.1:13000`. Check document list, ask a question tied to the uploaded document, validate the citation and inspect browser console errors. File upload through Computer Use requires the browser extension setting `Allow access to file URLs`; automated API smoke remains the authoritative upload evidence when that local browser permission is disabled.

Cleanup only this lab:

```sh
python3 tools/iac/local_lab.py down
```

## 3. Cloud prerequisites

Do not start bootstrap until all rows are reviewed.

| Input | Required value |
|---|---|
| AWS identity | Short-lived sandbox SSO/STS identity, confirmed account and region |
| Network | Two AZ IDs and reviewed runner/admin CIDRs |
| Governance | Owner, cost center, lab ID, expiry, per-run budget and stop time |
| IAM | Customer-managed plan/apply policies and AWS Load Balancer Controller policy ARN |
| GitHub | Plan/apply environments, required reviewer, repository variables and Infracost key |
| HTTPS | No domain is required for the minimum lab; CloudFront supplies its default trusted certificate |
| Runtime | Provider secret JSON, without printing it in logs |

Required GitHub variables: `AWS_REGION`, `AWS_PLAN_ROLE_ARN`, `AWS_APPLY_ROLE_ARN`, `AWS_LOAD_BALANCER_CONTROLLER_POLICY_ARN`, `TF_STATE_BUCKET`, `TF_STATE_KMS_ARN`, `LAB_OWNER`, `COST_CENTER`, `LAB_EXPIRES_AT`, `EKS_ADMIN_CIDRS`.

Required secrets: `INFRACOST_API_KEY`, `INSIGHTHUB_PROVIDER_SECRET_JSON`.

Bootstrap also owns the account-scoped service-linked roles required by the EKS control plane, EKS managed node groups, RDS, ElastiCache and Elastic Load Balancing when the sandbox account has never used those services. Destroy them last, after the corresponding services have finished deleting.

## 4. Bootstrap and reviewed deployment

1. Copy `infra/bootstrap/terraform.tfvars.example`, fill non-secret reviewed values and apply bootstrap with the short-lived setup identity.
2. Configure the two GitHub Environments with their exact role ARNs. Require a reviewer for `insighthub-dev`.
3. Open the Day 03 PR. Review fmt, lint, security, policy, plan and cost results. Reject unexpected delete/replace, broad IAM, public data access or cost above the lab budget.
4. Add the AI-reviewed sanitized plan explanation to the PR. Include create/change/destroy counts, IAM/network/data risk, cost assumptions and unknown values.
5. Run workflow dispatch with `apply=true`. Approve only the protected apply environment after the saved-plan checksum and cost comment are reviewed.
6. Apply the edge root after the ALB is ready. The final workflow step runs the public HTTPS smoke test against the CloudFront URL.
7. Verify namespace, ServiceAccount annotation, workloads, RDS/Redis status, tags and a denied attempt to read an unrelated secret.

The workflow passes the reviewed AWS region and EKS VPC ID directly to the Load Balancer Controller, avoiding a dependency on node access to EC2 Instance Metadata.

## 5. Teardown

Record sanitized evidence before teardown. Remove in dependency order: CloudFront edge, Helm release/Ingress and ALB, platform state, core state, images and repositories, then bootstrap only after all other state is safely removed. Check CloudFront, ALB, ENI, EIP, RDS snapshots, ElastiCache snapshots, ECR images, CloudWatch logs, Secrets Manager recovery state and S3 plan prefix. Do not rely only on an empty Terraform state.

Keep the state bucket only if the course owner explicitly needs it for later labs. Otherwise destroy it last after exporting the required sanitized reports. Confirm the AWS inventory and billing view show no remaining Day 03 resources.
