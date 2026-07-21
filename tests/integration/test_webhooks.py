"""Integration tests for webhook routes."""

import pytest
from fastapi.testclient import TestClient
from backend.api.app import create_app
from backend.db.models import User
from backend.core.auth import hash_password, create_access_token
from backend.api.webhooks import _in_memory_webhooks, _in_memory_deliveries


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clear_webhooks():
    _in_memory_webhooks.clear()
    _in_memory_deliveries.clear()
    yield
    _in_memory_webhooks.clear()
    _in_memory_deliveries.clear()


@pytest.fixture
def test_user(db_session):
    user = User(
        email="webhooktest@example.com",
        name="Webhook Tester",
        hashed_password=hash_password("testpass"),
        role="member",
        is_active=True,
    )
    existing = db_session.query(User).filter(User.email == "webhooktest@example.com").first()
    if existing:
        db_session.delete(existing)
        db_session.commit()
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def auth_header(test_user):
    token = create_access_token(
        {"sub": str(test_user.id), "email": test_user.email, "role": test_user.role}
    )
    return {"Authorization": f"Bearer {token}"}


class TestCreateWebhook:
    def test_create_with_valid_data(self, client, auth_header):
        response = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/hook",
                "events": ["content.created"],
                "description": "Test webhook",
            },
            headers=auth_header,
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["url"] == "https://example.com/hook"
        assert data["events"] == ["content.created"]
        assert data["description"] == "Test webhook"
        assert data["is_active"] is True
        assert "secret" in data

    def test_create_with_multiple_events(self, client, auth_header):
        response = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/hook2",
                "events": ["content.created", "content.published", "workflow.completed"],
            },
            headers=auth_header,
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["events"]) == 3

    def test_create_with_invalid_event(self, client, auth_header):
        response = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/hook",
                "events": ["invalid.event"],
            },
            headers=auth_header,
        )
        assert response.status_code == 422

    def test_create_without_auth(self, client):
        response = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/hook",
                "events": ["content.created"],
            },
        )
        assert response.status_code == 401

    def test_create_empty_events(self, client, auth_header):
        response = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/hook",
                "events": [],
            },
            headers=auth_header,
        )
        assert response.status_code == 422

    def test_create_with_custom_secret(self, client, auth_header):
        response = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/hook",
                "events": ["content.created"],
                "secret": "my-custom-secret-key",
            },
            headers=auth_header,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["secret"] == "my-custom-secret-key"


class TestListWebhooks:
    def test_list_empty(self, client, auth_header):
        response = client.get("/api/v1/webhooks", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert data["webhooks"] == []
        assert data["total"] == 0

    def test_list_after_create(self, client, auth_header):
        client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/hook",
                "events": ["content.created"],
            },
            headers=auth_header,
        )
        response = client.get("/api/v1/webhooks", headers=auth_header)
        data = response.json()
        assert data["total"] == 1
        assert data["webhooks"][0]["url"] == "https://example.com/hook"

    def test_list_multiple(self, client, auth_header):
        for i in range(3):
            client.post(
                "/api/v1/webhooks",
                json={
                    "url": f"https://example.com/hook{i}",
                    "events": ["content.created"],
                },
                headers=auth_header,
            )
        response = client.get("/api/v1/webhooks", headers=auth_header)
        data = response.json()
        assert data["total"] == 3

    def test_list_requires_auth(self, client):
        response = client.get("/api/v1/webhooks")
        assert response.status_code == 401


class TestDeleteWebhook:
    def test_delete_existing(self, client, auth_header):
        create_resp = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/to-delete",
                "events": ["content.created"],
            },
            headers=auth_header,
        )
        webhook_id = create_resp.json()["id"]

        response = client.delete(
            f"/api/v1/webhooks/{webhook_id}",
            headers=auth_header,
        )
        assert response.status_code == 200
        assert response.json()["id"] == webhook_id

        list_resp = client.get("/api/v1/webhooks", headers=auth_header)
        assert list_resp.json()["total"] == 0

    def test_delete_nonexistent(self, client, auth_header):
        response = client.delete(
            "/api/v1/webhooks/nonexistent-id",
            headers=auth_header,
        )
        assert response.status_code == 404

    def test_delete_requires_auth(self, client):
        response = client.delete("/api/v1/webhooks/some-id")
        assert response.status_code == 401


class TestWebhookTestDelivery:
    def test_test_delivery(self, client, auth_header):
        create_resp = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://httpbin.org/post",
                "events": ["content.created"],
            },
            headers=auth_header,
        )
        webhook_id = create_resp.json()["id"]

        response = client.post(
            f"/api/v1/webhooks/{webhook_id}/test",
            headers=auth_header,
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "status" in data
        assert data["event"] == "content.created"

    def test_test_delivery_nonexistent(self, client, auth_header):
        response = client.post(
            "/api/v1/webhooks/nonexistent/test",
            headers=auth_header,
        )
        assert response.status_code == 404

    def test_test_delivery_requires_auth(self, client):
        response = client.post("/api/v1/webhooks/some-id/test")
        assert response.status_code == 401

    def test_delivery_tracked(self, client, auth_header):
        create_resp = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://httpbin.org/post",
                "events": ["content.created"],
            },
            headers=auth_header,
        )
        webhook_id = create_resp.json()["id"]

        client.post(
            f"/api/v1/webhooks/{webhook_id}/test",
            headers=auth_header,
        )

        response = client.get(
            f"/api/v1/webhooks/{webhook_id}/deliveries",
            headers=auth_header,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
