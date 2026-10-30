# AdaptEdge — CI/CD for an adaptive WebRTC/QUIC transport experiment

[![ci](https://github.com/Erixest/adaptedge/actions/workflows/ci.yml/badge.svg)](https://github.com/Erixest/adaptedge/actions/workflows/ci.yml)

AdaptEdge is the sample research project for **Assignment 5: DevOps and CI/CD**.
It packages a small, deterministic piece of the author's dissertation work — an
adaptive transport selector for a WebRTC/QUIC edge segment with LoRa + ESP32
nodes — as a reproducible Python service with a full container and pipeline
workflow.

The scientific claim under test is deliberately modest: a per-session selector
that observes RTT, loss, jitter and handover state lowers **mean** latency
against the best *pinned* transport in a seeded replay anchored to the real
LoRa pilot, while keeping the p95/p99 tail within measurement noise. The
repository is a DevOps artifact: every result is produced by the same command,
from the same commit, in the same image.

## What is inside

```
src/adaptedge/
  selector.py     explainable utility model + hysteresis
  simulator.py    seeded replay harness (5 link regimes)
  metrics.py      p50/p95/p99, jitter, deadline misses
  dataset.py      loads the real SF7/SF9 pilot CSVs and summarises them
  api.py          FastAPI: /health, /select, /metrics/sample, /metrics/pilot
  evaluate.py     writes reports/metrics.json (replay + real pilot summary)
tests/            unit, API, dataset, determinism and CLI tests
data/             extracted real LoRa pilot CSVs + provenance
Dockerfile        multi-stage, non-root, healthcheck
Jenkinsfile       lint → test → evaluate → build → smoke → publish → deploy
.github/workflows/GitHub Actions mirror (matrix + GHCR publish)
deploy/k8s/       namespace, deployment, service, kustomization
```

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/ruff check src tests
.venv/bin/pytest -q --cov=adaptedge --cov-report=term-missing
.venv/bin/python -m adaptedge.evaluate --runs 200 --seed 42 --out reports/metrics.json
```

Build and run the container with rootless nerdctl:

```bash
BUILDKIT_HOST=unix:///run/user/1000/buildkit/rootless \
  nerdctl build -t adaptedge:local .
nerdctl run --rm -p 127.0.0.1:18080:8000 adaptedge:local
curl http://127.0.0.1:18080/health
```

Example decision request:

```bash
curl -s -X POST http://127.0.0.1:18080/select \
  -H 'content-type: application/json' \
  -d '{"rtt_ms":220,"loss_pct":5,"jitter_ms":45,"handover":false}'
```

## Pipeline

The Jenkins pipeline is defined in [`Jenkinsfile`](Jenkinsfile) and executes:

1. **Checkout** — immutable commit identity, clean-tree check.
2. **Toolchain** — Python venv, pinned project extras, `nerdctl` and Java probe.
3. **Lint** — `ruff` with the project rules.
4. **Unit tests** — `pytest` + coverage + JUnit report.
5. **Reproducible evaluation** — 200 seeded episodes; `reports/metrics.json`.
6. **Build image** — multi-stage OCI image via `nerdctl build`.
7. **Smoke test** — starts the container and probes `/health`.
8. **Publish image** (optional) — pushes to GHCR when `PUSH_IMAGE=true`.
9. **Deploy** (optional) — Kubernetes when reachable, otherwise a local test
   container; both paths are implemented in `deploy/deploy.sh`.

GitHub Actions mirrors the quality gates and publishes the same image to GHCR.

## Reproducibility contract

- The replay is deterministic for a given `(runs, seed, switch_penalty_ms,
  deadline_ms)` tuple; a test asserts this.
- The real pilot CSVs are shipped in `data/`; CI checks the published SF7/SF9
  medians and the SF7 anchor used by the LoRa regime.
- The evaluation artifact contains the seed and configuration, not a timestamp,
  so two runs of the same commit produce byte-identical JSON.
- The container image is built from a pinned `python:3.12-slim` base and runs as
  UID 10001 with a read-only root filesystem in Kubernetes.
- The Jenkins job archives the JUnit XML, coverage XML and metrics JSON.

## Research context

The dissertation studies low-latency transport selection for WebRTC and QUIC on
an ESP32 + LoRa edge segment. The clean co-located pilot measured SF7 median
RTT `201.262 ms` (p95 `201.274 ms`, 46 acknowledged probes) and SF9 median
`637.697 ms` (32 probes), leaving about `112 ms` of the `750 ms` deadline at
SF9. These are baseline measurements, not a field or range result. This
repository does **not** replace the physical testbed: it is the automation
harness that carries the experiment's data-processing and regression checks
once the four-node stand is assembled.

Current seeded result (`--runs 200 --seed 42`): mean latency `148.030 ms` for
the adaptive selector versus `152.698 ms` for the best pinned transport
(WebRTC), a `3.057%` mean improvement; p95 is `286.677 ms` versus `285.410 ms`
(`-0.444%`) and p99 is `306.543 ms` versus `306.429 ms` (`-0.037%`), i.e. tail
parity within noise. The honest reading is that the replay's tail is dominated
by high-loss episodes where WebRTC is already optimal, so the gain is in the
mean, not the tail.

## Links

- Repository: <https://github.com/Erixest/adaptedge>
- Actions: <https://github.com/Erixest/adaptedge/actions>
- Assignment report and slides: see the parent `assignment5` folder.

## License

MIT — see [LICENSE](LICENSE).
