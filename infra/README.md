# Day 3: Terraform IaC

Terraform hiện quản lý namespace `insighthub` trên Kubernetes cluster có sẵn.

```bash
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan
```

Đặt `kubeconfig` và `kube_context` qua `terraform.tfvars` hoặc biến môi trường
`TF_VAR_kubeconfig` và `TF_VAR_kube_context`. Không commit file chứa credentials.
