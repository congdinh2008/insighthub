# K8s RBAC — ServiceAccount mcp-readonly

ServiceAccount + ClusterRole read-only riêng cho MCP server.
Không dùng kubeconfig cluster-admin với MCP — blast radius quá lớn.

## Apply RBAC

```bash
# Tạo namespace trước nếu chưa có
kubectl create namespace insighthub --dry-run=client -o yaml | kubectl apply -f -

# Apply RBAC
kubectl apply -f infra/k8s/mcp-readonly/serviceaccount.yaml
kubectl apply -f infra/k8s/mcp-readonly/clusterrole.yaml
kubectl apply -f infra/k8s/mcp-readonly/clusterrolebinding.yaml
```

## Tạo kubeconfig read-only

```bash
# 1. Lấy token của ServiceAccount
SECRET_NAME=$(kubectl get sa mcp-readonly -n insighthub -o jsonpath='{.secrets[0].name}' 2>/dev/null)
if [ -z "$SECRET_NAME" ]; then
  # K8s 1.24+ — tạo token thủ công
  TOKEN=$(kubectl create token mcp-readonly -n insighthub --duration=8760h)
else
  TOKEN=$(kubectl get secret "$SECRET_NAME" -n insighthub -o jsonpath='{.data.token}' | base64 -d)
fi

# 2. Lấy CA cert và server URL
CLUSTER_SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
kubectl config view --minify --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' \
  | base64 -d > /tmp/mcp-ca.crt

# 3. Build kubeconfig
kubectl config set-cluster insighthub-mcp \
  --server="$CLUSTER_SERVER" \
  --certificate-authority=/tmp/mcp-ca.crt \
  --embed-certs=true \
  --kubeconfig=~/.kube/mcp-viewer.kubeconfig

kubectl config set-credentials mcp-readonly \
  --token="$TOKEN" \
  --kubeconfig=~/.kube/mcp-viewer.kubeconfig

kubectl config set-context insighthub-mcp \
  --cluster=insighthub-mcp \
  --user=mcp-readonly \
  --namespace=insighthub \
  --kubeconfig=~/.kube/mcp-viewer.kubeconfig

kubectl config use-context insighthub-mcp \
  --kubeconfig=~/.kube/mcp-viewer.kubeconfig
```

## Verify least-privilege

```bash
# Phải được: đọc pod
kubectl --kubeconfig ~/.kube/mcp-viewer.kubeconfig get pods -n insighthub

# Phải bị từ chối: xóa pod
kubectl --kubeconfig ~/.kube/mcp-viewer.kubeconfig delete pod -n insighthub --all
# → Error from server (Forbidden)

# Verify với auth can-i
kubectl auth can-i get pods   --as=system:serviceaccount:insighthub:mcp-readonly  # yes ✓
kubectl auth can-i delete pods --as=system:serviceaccount:insighthub:mcp-readonly  # no ✓
kubectl auth can-i create deployments --as=system:serviceaccount:insighthub:mcp-readonly  # no ✓
```

## Cập nhật .mcp.json

Sau khi có file `~/.kube/mcp-viewer.kubeconfig`, sửa trong `.mcp.json`:

```json
"kubernetes": {
  "env": {
    "KUBECONFIG": "/absolute/path/to/.kube/mcp-viewer.kubeconfig"
  }
}
```

Dùng đường dẫn tuyệt đối — `~` không expand trong một số shell khi chạy qua Node.js.
