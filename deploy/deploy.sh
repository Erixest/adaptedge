#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:-adaptedge:latest}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="${NAMESPACE:-adaptedge}"
KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"
export KUBECONFIG

cd "${ROOT}"

if kubectl version --request-timeout=3s >/dev/null 2>&1; then
    echo "Kubernetes API reachable: applying manifests"
    kubectl apply -k deploy/k8s
    kubectl -n "${NAMESPACE}" set image deployment/adaptedge adaptedge="${IMAGE}"
    kubectl -n "${NAMESPACE}" rollout status deployment/adaptedge --timeout=120s
    kubectl -n "${NAMESPACE}" get pods,svc
else
    echo "Kubernetes API not reachable: deploying to the local test target"
    nerdctl rm -f adaptedge-test >/dev/null 2>&1 || true
    nerdctl run -d --name adaptedge-test -p 127.0.0.1:18081:8000 "${IMAGE}"
    python3 "${ROOT}/scripts/healthcheck.py" 18081
    echo "CD target: http://127.0.0.1:18081/health"
fi
