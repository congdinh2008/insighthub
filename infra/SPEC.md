# InsightHub Day 3 infrastructure specification

## Overview

This specification defines the intended AWS infrastructure for the InsightHub
development environment. It is the source of intent for a future Terraform
implementation; it does not provision resources or contain Terraform code.

The target platform is Amazon EKS with the Kubernetes namespace
`insighthub-dev`, Amazon RDS for PostgreSQL, Amazon ElastiCache for Redis, and
short-lived AWS identities. The Day 1 workload remains five application
components: web, API, PostgreSQL-compatible data store, Redis-compatible queue,
and ingestion worker. In AWS, PostgreSQL and Redis are managed services rather
than Kubernetes pods.

AWS is used only for a scoped lab or environment verification after local
validation. A lab must have an owner, expiry, inventory, and a reviewed cleanup
plan; its resources must be removed promptly after the lab unless retention is
explicitly approved.

## Requirements

- Terraform must require version `>= 1.7.0, < 2.0.0`.
- The AWS provider must be constrained to `~> 5.70`.
- The EKS namespace must be named `insighthub-dev`.
- RDS must run PostgreSQL 16, support the `pgvector` extension, encrypt storage
  at rest, use private subnets, and set public accessibility to false.
- ElastiCache must run Redis 7 in private subnets and have no public endpoint.
- Workloads that need AWS permissions must use IRSA through ServiceAccount
  `insighthub`; IAM Users and long-lived AWS access keys are prohibited.
- The Terraform S3 backend must use encryption and `use_lockfile = true`.
- All taggable resources must receive the five required tags: `project`,
  `environment`, `owner`, `cost_center`, and `managed_by = "terraform"`.
- Credentials, database passwords, private keys, AWS Account IDs, and other
  secrets must not be hard-coded or committed. Runtime secrets must be supplied
  through AWS Secrets Manager or another explicitly approved secret-delivery
  integration.

## Constraints

- This is a development/lab design; it must not assume production account,
  region, CIDRs, capacity, availability zones, or DNS names.
- AWS region is configurable. The Day 3 and cost documents do not prescribe a
  value, so the default region is **TBD** and must be confirmed with the sandbox
  account before implementation.
- Account ID must be discovered from the active AWS identity at execution time;
  it is never an input default or a literal in source code.
- Database and cache services are managed AWS services, not StatefulSets.
- RDS and Redis must never allow inbound access from `0.0.0.0/0`. Their security
  groups may allow only the minimum required application/EKS workload security
  groups and ports.
- Network egress, NAT topology, VPC endpoints, EKS control-plane endpoint
  exposure, instance/Fargate topology, node sizes, backup retention, TLS
  details, Kubernetes add-ons, and domain/HTTPS configuration are **TBD** until
  selected and reviewed for the target lab.
- Terraform state can contain sensitive metadata. State bucket access must be
  least-privilege and restricted to the approved human/CI roles; state must not
  be committed.
- No `terraform init`, `plan`, `apply`, or `destroy` is part of this
  specification-writing task.

## Networking

- Create or consume a VPC whose CIDR is an explicit configurable input
  (**TBD**). Do not assume an existing default VPC.
- Place EKS worker/data-plane networking, RDS DB subnet groups, and ElastiCache
  subnet groups across the configured private subnets in the selected AZs.
- RDS and ElastiCache have no public IP/public endpoint exposure. RDS must set
  `publicly_accessible = false` in the future implementation.
- Define separate, least-privilege security groups for EKS workloads, RDS, and
  ElastiCache. Permit PostgreSQL only from approved workload security groups;
  permit Redis only from approved workload security groups. Do not use CIDR-wide
  public ingress rules for either service.
- The exact CIDRs, subnet count, AZ count, egress route design, endpoint
  exposure, and allowed source security groups are **TBD** inputs/review items.

## EKS

- Provision or integrate with an EKS cluster in the selected configurable AWS
  region; cluster name and Kubernetes version are **TBD** inputs.
- Manage Kubernetes namespace `insighthub-dev` declaratively.
- Create ServiceAccount `insighthub` in namespace `insighthub-dev` and annotate
  it with the IRSA IAM role ARN produced for this environment.
- Deploy the InsightHub application workloads into `insighthub-dev`. The
  managed RDS and ElastiCache services are verified separately from pod
  readiness.
- Kubernetes RBAC, network policies, Helm release details, ingress controller,
  TLS certificate source, hostname, worker capacity, and autoscaling are **TBD**
  unless later specifications make them concrete.

## RDS

- Use Amazon RDS PostgreSQL major version 16 in a private DB subnet group.
- Enable storage encryption at rest. KMS key selection/ownership is **TBD**;
  the implementation must use the approved KMS approach and not embed key IDs.
- Set the instance/cluster to non-public and ensure its security group has no
  `0.0.0.0/0` ingress.
- Verify that the selected PostgreSQL 16 engine/version supports `pgvector`,
  then enable `vector` with a database role authorized to create the extension.
- Database engine patch version, instance class, storage, Multi-AZ, database
  name, parameter groups, backup retention, maintenance window, deletion
  protection, final-snapshot behavior, and credentials are **TBD** inputs.
- Database credentials must be generated/stored and delivered without appearing
  in Terraform source, plans shared outside approved controls, application
  images, or Git.

## Redis

- Use Amazon ElastiCache for Redis major version 7, with its subnet group made
  from private subnets only.
