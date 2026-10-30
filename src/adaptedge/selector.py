"""Deterministic expected-latency transport selector.

The selector is intentionally small and explainable: a transparent linear model
encodes the operational intuition from the LoRa/ESP32 pilot (RoQ is cheapest
on clean links, MoQ tolerates moderate loss, WebRTC survives high loss and
handovers). A hysteresis margin in milliseconds prevents control-plane
flapping when two transports are nearly tied.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Transport(StrEnum):
    ROQ = "roq"
    MOQ = "moq"
    WEBRTC = "webrtc"


@dataclass(frozen=True)
class LinkState:
    """Observed link features for one decision epoch."""

    rtt_ms: float
    loss_pct: float
    jitter_ms: float
    handover: bool = False
    payload_bytes: int = 1024

    def __post_init__(self) -> None:
        if self.rtt_ms < 0:
            raise ValueError("rtt_ms must be non-negative")
        if not 0 <= self.loss_pct <= 100:
            raise ValueError("loss_pct must be between 0 and 100")
        if self.jitter_ms < 0:
            raise ValueError("jitter_ms must be non-negative")
        if self.payload_bytes <= 0:
            raise ValueError("payload_bytes must be positive")


@dataclass(frozen=True)
class Selection:
    transport: Transport
    utilities: dict[str, float]
    predicted_latency_ms: dict[str, float]
    reason: str
    switched: bool


def expected_latency_ms(state: LinkState, transport: Transport) -> float:
    """Expected latency in milliseconds for a link state.

    This is the single model shared with the replay harness; the harness adds
    seeded Gaussian measurement noise on top of these expected values.
    """
    rtt = state.rtt_ms
    loss = state.loss_pct
    jitter = state.jitter_ms
    handover = state.handover

    if transport is Transport.ROQ:
        return rtt * 1.00 + 0.10 * jitter + 30.0 * loss + (70.0 if handover else 0.0)
    if transport is Transport.MOQ:
        return (
            rtt * 1.04
            + 0.10 * jitter
            + 8.0 * loss
            + 12.0
            + (55.0 if handover else 0.0)
        )
    return rtt * 1.04 + 0.20 * jitter + 2.0 * loss + 24.0


def utilities(state: LinkState) -> dict[Transport, float]:
    """Return a higher-is-better score for each transport.

    The score is the negative expected latency, so a utility margin is directly
    interpretable as milliseconds saved by switching.
    """
    return {
        transport: round(-expected_latency_ms(state, transport), 6)
        for transport in Transport
    }


def select_transport(
    state: LinkState,
    previous: str | Transport | None = None,
    hysteresis_ms: float = 5.0,
) -> Selection:
    """Pick the lowest predicted-latency transport, with switch hysteresis."""
    if hysteresis_ms < 0:
        raise ValueError("hysteresis_ms must be non-negative")
    scores = utilities(state)
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0].value))
    best, best_score = ranked[0]

    previous_transport: Transport | None
    if previous is None:
        previous_transport = None
    else:
        try:
            previous_transport = Transport(previous)
        except ValueError as exc:
            raise ValueError(f"unknown previous transport: {previous!r}") from exc

    if (
        previous_transport is not None
        and previous_transport != best
        and best_score - scores[previous_transport] < hysteresis_ms
    ):
        chosen = previous_transport
        reason = "hysteresis: kept previous transport inside the margin"
        switched = False
    else:
        chosen = best
        reason = "lowest predicted latency"
        switched = previous_transport is not None and previous_transport != chosen

    return Selection(
        transport=chosen,
        utilities={transport.value: score for transport, score in scores.items()},
        predicted_latency_ms={
            transport.value: round(-score, 3) for transport, score in scores.items()
        },
        reason=reason,
        switched=switched,
    )
