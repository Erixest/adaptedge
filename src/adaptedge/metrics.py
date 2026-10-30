"""Latency statistics used by the replay harness and the REST API."""

from __future__ import annotations

import math
from collections.abc import Iterable


def percentile(values: Iterable[float], q: float) -> float:
    """Return the q-th percentile using linear interpolation (0 <= q <= 100)."""
    if not 0 <= q <= 100:
        raise ValueError("q must be between 0 and 100")
    ordered = sorted(float(v) for v in values)
    if not ordered:
        raise ValueError("percentile of empty sequence")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * (q / 100.0)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[int(position)]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def summarize(values: Iterable[float]) -> dict[str, float | int]:
    """Summarize a latency sample in milliseconds.

    The tail percentiles are the primary decision metric for interactive
    transport selection; jitter is reported as the population standard
    deviation so that the same input always produces the same output.
    """
    sample = [float(v) for v in values]
    if not sample:
        raise ValueError("cannot summarize an empty sample")
    mean = sum(sample) / len(sample)
    variance = sum((v - mean) ** 2 for v in sample) / len(sample)
    return {
        "n": len(sample),
        "mean_ms": round(mean, 3),
        "p50_ms": round(percentile(sample, 50), 3),
        "p95_ms": round(percentile(sample, 95), 3),
        "p99_ms": round(percentile(sample, 99), 3),
        "jitter_ms": round(math.sqrt(variance), 3),
        "max_ms": round(max(sample), 3),
    }


def deadline_miss_pct(values: Iterable[float], deadline_ms: float) -> float:
    """Return the percentage of samples that exceed a hard deadline."""
    sample = [float(v) for v in values]
    if not sample:
        raise ValueError("cannot evaluate an empty sample")
    if deadline_ms <= 0:
        raise ValueError("deadline_ms must be positive")
    missed = sum(1 for v in sample if v > deadline_ms)
    return round(100.0 * missed / len(sample), 3)
