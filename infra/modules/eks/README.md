# EKS module

Creates a private-node EKS cluster with a restricted public API endpoint, private endpoint access, encrypted Kubernetes secrets, control-plane logs and one bounded managed node group. The module exposes the OIDC provider for namespace-scoped IRSA roles.

The node role keeps the CNI policy for this short-lived lab. A production rollout should move CNI permissions to its own service account and test the migration before removing the node attachment.
