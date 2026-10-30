import pytest

from adaptedge.metrics import deadline_miss_pct, percentile, summarize


def test_percentile_interpolates_and_handles_edges():
    values = [10.0, 20.0, 30.0, 40.0]
    assert percentile(values, 0) == 10.0
    assert percentile(values, 50) == 25.0
    assert percentile(values, 100) == 40.0
    assert percentile([7.0], 99) == 7.0


def test_percentile_rejects_empty_and_invalid_q():
    with pytest.raises(ValueError):
        percentile([], 50)
    with pytest.raises(ValueError):
        percentile([1, 2, 3], 101)


def test_summarize_reports_tail_statistics():
    summary = summarize([100, 110, 120, 130, 140])
    assert summary["n"] == 5
    assert summary["p50_ms"] == 120.0
    assert summary["p99_ms"] == pytest.approx(139.6)
    assert summary["max_ms"] == 140.0
    assert summary["jitter_ms"] > 0


def test_summarize_rejects_empty_sample():
    with pytest.raises(ValueError):
        summarize([])


def test_deadline_miss_percentage():
    assert deadline_miss_pct([100, 200, 800, 900], 750) == 50.0
    with pytest.raises(ValueError):
        deadline_miss_pct([], 750)
    with pytest.raises(ValueError):
        deadline_miss_pct([1], 0)
