from pathlib import Path

import pytest

from adaptedge.dataset import PILOT_SF7_MEDIAN_MS, load_rtt_ms, pilot_report
from adaptedge.simulator import REGIMES

DATA = Path(__file__).resolve().parents[1] / "data"


def test_real_sf7_pilot_matches_published_statistics():
    values = load_rtt_ms(DATA / "lora_pilot_sf7.csv")
    assert len(values) == 46
    assert min(values) == pytest.approx(201.245)
    assert max(values) == pytest.approx(201.286)
    assert sum(values) / len(values) == pytest.approx(201.2604, abs=1e-4)
    assert PILOT_SF7_MEDIAN_MS == pytest.approx(201.262)


def test_pilot_report_contains_sf7_and_sf9():
    report = pilot_report(DATA)
    assert report["available"] is True
    assert report["captures"]["sf7"]["samples"] == 46
    assert report["captures"]["sf9"]["samples"] == 32
    assert report["headline"]["sf7_median_ms"] == pytest.approx(201.262)
    assert report["headline"]["sf9_median_ms"] == pytest.approx(637.697)
    assert report["headline"]["sf9_margin_ms"] == pytest.approx(112.303, abs=0.01)


def test_lora_regime_contains_the_real_pilot_anchor():
    lora = next(regime for regime in REGIMES if regime.name == "lora")
    assert lora.rtt_range[0] < PILOT_SF7_MEDIAN_MS < lora.rtt_range[1]


def test_loader_rejects_missing_columns(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("seq,value\n1,2\n")
    with pytest.raises(ValueError):
        load_rtt_ms(path)
