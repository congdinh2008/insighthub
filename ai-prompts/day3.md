# Day 03 - Bộ prompt thực hiện solution

Sáu prompt dưới đây dành cho học viên thực hiện AI-Powered IaC & Pipeline từ solution Day 01-02. Đây là prompt pack đề xuất, không phải log cuộc trao đổi với giảng viên và không phải bằng chứng các prompt đã được chạy.

## D3-P01 - Khảo sát kiến trúc và requirements

```text
RÀNG BUỘC
Chỉ phân tích, chưa sửa source hoặc tạo cloud resource. Đọc AGENTS.md,
specification mục 0/4/7, Compose, Dockerfiles, schema, worker và CI hiện có.
Giữ nguyên API, queue, retry, embedding identity và năm thành phần Day 01.

NHIỆM VỤ
Lập architecture map hiện tại và gap matrix cho MH1-MH14 cùng Should-have
Day 03. Phân biệt local Kubernetes với AWS managed services, source artifact
với runtime evidence và fixture model với provider thật.

ĐẦU RA VÀ KIỂM CHỨNG
Nêu file nguồn cho từng kết luận, đầu vào AWS/GitHub/domain còn thiếu,
phạm vi file được phép thay đổi và các hạng mục thuộc Day 04-06 phải loại.
Không ghi một mục là đã đạt nếu mới thấy cấu hình dự kiến.
```

## D3-P02 - SPEC, planning và design review

```text
RÀNG BUỘC
Chưa triển khai. Chỉ dùng tài liệu chính chủ để kiểm tra Terraform, AWS,
GitHub Actions, Helm và các tool được pin. Thiết kế cho lab ngắn hạn,
local-first, không duy trì cloud qua đêm.

NHIỆM VỤ
Viết SPEC và plan: topology, module/state ownership, OIDC trust,
IRSA/secrets, policy gates, cost, HTTPS, evidence, teardown và commit strategy.
Thiết kế tách plan/apply role, core/platform state và local/AWS values.

ĐẦU RA VÀ KIỂM CHỨNG
Map từng requirement tới artifact, lệnh verify và expected result.
Nêu rủi ro IAM/network/state/cost, quyết định managed service và điều kiện
dừng trước apply. Tự review plan rồi chờ human review trước implementation.
```

## D3-P03 - Terraform và policy gates

```text
RÀNG BUỘC
Chỉ triển khai SPEC đã duyệt. Không dùng credential hardcode, wildcard trust,
public DB/cache, DynamoDB lock mới hoặc blanket skip/soft-fail.
Không apply AWS ở bước này.

NHIỆM VỤ
Tạo bootstrap, core modules, platform root, example variables, standard tags,
S3 native lockfile, OIDC/IRSA, Secrets Manager, Rego và positive/negative tests.
Pin provider/tool versions và checksum.

ĐẦU RA VÀ KIỂM CHỨNG
Chạy fmt, init backend-disabled, validate từng root, TFLint, Checkov và
Conftest. Báo rõ exceptions có lý do, quyền còn cần review, cost drivers
và mọi phần chỉ mới được static validation.
```

## D3-P04 - Helm và local Kubernetes verification

```text
RÀNG BUỘC
Giữ contract Day 01. Local dùng PostgreSQL/Redis trong cluster; AWS values
phải dùng RDS/ElastiCache và không tạo hai StatefulSet này. Không thêm
dashboard, alert, ChatOps hoặc security gateway của day sau.

NHIỆM VỤ
Tạo Helm chart cho web/api/ingestion-worker, probes, resources, security
context, HPA, Ingress, Secrets Store CSI và migration Job. Dựng kind riêng,
chạy five-component smoke rồi test UI bằng Microsoft Edge.

ĐẦU RA VÀ KIỂM CHỨNG
Helm lint/render local/dev/staging; pods Ready; health 200; upload 202;
đúng document ID Ready <=30 giây; chat có answer/citations; console không lỗi.
Ghi rõ fixture/provider mode và teardown đúng cluster lab.
```

## D3-P05 - GitHub Actions và plan review

```text
RÀNG BUỘC
Không đưa AWS credential, state hoặc raw plan vào artifact công khai.
PR từ fork không được nhận cloud identity. Actions và tools phải pin.
Apply chỉ dùng saved plan đã qua review và checksum.

NHIỆM VỤ
Tạo workflow fmt/lint/security/policy/plan/cost/apply, application tests,
image build, OIDC, Infracost PR comment, source binding và protected Environment.
Khi có input cloud, tạo plan thật và dùng AI giải thích bản sanitized plan.

ĐẦU RA VÀ KIỂM CHỨNG
Workflow syntax/test contracts PASS. PR comment nêu create/change/destroy,
IAM/network/data risk, chi phí, unknown values và kết luận human review.
Chưa approve/apply nếu có unexpected destroy, vượt budget hoặc thiếu input.
```

## D3-P06 - Cloud acceptance, cleanup và bàn giao

```text
RÀNG BUỘC
Chỉ chạy sau protected-environment approval và trên AWS sandbox đã xác minh.
Dùng domain/certificate có sẵn. Không dùng personal admin mặc định.
Không ghi local PASS thành cloud PASS.

NHIỆM VỤ
Apply đúng saved plan, kiểm tra namespace/IRSA/RDS/Redis/tags, deploy Helm,
chạy HTTPS smoke và Microsoft Edge E2E. Thu sanitized evidence, chạy fresh plan,
sau đó teardown theo ownership và kiểm kê tài nguyên tính phí.

ĐẦU RA VÀ KIỂM CHỨNG
Cung cấp PR/run/live URL, source and image digest, cost assumptions, request
results, permission allow/deny, tag inventory và cleanup inventory.
Hoàn thiện runbook, requirement matrix, self-check và PR description;
mọi mục chưa chạy phải giữ trạng thái chưa xác minh.
```

Khi nộp bài, học viên ghi metadata và kết quả của tối thiểu ba prompt thực sự đã dùng. Không sao chép yêu cầu của giảng viên thành prompt log và không bịa model, thời gian, tool output hoặc quyết định review.
