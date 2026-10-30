# Pipeline design notes

## Stages and quality gates

| Stage | Command | Artifact | Gate |
|---|---|---|---|
| Lint | `ruff check src tests` | — | zero findings |
| Unit tests | `pytest` | `reports/junit.xml`, `coverage.xml` | all tests pass |
| Evaluation | `python -m adaptedge.evaluate` | `reports/metrics.json` | deterministic, `p99_improvement_pct > 0` in tests |
| Build | `nerdctl build` | `adaptedge:<build>` | image exists |
| Smoke | `scripts/smoke_test.sh` | container log | `/health` returns `status=ok` |
| Publish | `nerdctl push` | GHCR tag | only when `PUSH_IMAGE=true` |
| Deploy | `deploy/deploy.sh` | rollout status | k8s reachable or local target healthy |

## Why nerdctl instead of Docker-in-Docker

The Jenkins controller runs as the unprivileged host user. Rootless containerd
plus `nerdctl` gives an OCI-compatible build/run path without a privileged
daemon and without exposing a Docker socket. The pipeline therefore uses the
same CLI shape as Docker (`build`, `run`, `tag`, `push`) while the daemon runs
inside the user session.

## Failure handling

- The smoke test cleans up its container in a `trap`, even on failure.
- The Jenkins `post` block removes the CI container and archives reports.
- The deployment script prefers Kubernetes but falls back to a local container
  so the CD stage is still exercised on a laptop.
- Builds are not concurrent (`disableConcurrentBuilds`) to protect the fixed
  smoke-test port and the rootless containerd namespace.
