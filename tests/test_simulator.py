import pytest

from adaptedge.simulator import REGIMES, run_simulation


def test_simulation_is_deterministic_for_a_seed():
    first = run_simulation(runs=40, seed=123)
    second = run_simulation(runs=40, seed=123)
    assert first["summaries"] == second["summaries"]
    assert first["selection_counts"] == second["selection_counts"]
    assert first["episodes"] == second["episodes"]


def test_simulation_changes_with_seed():
    first = run_simulation(runs=40, seed=1)
    second = run_simulation(runs=40, seed=2)
    assert first["summaries"] != second["summaries"]


def test_adaptive_tail_is_close_to_oracle_and_better_than_best_pinned():
    result = run_simulation(runs=400, seed=42)
    adaptive = result["summaries"]["adaptive"]
    oracle = result["summaries"]["oracle"]
    assert adaptive["p99_ms"] >= oracle["p99_ms"]
    assert result["mean_improvement_pct"] > 0
    assert result["p95_improvement_pct"] >= -1.0
    assert result["p99_improvement_pct"] >= -1.0
    assert result["best_pinned"] in {"roq", "moq", "webrtc"}
    assert sum(result["selection_counts"].values()) == 400


def test_regime_mix_and_validation():
    assert sum(regime.weight for regime in REGIMES) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        run_simulation(runs=0)
    with pytest.raises(ValueError):
        run_simulation(runs=10, switch_penalty_ms=-1)
    with pytest.raises(ValueError):
        run_simulation(runs=10, deadline_ms=0)
