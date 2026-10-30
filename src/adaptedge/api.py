"""Minimal REST surface for the containerized research artifact."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

from . import __version__
from .dataset import pilot_report
from .selector import LinkState, Transport, select_transport
from .simulator import run_simulation

app = FastAPI(
    title="AdaptEdge API",
    version=__version__,
    description="Adaptive WebRTC/QUIC transport selection replay harness",
)


class LinkStateIn(BaseModel):
    rtt_ms: float = Field(ge=0, le=10_000, examples=[180.0])
    loss_pct: float = Field(ge=0, le=100, examples=[5.0])
    jitter_ms: float = Field(ge=0, le=10_000, examples=[45.0])
    handover: bool = False
    payload_bytes: int = Field(default=1024, ge=1, le=1_000_000)
    previous: Transport | None = None


class SelectionOut(BaseModel):
    transport: Transport
    utilities: dict[str, float]
    predicted_latency_ms: dict[str, float]
    reason: str
    switched: bool


@lru_cache(maxsize=4)
def _sample_metrics(runs: int, seed: int) -> dict:
    result = run_simulation(runs=runs, seed=seed)
    result.pop("episodes", None)
    return result


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "adaptedge", "version": __version__}


@app.get("/version")
def version() -> dict[str, str]:
    return {"version": __version__}


@app.post("/select", response_model=SelectionOut)
def select(payload: LinkStateIn) -> SelectionOut:
    state = LinkState(
        rtt_ms=payload.rtt_ms,
        loss_pct=payload.loss_pct,
        jitter_ms=payload.jitter_ms,
        handover=payload.handover,
        payload_bytes=payload.payload_bytes,
    )
    selection = select_transport(state, previous=payload.previous)
    return SelectionOut(
        transport=selection.transport,
        utilities=selection.utilities,
        predicted_latency_ms=selection.predicted_latency_ms,
        reason=selection.reason,
        switched=selection.switched,
    )


@app.get("/metrics/pilot")
def metrics_pilot() -> dict:
    data_dir = Path(os.environ.get("ADAPTEDGE_DATA_DIR", "data"))
    return pilot_report(data_dir)


@app.get("/metrics/sample")
def sample_metrics(runs: int = 120, seed: int = 7) -> dict:
    if not 1 <= runs <= 2000:
        runs = 120
    result = _sample_metrics(runs, seed)
    return {
        "config": result["config"],
        "best_pinned": result["best_pinned"],
        "p99_improvement_pct": result["p99_improvement_pct"],
        "summaries": result["summaries"],
        "deadline_miss_pct": result["deadline_miss_pct"],
    }


@app.get("/metrics/sample/summary")
def sample_summary(runs: int = 120, seed: int = 7) -> dict:
    result = _sample_metrics(runs, seed)
    return {"adaptive": result["summaries"]["adaptive"]}
