from fastapi.testclient import TestClient

from adaptedge.api import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"


def test_select_endpoint_returns_explainable_decision():
    response = client.post(
        "/select",
        json={
            "rtt_ms": 220,
            "loss_pct": 5,
            "jitter_ms": 45,
            "handover": False,
            "payload_bytes": 1024,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["transport"] in {"roq", "moq", "webrtc"}
    assert set(body["utilities"]) == {"roq", "moq", "webrtc"}
    assert set(body["predicted_latency_ms"]) == {"roq", "moq", "webrtc"}
    assert body["reason"]


def test_select_rejects_invalid_input():
    response = client.post(
        "/select",
        json={"rtt_ms": -1, "loss_pct": 0, "jitter_ms": 1},
    )
    assert response.status_code == 422


def test_pilot_endpoint_returns_real_data():
    response = client.get("/metrics/pilot")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["captures"]["sf7"]["samples"] == 46


def test_metrics_endpoint_is_deterministic():
    first = client.get("/metrics/sample?runs=40&seed=9")
    second = client.get("/metrics/sample?runs=40&seed=9")
    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["summaries"]["adaptive"]["n"] == 40


def test_version_endpoint():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json()["version"] == "0.1.0"
