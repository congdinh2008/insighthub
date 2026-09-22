# EKS platform state

This state starts only after the AWS infrastructure state exposes a reachable EKS cluster. It creates namespace `insighthub-<environment>`, the IRSA-bound `insighthub` service account and its minimal namespace RBAC.

The Helm release consumes these resources with `platform.create=false`; it does not create a second namespace or service account. Local values set `platform.create=true` because Terraform does not own the kind lab.
