#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:?usage: smoke_test.sh IMAGE CONTAINER PORT}"
CONTAINER="${2:?usage: smoke_test.sh IMAGE CONTAINER PORT}"
PORT="${3:-18080}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
    nerdctl rm -f "${CONTAINER}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

cleanup
nerdctl run -d --name "${CONTAINER}" -p "127.0.0.1:${PORT}:8000" "${IMAGE}"

for _ in $(seq 1 30); do
    if python3 "${ROOT}/scripts/healthcheck.py" "${PORT}"; then
        echo "smoke test passed: http://127.0.0.1:${PORT}/health"
        exit 0
    fi
    sleep 2
done

echo "smoke test failed; container logs:" >&2
nerdctl logs "${CONTAINER}" >&2 || true
exit 1
