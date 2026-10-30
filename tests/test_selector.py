import pytest

from adaptedge.selector import (
    LinkState,
    Transport,
    expected_latency_ms,
    select_transport,
    utilities,
)


def test_clean_link_prefers_roq():
    state = LinkState(rtt_ms=60, loss_pct=0.5, jitter_ms=8)
    selection = select_transport(state)
    assert selection.transport is Transport.ROQ
    assert selection.utilities["roq"] > selection.utilities["moq"]
    assert selection.predicted_latency_ms["roq"] < selection.predicted_latency_ms["moq"]


def test_medium_loss_lora_link_prefers_moq():
    state = LinkState(rtt_ms=220, loss_pct=2, jitter_ms=45)
    selection = select_transport(state)
    assert selection.transport is Transport.MOQ


def test_high_loss_link_prefers_webrtc():
    state = LinkState(rtt_ms=220, loss_pct=6, jitter_ms=45)
    selection = select_transport(state)
    assert selection.transport is Transport.WEBRTC


def test_handover_prefers_webrtc():
    state = LinkState(rtt_ms=150, loss_pct=2, jitter_ms=35, handover=True)
    selection = select_transport(state)
    assert selection.transport is Transport.WEBRTC


def test_hysteresis_keeps_previous_transport():
    state = LinkState(rtt_ms=60, loss_pct=0.5, jitter_ms=8)
    forced = select_transport(state, previous="moq", hysteresis_ms=100.0)
    assert forced.transport is Transport.MOQ
    assert forced.reason.startswith("hysteresis")
    assert forced.switched is False


def test_switch_is_reported_when_margin_is_clear():
    state = LinkState(rtt_ms=220, loss_pct=2, jitter_ms=45)
    selection = select_transport(state, previous="roq", hysteresis_ms=0.01)
    assert selection.transport is Transport.MOQ
    assert selection.switched is True


def test_unknown_previous_transport_is_rejected():
    with pytest.raises(ValueError):
        select_transport(LinkState(rtt_ms=50, loss_pct=0, jitter_ms=2), previous="sctp")


def test_utilities_cover_all_transports_and_validate_state():
    state = LinkState(rtt_ms=50, loss_pct=0, jitter_ms=2, payload_bytes=64)
    scores = utilities(state)
    assert set(scores) == set(Transport)
    assert all(isinstance(value, float) for value in scores.values())
    assert expected_latency_ms(state, Transport.ROQ) > 0
    with pytest.raises(ValueError):
        LinkState(rtt_ms=-1, loss_pct=0, jitter_ms=2)
    with pytest.raises(ValueError):
        LinkState(rtt_ms=10, loss_pct=101, jitter_ms=2)
    with pytest.raises(ValueError):
        LinkState(rtt_ms=10, loss_pct=0, jitter_ms=2, payload_bytes=0)
