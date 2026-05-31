# Day 3 AI Prompts — IaC & CI/CD Pipeline

> Tài liệu chứng minh AI-augmented workflow.
> Pattern chủ đạo: Spec-driven → AI generate → Human review → Policy gate (3-Layer Defense).

---

## Prompt 1 — Phân tích kiến trúc hiện tại và thiết kế IaC

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-24 09:00

**Prompt**:
```
Đọc docker-compose.yml để hiểu 5 services của InsightHub v1.
Phân tích và thiết kế IaC Terraform cho AWS deployment. CHƯA viết code.

Yêu cầu phân tích:
1. Mỗi service hiện tại → AWS managed equivalent là gì?
2. Networking topology: public/private/db subnets — tại sao cần 3 tier?
3. Tại sao IRSA thay vì IAM user cho pod credentials?
4. pgvector trên RDS cần gì khác so với vanilla PostgreSQL?
5. Module nào nên dùng từ terraform-aws-modules (không tự viết VPC)?
```

**Agent output (tóm tắt)**:
- postgres → RDS PostgreSQL 16 + custom parameter group `shared_preload_libraries=vector`
- redis → ElastiCache Redis 7 (không thể dùng managed Redis nếu muốn AUTH token)
- api/worker/web → EKS managed node group (không Fargate vì shared memory với pgvector)
- 3-tier subnets: public (ALB), private (EKS nodes), db (RDS/Redis) — defense in depth
- IRSA: pod không cần static key, token rotate tự động, least-privilege per-SA
- Module đề xuất: `terraform-aws-modules/{vpc,eks,rds}` — đã battle-tested, pass checkov mặc định

**Lý do prompt hoạt động**:
- "CHƯA viết code" ngăn agent bắt đầu code khi kiến trúc chưa được review
- Numbered questions tạo structured output dễ review từng điểm

**Điều chỉnh sau review**:
- ✅ IRSA analysis đúng — approve
- ✅ terraform-aws-modules approach — approve
- ❌ Agent đề xuất Fargate cho workers — reject (pgvector cần EBS, Fargate không mount EBS)
- Thêm yêu cầu: RDS Multi-AZ tắt ở dev (cost), bật ở prod (variable)

---

## Prompt 2 — Sinh Terraform module (Constraint-first)

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-24 09:30

**Prompt**:
```
Sinh Terraform module cho InsightHub AWS deployment.

Constraints (PHẢI tuân thủ):
1. Dùng terraform-aws-modules/vpc/aws ~>5.16 — KHÔNG tự viết VPC
2. Dùng terraform-aws-modules/eks/aws ~>20.31 — KHÔNG tự viết EKS
3. Dùng terraform-aws-modules/rds/aws ~>6.10 — KHÔNG tự viết RDS
4. RDS: storage_encrypted=true, publicly_accessible=false, kms_key_id=custom
5. ElastiCache: at_rest_encryption_enabled=true, transit_encryption_enabled=true, auth_token
6. Tất cả resources: tags = {project, environment, owner, cost_center, managed_by}
7. Backend S3 dùng partial config (không hardcode bucket name — dùng -backend-config)
8. IRSA: submodule riêng, trust policy chỉ cho specific SA + namespace
9. Submodule networking: SG chỉ allow inbound từ EKS node SG (không CIDR)
10. `terraform validate` và `terraform fmt -check` phải pass

Cấu trúc file: providers.tf, backend.tf, variables.tf, locals.tf, main.tf, outputs.tf
Submodule: modules/networking/, modules/irsa/
```

**Plan agent đưa ra (đã review)**:
1. providers.tf — required_version ≥1.9.0, pin AWS/k8s/helm/random providers
2. backend.tf — partial config + backend-dev.hcl example
3. variables.tf — aws_region, environment (validation), node sizes, db vars
4. locals.tf — name_prefix, common_tags, CIDR calculation
5. main.tf — VPC → EKS → namespace → DB param group → random passwords → RDS → ElastiCache → KMS → SGs → IRSA → CloudWatch
6. outputs.tf — endpoints, role ARNs, namespace
7. modules/networking/main.tf — 2 SGs với required_version + required_providers
8. modules/irsa/main.tf — OIDC trust policy, data.aws_caller_identity

**Review trước khi approve**:
- ✅ Partial backend config đúng (không thể dùng var trong backend block)
- ❌ Agent dùng `final_snapshot_identifier` trong rds module — không phải argument hợp lệ → remove
- ❌ Agent không thêm `required_version` vào submodules → add (tflint bắt)
- ❌ Agent giữ `vpc_cidr` variable trong networking module nhưng không dùng → remove (tflint bắt)
- ✅ KMS policy explicit — approve (checkov CKV2_AWS_64 yêu cầu)
- ✅ Redis auth_token — approve (checkov CKV_AWS_31)

**Lý do prompt hoạt động**:
- 10 constraints numbered → agent không "sáng tạo" ngoài scope
- Explicit file list → không thêm file không cần thiết
- "terraform validate phải pass" làm agent self-check trước khi trả output

---

## Prompt 3 — GitHub Actions CI/CD Pipeline (Multi-stage)

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-24 11:00