- Do not expose Redis publicly and do not allow inbound `0.0.0.0/0` rules.
- Restrict Redis ingress to the specific approved EKS/application workload
  security groups on the required Redis port.
- Node type, replication/multi-AZ settings, shard/replica count, encryption in
  transit/at rest settings, auth token handling, maintenance window, backup
  policy, and parameter group are **TBD** inputs. Any selected encryption or
  auth setting must remain compatible with the InsightHub Redis/ARQ clients.

## IAM / IRSA

- Enable or use the EKS cluster OIDC issuer and create an IAM OIDC provider only
  when one is not already managed by the approved platform boundary.
- Create one least-privilege IAM role for ServiceAccount `insighthub` in
  namespace `insighthub-dev`; its trust policy must bind both the issuer
  audience (`sts.amazonaws.com`) and exact Kubernetes subject
  `system:serviceaccount:insighthub-dev:insighthub`.
- Attach only permissions justified by the InsightHub workload. Permission
  actions/resources are **TBD** and must be reviewed before implementation; no
  wildcard administrative policy is permitted.
- Use workload identity via projected IRSA tokens. Do not create IAM Users for
  application access and do not create/store long-lived access keys.
- CI/CD AWS access must use GitHub Actions OIDC with a least-privilege role and
  trust conditions restricted to the approved repository, ref and/or GitHub
  environment. Exact repository and environment are **TBD**.

## Backend

- Use a pre-existing, separately bootstrapped S3 bucket for Terraform state.
  Bucket name, state key prefix, and region are configurable **TBD** values;
  this module must not depend on creating its own backend during initialization.
- Configure the S3 backend with encryption enabled and
  `use_lockfile = true`. Do not introduce a new DynamoDB lock table.
- Backend bucket policy, encryption implementation/KMS key, versioning,
  lifecycle/retention, logging, and access roles are **TBD** but must be
  documented and approved before backend bootstrap.
- State paths must separate environments. Workspace naming and exact key layout
  are **TBD**; a development state must not share a key with staging or
  production.

## Tags

The following tags are mandatory on every AWS resource type that supports
tags, using provider-level defaults plus explicit propagation where needed:

| Tag | Required value |
| --- | --- |
| `project` | Configurable InsightHub project identifier |
| `environment` | `dev` for this specification's environment |
| `owner` | Configurable accountable owner; no default |
| `cost_center` | Configurable cost center; no default |
| `managed_by` | `terraform` |

Lab operational tags such as `Class`, `LabId`, and `ExpiresAt` may be added when
required by the cost/cleanup process; they do not replace the five mandatory
tags.

## Inputs / Outputs

### Inputs

| Input | Status / purpose |
| --- | --- |
| `aws_region` | Configurable; default **TBD** |
| `environment` | Required; this design uses `dev` |
| `project`, `owner`, `cost_center` | Required tag values; no sensitive defaults |
| `vpc_id` or VPC CIDR/subnet configuration | Required deployment topology; **TBD** |
| Private subnet IDs / AZ selection | Required for EKS, RDS, and Redis; **TBD** |
| EKS cluster name/version and compute topology | **TBD** |
| RDS capacity, storage, backups, and maintenance settings | **TBD** |
| Redis capacity, replication, encryption, and maintenance settings | **TBD** |
| Backend bucket, key prefix, and backend region | Required bootstrap configuration; **TBD** |
| Approved KMS, secret, CI OIDC, and workload IAM policy references | **TBD**; never literal secrets or account IDs |

### Outputs

Future Terraform outputs may expose non-secret connection metadata needed by
deployment automation:

- EKS cluster name, endpoint, and OIDC issuer/provider reference.
- Namespace name: `insighthub-dev`.
- IRSA role ARN and ServiceAccount name: `insighthub`.
- RDS endpoint/address, port, database identifier, and security-group ID.
- Redis primary endpoint/address, port, replication-group identifier, and
  security-group ID.
- Private subnet IDs and security-group IDs used by the deployment.

Outputs must not expose passwords, auth tokens, private keys, full secret
values, or Terraform state contents.

## Acceptance Criteria

- [ ] `infra/SPEC.md` is the implementation reference and no Terraform code is
      introduced as part of this specification task.
- [ ] A future implementation pins Terraform to `>= 1.7.0, < 2.0.0` and AWS
      provider to `~> 5.70`.
- [ ] The future S3 backend enables encryption and `use_lockfile = true`, with
      state kept outside Git and no new DynamoDB lock table.
- [ ] The EKS namespace `insighthub-dev` exists, and ServiceAccount
      `insighthub` is bound to the intended IRSA role.
- [ ] The IRSA trust policy restricts its subject to
      `system:serviceaccount:insighthub-dev:insighthub` and uses short-lived
      tokens; no IAM User or long-lived access key is used for workload access.
- [ ] RDS runs PostgreSQL 16 with verified pgvector support, storage encryption,
      private subnet placement, and `publicly_accessible = false`.
- [ ] ElastiCache runs Redis 7 in private subnets with no public endpoint.
- [ ] RDS and Redis security groups contain no `0.0.0.0/0` inbound rule and
      accept traffic only from approved workload security groups.
- [ ] Every taggable resource has `project`, `environment`, `owner`,
      `cost_center`, and `managed_by=terraform`.
- [ ] No credentials, AWS Account ID, or secret value is hard-coded in source,
      inputs, outputs, tags, or documentation.
- [ ] Region, network topology, sizing, backup/retention, KMS, secret delivery,
      and unresolved values are explicitly selected from the documented **TBD**
      items before any implementation or AWS lab run.
