"""Real pilot-data access for calibration and regression checks.

The CSV files in ``data/`` are extracted from the dissertation's Heltec
LoRa RTT captures (``ACK_OK`` rows only). They are deliberately small enough
to ship with the repository so that CI can assert the published pilot numbers
without downloading the multi-gigabyte raw run archive.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .metrics import percentile, summarize

PILOT_SF7_MEDIAN_MS = 201.262

PILOT_FILES = {
    "sf7": "lora_pilot_sf7.csv",
    "sf9": "lora_pilot_sf9.csv",
    "sf7_minus9dbm": "lora_pilot_sf7_minus9dbm.csv",
}


def load_rtt_ms(path: Path) -> list[float]:
    """Load ``seq,rtt_us`` rows and return RTT in milliseconds."""
    values: list[float] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"seq", "rtt_us"}
        if not required.issubset(reader.fieldnames or set()):
            raise ValueError(f"{path} must contain columns {sorted(required)}")
        for row in reader:
            rtt_us = float(row["rtt_us"])
            if rtt_us <= 0:
                raise ValueError(f"{path} contains a non-positive RTT")
            values.append(rtt_us / 1000.0)
    if not values:
        raise ValueError(f"{path} contains no samples")
    return values


def pilot_report(data_dir: Path) -> dict:
    """Return summaries for every shipped pilot capture."""
    report: dict = {"available": False, "captures": {}}
    for key, filename in PILOT_FILES.items():
        path = data_dir / filename
        if not path.exists():
            continue
        values = load_rtt_ms(path)
        summary = summarize(values)
        summary["p99_us"] = round(percentile([v * 1000 for v in values], 99), 1)
        report["captures"][key] = {
            "source": str(path.as_posix()),
            "samples": len(values),
            "summary": summary,
        }
    report["available"] = bool(report["captures"])
    if report["available"]:
        sf7 = report["captures"].get("sf7", {}).get("summary", {})
        sf9 = report["captures"].get("sf9", {}).get("summary", {})
        report["headline"] = {
            "sf7_median_ms": sf7.get("p50_ms"),
            "sf7_p95_ms": sf7.get("p95_ms"),
            "sf9_median_ms": sf9.get("p50_ms"),
            "deadline_ms": 750.0,
            "sf9_margin_ms": round(750.0 - sf9.get("p50_ms", 0.0), 3) if sf9 else None,
        }
    return report
