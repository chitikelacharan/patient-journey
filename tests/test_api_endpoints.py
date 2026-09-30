import pytest
from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "uptime_seconds" in data
    assert data["hipaa_audit_mode"] == "ACTIVE_SHA256"

def test_prometheus_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "medpulse_uptime_seconds" in response.text
    assert "medpulse_http_requests_total" in response.text

def test_kpi_summary_endpoint():
    response = client.get("/api/bottlenecks/kpi-summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_cohort_patients" in data
    assert "avg_length_of_stay_hours" in data
    assert "healed_anomalies_count" in data

def test_top_bottlenecks_endpoint():
    response = client.get("/api/bottlenecks/top?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_root_cause_analysis_endpoint():
    response = client.get("/api/ai/root-cause")
    assert response.status_code == 200
    data = response.json()
    assert "factors" in data
    assert len(data["factors"]) > 0

def test_what_if_simulation_endpoint():
    payload = {
        "prior_auth_automation_pct": 50.0,
        "diagnostic_batch_speedup_pct": 30.0,
        "discharge_transport_speedup_pct": 20.0
    }
    response = client.post("/api/ai/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["hours_saved_per_patient"] >= 0
    assert data["wait_time_reduction_pct"] >= 0

def test_hipaa_audit_verification_endpoint():
    response = client.get("/api/audit/verify")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["tamper_detected"] is False

def test_adversarial_injection_sandbox():
    payload = {
        "scenario": "OUT_OF_ORDER",
        "patient_identifier": "TEST-CI-PATIENT-99",
        "cohort": "Emergency"
    }
    response = client.post("/api/adversarial/inject", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["scenario"] == "OUT_OF_ORDER_TIMESTAMP"
    assert data["result"]["status"] == "AUTOCORRECTED"
