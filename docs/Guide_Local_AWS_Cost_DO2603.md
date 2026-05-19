# Guide bắt buộc: local first, chi phí và xóa AWS sau lab
DO2603, 08/09/2026. Đây là yêu cầu vận hành của lớp theo chỉ đạo anh Công.

## Quy tắc áp dụng mọi ngày
1. Chạy đúng và đo/tối ưu local trước: fixture -> real model phù hợp -> deployment local.
2. Chỉ dùng AWS khi cần kiểm chứng IAM/OIDC, managed service hoặc đặc tính cloud mà local không chứng minh được. Ghi mục tiêu còn thiếu; không tạo cloud chỉ để có ảnh dashboard.
3. Tạo theo từng lượt thực hành có thời điểm kết thúc. **Xóa ngay sau khi làm xong, không để chạy liên tục, qua đêm hoặc giữa các buổi.** Provision lại bằng IaC khi cần.
4. Người tạo chịu trách nhiệm inventory, cleanup và evidence. Teardown lỗi là việc đang mở phải xử lý ngay; không chuyển thành “sẽ xóa cuối khóa”.
5. Starter và bộ kiểm thử không tự provision/xóa AWS. Local-first không cắt task Terraform/GitHub/Helm/EKS/RDS/ElastiCache/OIDC, Slack live, guardrails và gateway của specification.

## Chọn giải pháp vừa đủ
| Nhu cầu | Mặc định local | Chỉ cân nhắc AWS khi |
|---|---|---|
| RAG/API/worker | Compose + PostgreSQL, Redis/worker bắt buộc từ Day 1 | Cần đo dịch vụ AWS hoặc truy cập có kiểm soát |
| Container deploy | kind/k3d với image local hoặc Compose | Cần thực hành ECS/EKS cụ thể; giữ mục tiêu EKS của Day 3, kiểm chứng cloud theo lượt |
| IAM và pipeline | policy/plan/test local trước, GitHub Actions bắt buộc Day 3 | Cần chứng minh trust OIDC/role thật |
| Metrics/RCA | Prometheus + Grafana, đủ 9 panels và 3 RCA Day 4 | Cần CloudWatch/managed telemetry thật |
| ChatOps/MCP | MCP local; Slack thật kết nối bot local, doubles chỉ cho unit test | Cần endpoint hoặc identity cloud cụ thể |
| Evals/cost | cùng workload; đo latency/RAM/token | Real API có chất lượng cần so sánh và budget được giới hạn |

Đề xuất triển khai thực tế phải so độ phức tạp, blast radius, vận hành và tổng chi phí. Một app nhỏ chưa cần EKS+RDS+ElastiCache. Không đánh đổi bảo mật bằng mở DB ra internet để tiết kiệm tiền.