**Prompt**:
```
Sinh .github/workflows/iac.yml với các stage sau (THEO THỨ TỰ):

Stage 1: fmt — terraform fmt -check -recursive
Stage 2: lint — tflint --recursive (needs: fmt)
Stage 3: scan — checkov bridgecrewio/checkov-action@v12, SARIF upload (needs: fmt)
Stage 4: policy-check — conftest test với Rego policies (needs: lint, scan)
Stage 5: plan — terraform plan -detailed-exitcode, post summary to PR (needs: policy-check)
Stage 6: cost-estimate — infracost comment on PR (needs: plan, chỉ trên PR)
Stage 7: apply — manual approval, chỉ khi input apply=true VÀ branch=main (needs: plan)

Constraints:
1. AWS auth: OIDC (aws-actions/configure-aws-credentials@v4) — KHÔNG long-lived keys
2. Environment variable: TF_VERSION, TFLINT_VERSION, CHECKOV_VERSION, AWS_REGION
3. permissions: id-token: write (OIDC), pull-requests: write (PR comment)
4. apply stage dùng GitHub Environments (manual approval gate)
5. Upload plan artifact (retention 1 day) để apply reuse — KHÔNG re-plan
6. tflint: cache ~/.tflint.d/plugins theo version
7. workflow_dispatch: input environment (dev/staging/prod) + apply (true/false)
```

**Agent output**: `.github/workflows/iac.yml` đúng yêu cầu 7 stages.

**Review trước khi approve**:
- ✅ OIDC auth đúng — không có AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY
- ✅ artifact upload/download giữa plan và apply jobs
- ✅ `continue-on-error: true` trên plan step để capture exit code
- ❌ Agent dùng `needs.plan.outputs.plan_exit_code == 2` — phải là string `'2'` (YAML) → fix
- ✅ cost-estimate `if: github.event_name == 'pull_request'` đúng
- Thêm: post plan diff vào PR comment bằng `actions/github-script@v7`

**Lý do prompt hoạt động**:
- Stage names explicit và ordered → pipeline không thể skip security stages
- "KHÔNG long-lived keys" là hard constraint — agent không thể "default" sang key auth
- "upload artifact → reuse" tránh race condition apply một plan khác với plan đã review

---

## Prompt 4 — Conftest Rego Policies

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-24 12:00

**Prompt**:
```
Viết 3 Conftest Rego policies cho Terraform plan JSON:

1. infra/policies/required_tags.rego
   - Rule: tất cả taggable AWS resources phải có: project, environment, owner, cost_center, managed_by
   - Chỉ check resources với actions create/update (không check destroy)
   - List explicit: aws_instance, aws_db_instance, aws_elasticache_replication_group, ...

2. infra/policies/encryption.rego
   - Rule: RDS phải storage_encrypted=true
   - Rule: ElastiCache phải at_rest_encryption_enabled=true VÀ transit_encryption_enabled=true
   - Rule: KMS key phải enable_key_rotation=true

3. infra/policies/no_public_resources.rego
   - Rule: RDS không publicly_accessible
   - Rule: SG không allow 0.0.0.0/0 trên ports 5432, 6379, 3306 (dangerous DB ports)

Dùng: package terraform.<name>, import rego.v1, deny set, violations set
```

**Agent output**: 3 file Rego đúng cú pháp.

**Điều chỉnh sau review**:
- ✅ `import rego.v1` modern syntax
- ✅ `deny contains msg if` pattern (không dùng legacy `deny[msg]`)
- ✅ `input.resource_changes[_].change.actions[_] in {"create", "update"}` chính xác
- Sửa: `no_public_resources.rego` dùng `numbers.range()` — Rego builtin đúng

**Lý do prompt hoạt động**:
- Liệt kê explicit từng rule và resource type → agent không tự suy luận resource list
- "Dùng: deny set, violations set" → định hướng pattern để test được với conftest

---

## Tổng kết Day 3

**3-Layer Defense thực tế**:
| Layer | Tool | Kết quả |
|---|---|---|
| AI Generate | Claude Code | Terraform + Pipeline + Rego trong <2h |
| Human Review | Manual review 4 prompts | 8 correction, 3 addition |
| Policy Gate | tflint + checkov + conftest | 0 warnings, 0 HIGH, all pass |

**Metrics**:
- Thời gian viết Terraform thủ công (ước): ~8 giờ
- Thời gian với AI (actual): ~2 giờ (bao gồm review + fix)
- Số lần AI tự sửa sau human feedback: 8
- checkov: 68 PASS / 0 FAIL (sau skip 5 documented findings)
- tflint: 0 warnings (sau fix submodule terraform blocks)
- verify-day-3.sh: 12/12 PASS

**Key learnings**:
1. Constraint-first prompt ngăn agent thêm feature không cần (Fargate, rotation Lambda)
2. "CHƯA viết code" tách bước analysis khỏi implementation — review dễ hơn
3. Backend partial config là pattern bắt buộc — không có cách nào dùng var trong backend block
4. tflint bắt lỗi submodule thiếu required_version — cần thêm vào mọi submodule
5. IRSA trust policy cần double condition: `sub` (SA + namespace) VÀ `aud` (sts.amazonaws.com)
