"""
Comprehensive Backend API Tests — Buy or Wait?
Tests all endpoints:
1. GET / (Root / Route discovery)
2. GET /api/health (Health check, environment, Gemini, Supabase status)
3. GET /api/requests (Dataset requests listing)
4. POST /api/decide (Single request decision execution)
5. POST /api/decide (404 error handling)
6. POST /api/simulate (What-If purchase simulator)
7. POST /api/simulate (400 bad request error handling)
8. GET /api/history (Supabase / simulation history)
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api import app, container


@pytest.fixture(scope="module")
def client():
    """Initializes and yields TestClient for FastAPI app."""
    container.initialize()
    with TestClient(app) as test_client:
        yield test_client


def test_01_server_startup_and_routes(client):
    """Verifies that server starts, loads routes, and responds on root."""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert "endpoints" in data
    assert "/api/health" in data["endpoints"].values()
    assert "/api/decide" in data["endpoints"].values()
    assert "/api/simulate" in data["endpoints"].values()


def test_02_health_endpoint(client):
    """Verifies /api/health checks environment, Gemini, and Supabase safely."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "environment" in data
    assert "gemini" in data
    assert "supabase" in data
    
    # Assert zero secrets leaked in health payload
    health_str = str(data)
    assert "eyJhbG" not in health_str, "JWT secret leaked in health endpoint!"
    assert "AQ.A" not in health_str, "Gemini key leaked in health endpoint!"


def test_03_requests_endpoint(client):
    """Verifies GET /api/requests retrieves requests with limit and user filtering."""
    resp = client.get("/api/requests?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert len(data["requests"]) == 5
    first_req = data["requests"][0]
    assert "request_id" in first_req
    assert "user_id" in first_req
    assert "requested_amount" in first_req


def test_04_decide_endpoint_success(client):
    """Verifies POST /api/decide computes full deterministic financial decision."""
    payload = {"request_id": "request_01"}
    resp = client.post("/api/decide", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "request_01"
    assert "amount_safe_to_pay" in data
    assert "affordability_status" in data
    assert data["affordability_status"] in ["affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"]
    assert "recommended_payment_method" in data
    assert "payment_plan" in data
    assert "decision_explanation" in data
    assert len(data["decision_explanation"]) > 10


def test_05_decide_endpoint_not_found(client):
    """Verifies POST /api/decide returns 404 for unknown request ID."""
    payload = {"request_id": "non_existent_req_9999"}
    resp = client.post("/api/decide", json=payload)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_06_simulate_endpoint_success(client):
    """Verifies POST /api/simulate runs what-if multi-scenario simulation & ranking."""
    payload = {
        "request_id": "request_01",
        "scenarios": [
            {"purchase_amount": 25000.0, "payment_method": "full_payment", "scenario_label": "Standard Full"},
            {"purchase_amount": 25000.0, "payment_method": "wait", "scenario_label": "Standard Wait"},
            {"purchase_amount": 15000.0, "payment_method": "full_payment", "scenario_label": "Reduced Purchase"}
        ]
    }
    resp = client.post("/api/simulate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "request_01"
    assert data["total_scenarios"] == 3
    assert len(data["scenarios"]) == 3
    assert "best_scenario" in data
    assert "comparison_summary" in data


def test_07_simulate_endpoint_bad_request(client):
    """Verifies POST /api/simulate returns 400 for invalid payment method or non-positive amount."""
    # Invalid payment method
    payload_bad_method = {
        "request_id": "request_01",
        "scenarios": [{"purchase_amount": 10000.0, "payment_method": "crypto_transfer"}]
    }
    resp1 = client.post("/api/simulate", json=payload_bad_method)
    assert resp1.status_code == 400

    # Non-positive amount
    payload_bad_amount = {
        "request_id": "request_01",
        "scenarios": [{"purchase_amount": -500.0, "payment_method": "full_payment"}]
    }
    resp2 = client.post("/api/simulate", json=payload_bad_amount)
    assert resp2.status_code in [400, 422]


def test_08_history_endpoint(client):
    """Verifies GET /api/history returns history records structure."""
    resp = client.get("/api/history?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "source" in data
    assert "records" in data


def test_09_dashboard_endpoint(client):
    """Verifies GET /dashboard returns HTML dashboard interface."""
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "Buy or Wait?" in resp.text