## Trước khi tạo AWS
- Xác nhận đúng account sandbox, region, profile, workspace/state; không dùng tài khoản production hay quyền administrator mặc định.
- Lập `lab-manifest.json` chứa owner, class=DO2603, lab_id duy nhất, account_id, regions, started_at, expires_at, budget_usd, resource IDs/ARNs, IaC workspace, dependencies và người kiểm tra.
- Tag tài nguyên hỗ trợ tag: Class, LabId, Owner, ExpiresAt. Lưu ID trực tiếp cho tài nguyên thiếu tag; tag không tự xóa và không bảo đảm inventory đầy đủ.
- Dự toán theo **thời gian tồn tại thực tế**, gồm provision/idle/test/destroy: compute/control plane + DB/cache + storage/snapshot + network/NAT/public IPv4 + requests/model/telemetry. Lấy giá hiện hành theo region và account, lưu URL/ngày; không giả định free tier.
- Đặt timer kết thúc trước buổi nghỉ, dành thời gian teardown, đặt cảnh báo ngân sách như lớp bổ sung. AWS Budgets có độ trễ, không phải chặn phí tức thời. [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- CI nếu dùng AWS: OIDC, trust bound repo/ref/environment và role tối thiểu; không lưu access key dài hạn. [GitHub OIDC](https://docs.github.com/en/actions/concepts/security/openid-connect)

## Quy trình tạo và teardown bằng IaC
Các lệnh dưới đây là mẫu để học viên thực hiện trong **root module lab đã kiểm tra**; starter không chứa module AWS hoàn chỉnh. Dùng state riêng, bảo vệ plan vì có thể chứa dữ liệu nhạy cảm.

```bash
# Read-only: kiểm tra identity và đúng workspace trước cả create và delete.
aws sts get-caller-identity --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION"
terraform -chdir=infra workspace show
terraform -chdir=infra state list

# Sau local tests, tạo plan; review resource IDs, chi phí và phạm vi.
terraform -chdir=infra plan -out=lab.tfplan
terraform -chdir=infra show lab.tfplan
# Chỉ áp dụng plan đã review của đúng lượt lab.
terraform -chdir=infra apply lab.tfplan

# NGAY sau thực hành: review destroy plan, rồi áp dụng chính plan đó.
terraform -chdir=infra plan -destroy -out=teardown.tfplan
terraform -chdir=infra show teardown.tfplan
terraform -chdir=infra apply teardown.tfplan
terraform -chdir=infra state list
```

Khai báo provider AWS sử dụng cùng profile/region với kiểm tra identity; các biến LAB_* không tự cấu hình Terraform. Không chạy lệnh apply khi manifest và plan khác account/workspace. Không dùng destroy toàn account hoặc script xóa theo tên mơ hồ.

Nếu có Kubernetes controller tạo AWS resource, xử lý resource con **trước** khi xóa cluster/controller; chờ kết quả thật. Với EKS, xóa Ingress/Service tạo load balancer, node groups/Fargate profiles/capabilities theo topology; managed Prometheus scraper có vòng đời riêng. [AWS EKS deletion](https://docs.aws.amazon.com/eks/latest/userguide/delete-cluster.html)

Không bỏ qua lỗi dependency bằng xóa state hay force-remove finalizer. Xác định tài nguyên và chủ sở hữu, khắc phục rồi chạy lại cleanup đúng phạm vi. State rỗng chưa chứng minh AWS không còn orphan.

## Kiểm tra tài nguyên còn sót
Dùng service API/console read-only trong **mọi region đã dùng**, đối chiếu từng ID với manifest. Resource Groups Tagging API hỗ trợ inventory nhưng không bao phủ mọi tài nguyên.

| Nhóm | Cần đối chiếu sau teardown |
|---|---|
| Compute/container | EKS cluster, node group/Fargate/capabilities; ECS service/task; EC2/ASG; launch resources thuộc lab |
| Database/cache | RDS instance/cluster/replica; retained backup/manual/final snapshot; ElastiCache cluster/serverless/snapshot |
| Network | ALB/NLB/target group, NAT gateway, EIP/public IPv4, VPC endpoints; ENI/security group/VPC lab còn phụ thuộc |
| Storage | EBS volume/snapshot, PVC/PV với reclaim policy; S3 objects/versions/delete markers/multipart thuộc lab |
| Artifact/telemetry | ECR image/repository, CloudWatch logs, managed Prometheus workspace/scraper nếu tạo riêng |
| Quyền/công cụ | Role/policy/token/tunnel/automation riêng của lab; kiểm tra scheduler không tạo lại tài nguyên |

RDS manual/final snapshots và retained backups có thể tiếp tục bị tính phí sau khi xóa instance. Dataset lab có thể tái tạo, không tạo snapshot dư thừa; nếu cần giữ dữ liệu, ghi owner/thời hạn và chi phí được chấp thuận. [RDS deletion](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_DeleteInstance.html)

NAT/public EIP có vòng đời cần theo dõi riêng theo cấu hình network. [NAT gateway](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html) Volume EBS còn tồn tại cũng cần xóa sau khi kiểm tra dữ liệu/owner, không chỉ terminate compute. [EBS deletion](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-deleting-volume.html)

## Evidence kết thúc lượt lab
Nộp manifest đã ẩn thông tin nhạy cảm, inventory trước/sau, timestamp kết thúc, lệnh và exit code, trạng thái cuối từng resource, elapsed hours, estimated cost và actual billed cost khi có. Không khai 0 USD chỉ vì billing chưa cập nhật. Nếu không dùng AWS, ghi `aws_used=false`, môi trường local và lệnh dừng; không cần tạo AWS để có bằng chứng teardown.

Reviewer chỉ đánh dấu AWS lab hoàn tất khi tài nguyên lab đã xóa hoặc trường hợp bảo lưu dữ liệu có owner/quyết định rõ ràng. Đối chiếu billing sau độ trễ để phát hiện khoản bất thường, nhưng không chờ billing mới xóa tài nguyên.

## Áp dụng xuyên suốt running project
Day 3 giữ module/cloud kiến thức và plan/deployment cần chứng minh; chưa chạy AWS thì ghi chưa xác minh AWS, không coi local PASS là hoàn thành AWS. Day 4 tiếp tục source/manifests và baseline local; Day 6 vẫn triển khai LiteLLM/guardrails/Promptfoo, AWS Budgets áp dụng khi dùng AWS. Không giữ dịch vụ tính phí giữa các buổi để bảo toàn tiến độ.
