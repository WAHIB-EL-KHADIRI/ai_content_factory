"""Integration tests for API"""

import pytest
from fastapi.testclient import TestClient
from backend.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestHealthEndpoints:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_system_health(self, client):
        response = client.get("/api/v1/system/health")
        assert response.status_code == 200


class TestModelEndpoints:
    def test_list_models(self, client):
        response = client.get("/api/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0

    def test_estimate_cost(self, client):
        response = client.get(
            "/api/v1/models/estimate-cost",
            params={"task_type": "chat", "input_tokens": 1000, "output_tokens": 500}
        )
        assert response.status_code == 200
        data = response.json()
        assert "estimated_cost_usd" in data


class TestAgentEndpoints:
    def test_list_agents(self, client):
        response = client.get("/api/v1/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) >= 8


class TestBrandEndpoints:
    def test_create_brand(self, client):
        response = client.post("/api/v1/brands", json={
            "project_id": "test_project",
            "name": "Test Brand",
            "voice_tone": "professional",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Brand"


class TestMemoryEndpoints:
    def test_store_memory(self, client):
        response = client.post("/api/v1/memory/store", json={
            "content": "Test memory",
            "memory_type": "user_preference",
            "importance": 0.5,
        })
        assert response.status_code == 200

    def test_recall_memory(self, client):
        client.post("/api/v1/memory/store", json={
            "content": "python is great",
            "memory_type": "factual_knowledge",
        })
        response = client.post("/api/v1/memory/recall", json={
            "query": "python",
        })
        assert response.status_code == 200


class TestWorkflowEndpoints:
    def test_list_workflows(self, client):
        response = client.get("/api/v1/workflows")
        assert response.status_code == 200


class TestAnalyticsEndpoints:
    def test_dashboard(self, client):
        response = client.get("/api/v1/analytics/dashboard")
        assert response.status_code == 200

    def test_usage(self, client):
        response = client.get("/api/v1/analytics/usage")
        assert response.status_code == 200

    def test_costs(self, client):
        response = client.get("/api/v1/analytics/costs")
        assert response.status_code == 200
