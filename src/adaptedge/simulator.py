"""Synthetic replay harness calibrated to the edge-segment pilot.

This is deliberately a *replay* benchmark, not a claim about the physical
testbed: regimes and transport penalties are transparent, seeded, and small
enough to audit. The harness exists so that every CI run produces the same
latency distribution and the same decision trace from the same seed.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from .dataset import PILOT_SF7_MEDIAN_MS
from .metrics import deadline_miss_pct, summarize
from .selector import LinkState, Transport, expected_latency_ms, select_transport

TRANSPORTS: tuple[Transport, ...] = (Transport.ROQ, Transport.MOQ, Transport.WEBRTC)


@dataclass(frozen=True)
class Regime:
    name: str
    rtt_range: tuple[float, float]
    loss_range: tuple[float, float]
    jitter_range: tuple[float, float]
    handover: bool
    weight: float


REGIMES: tuple[Regime, ...] = (
    Regime("wifi", (35.0, 75.0), (0.0, 1.0), (2.0, 10.0), False, 0.25),
    Regime("5g", (25.0, 60.0), (0.0, 0.8), (2.0, 8.0), False, 0.20),
    Regime("4g", (90.0, 160.0), (0.5, 2.0), (8.0, 25.0), False, 0.20),
    # The real SF7 pilot median (201.262 ms) anchors this regime; the range is
    # widened to stress the selector beyond the clean co-located baseline.
    Regime(
        "lora",
        (PILOT_SF7_MEDIAN_MS - 20.0, PILOT_SF7_MEDIAN_MS + 60.0),
        (2.0, 6.0),
        (25.0, 60.0),
        False,
        0.25,
    ),
    Regime("handover", (110.0, 210.0), (1.0, 4.0), (30.0, 80.0), True, 0.10),
)


def _latency_ms(transport: Transport, state: LinkState, rng: random.Random) -> float:
    """Expected latency plus seeded measurement noise."""
    return max(1.0, expected_latency_ms(state, transport) + rng.gauss(0.0, 3.0))


def _sample_state(regime: Regime, rng: random.Random) -> LinkState:
    return LinkState(
        rtt_ms=round(rng.uniform(*regime.rtt_range), 2),
        loss_pct=round(rng.uniform(*regime.loss_range), 3),
        jitter_ms=round(rng.uniform(*regime.jitter_range), 2),
        handover=regime.handover,
        payload_bytes=rng.choice((64, 512, 1024, 4096, 10240)),
    )


def run_simulation(
    runs: int = 200,
    seed: int = 42,
    switch_penalty_ms: float = 6.0,
    deadline_ms: float = 750.0,
) -> dict[str, Any]:
    """Run a deterministic replay and return per-episode and aggregate data."""
    if runs <= 0:
        raise ValueError("runs must be positive")
    if switch_penalty_ms < 0:
        raise ValueError("switch_penalty_ms must be non-negative")
    if deadline_ms <= 0:
        raise ValueError("deadline_ms must be positive")

    rng = random.Random(seed)
    weights = [regime.weight for regime in REGIMES]
    episodes: list[dict[str, Any]] = []
    latencies: dict[str, list[float]] = {transport.value: [] for transport in TRANSPORTS}
    latencies["adaptive"] = []
    latencies["oracle"] = []
    previous: Transport | None = None
    switch_count = 0
    selection_counts = {transport.value: 0 for transport in TRANSPORTS}

    for episode_index in range(runs):
        regime = rng.choices(REGIMES, weights=weights, k=1)[0]
        state = _sample_state(regime, rng)
        measured = {
            transport.value: round(_latency_ms(transport, state, rng), 3)
            for transport in TRANSPORTS
        }
        decision = select_transport(state, previous=previous)
        penalty = (
            switch_penalty_ms
            if previous is not None and decision.transport is not previous
            else 0.0
        )
        adaptive_latency = measured[decision.transport.value] + penalty
        oracle_latency = min(measured.values())
        if decision.switched:
            switch_count += 1
        selection_counts[decision.transport.value] += 1
        previous = decision.transport

        for transport in TRANSPORTS:
            latencies[transport.value].append(measured[transport.value])
        latencies["adaptive"].append(round(adaptive_latency, 3))
        latencies["oracle"].append(round(oracle_latency, 3))
        episodes.append(
            {
                "episode": episode_index,
                "regime": regime.name,
                "rtt_ms": state.rtt_ms,
                "loss_pct": state.loss_pct,
                "jitter_ms": state.jitter_ms,
                "handover": state.handover,
                "payload_bytes": state.payload_bytes,
                "selected": decision.transport.value,
                "switched": decision.switched,
                "latency_ms": measured,
                "adaptive_latency_ms": round(adaptive_latency, 3),
                "oracle_latency_ms": round(oracle_latency, 3),
            }
        )

    summaries = {name: summarize(values) for name, values in latencies.items()}
    pinned_p95 = {name: summaries[name]["p95_ms"] for name in ("roq", "moq", "webrtc")}
    pinned_p99 = {name: summaries[name]["p99_ms"] for name in ("roq", "moq", "webrtc")}
    best_pinned = min(pinned_p95, key=lambda name: (pinned_p95[name], name))
    adaptive_p95 = float(summaries["adaptive"]["p95_ms"])
    adaptive_p99 = float(summaries["adaptive"]["p99_ms"])
    adaptive_mean = float(summaries["adaptive"]["mean_ms"])
    best_pinned_p95 = float(pinned_p95[best_pinned])
    best_pinned_p99 = float(pinned_p99[best_pinned])
    best_pinned_mean = float(summaries[best_pinned]["mean_ms"])

    return {
        "schema_version": 1,
        "config": {
            "runs": runs,
            "seed": seed,
            "switch_penalty_ms": switch_penalty_ms,
            "deadline_ms": deadline_ms,
        },
        "summaries": summaries,
        "best_pinned": best_pinned,
        "mean_improvement_pct": round(
            100.0 * (best_pinned_mean - adaptive_mean) / best_pinned_mean, 3
        ),
        "p95_improvement_pct": round(
            100.0 * (best_pinned_p95 - adaptive_p95) / best_pinned_p95, 3
        ),
        "p99_improvement_pct": round(
            100.0 * (best_pinned_p99 - adaptive_p99) / best_pinned_p99, 3
        ),
        "switch_count": switch_count,
        "selection_counts": selection_counts,
        "deadline_miss_pct": {
            name: deadline_miss_pct(values, deadline_ms) for name, values in latencies.items()
        },
        "episodes": episodes,
    }
