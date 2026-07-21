"""Integration tests for admin routes."""

import pytest
from fastapi.testclient import TestClient
from backend.api.app import create_app
from backend.db.models import User, AuditLog
from backend.core.auth import hash_password, create_access_token


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_user(db_session):
    user = User(
        email="admin@example.com",
        name="Admin User",
        hashed_password=hash_password("adminpass"),
        role="admin",
        is_active=True,
    )
    existing = db_session.query(User).filter(User.email == "admin@example.com").first()
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
def member_user(db_session):
    user = User(
        email="member@example.com",
        name="Member User",
        hashed_password=hash_password("memberpass"),
        role="member",
        is_active=True,
    )
    existing = db_session.query(User).filter(User.email == "member@example.com").first()
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
def admin_header(admin_user):
    token = create_access_token(
        {"sub": str(admin_user.id), "email": admin_user.email, "role": admin_user.role}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def member_header(member_user):
    token = create_access_token(
        {"sub": str(member_user.id), "email": member_user.email, "role": member_user.role}
    )
    return {"Authorization": f"Bearer {token}"}


class TestAdminRequiresAuth:
    def test_no_token_returns_401(self, client):
        response = client.get("/api/v1/admin/stats")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client):
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


class TestAdminRequiresAdminRole:
    def test_member_user_gets_403(self, client, member_header):
        response = client.get("/api/v1/admin/stats", headers=member_header)
        assert response.status_code == 403

    def test_admin_user_gets_200(self, client, admin_header):
        response = client.get("/api/v1/admin/stats", headers=admin_header)
        assert response.status_code == 200


class TestAdminStats:
    def test_returns_system_stats(self, client, admin_header):
        response = client.get("/api/v1/admin/stats", headers=admin_header)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "projects" in data
        assert "content" in data
        assert "api_usage" in data

    def test_users_structure(self, client, admin_header):
        response = client.get("/api/v1/admin/stats", headers=admin_header)
        data = response.json()
        users = data["users"]
        assert "total" in users
        assert "active" in users
        assert "inactive" in users
        assert isinstance(users["total"], int)

    def test_api_usage_structure(self, client, admin_header):
        response = client.get("/api/v1/admin/stats", headers=admin_header)
        data = response.json()
        api = data["api_usage"]
        assert "total_calls" in api
        assert "total_tokens" in api
        assert "total_cost_usd" in api

    def test_stats_include_current_users(self, client, admin_header):
        response = client.get("/api/v1/admin/stats", headers=admin_header)
        data = response.json()
        assert data["users"]["total"] >= 1


class TestAdminListUsers:
    def test_returns_paginated_list(self, client, admin_header):
        response = client.get("/api/v1/admin/users", headers=admin_header)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "total_pages" in data

    def test_pagination_params(self, client, admin_header):
        response = client.get(
            "/api/v1/admin/users",
            params={"page": 1, "page_size": 1},
            headers=admin_header,
        )
        data = response.json()
        assert len(data["items"]) <= 1
        assert data["page"] == 1

    def test_search_by_email(self, client, admin_header):
        response = client.get(
            "/api/v1/admin/users",
            params={"search": "admin"},
            headers=admin_header,
        )
        data = response.json()
        assert len(data["items"]) >= 1
        emails = [u["email"] for u in data["items"]]
        assert any("admin" in e for e in emails)

    def test_filter_by_role(self, client, admin_header):
        response = client.get(
            "/api/v1/admin/users",
            params={"role": "admin"},
            headers=admin_header,
        )
        data = response.json()
        assert len(data["items"]) >= 1
        for user in data["items"]:
            assert user["role"] == "admin"

    def test_user_item_fields(self, client, admin_header):
        response = client.get("/api/v1/admin/users", headers=admin_header)
        data = response.json()
        user = data["items"][0]
        assert "id" in user
        assert "email" in user
        assert "name" in user
        assert "role" in user
        assert "is_active" in user


class TestAdminChangeRole:
    def test_change_role_success(self, client, admin_header, member_user):
        response = client.put(
            f"/api/v1/admin/users/{member_user.id}/role",
            json={"role": "admin"},
            headers=admin_header,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert "Role updated" in data["message"]

    def test_change_role_to_viewer(self, client, admin_header, member_user):
        response = client.put(
            f"/api/v1/admin/users/{member_user.id}/role",
            json={"role": "viewer"},
            headers=admin_header,
        )
        assert response.status_code == 200
        assert response.json()["role"] == "viewer"

    def test_cannot_change_own_role(self, client, admin_header, admin_user):
        response = client.put(
            f"/api/v1/admin/users/{admin_user.id}/role",
            json={"role": "member"},
            headers=admin_header,
        )
        assert response.status_code == 400

    def test_user_not_found(self, client, admin_header):
        response = client.put(
            "/api/v1/admin/users/nonexistent-id/role",
            json={"role": "admin"},
            headers=admin_header,
        )
        assert response.status_code == 404

    def test_invalid_role_rejected(self, client, admin_header, member_user):
        response = client.put(
            f"/api/v1/admin/users/{member_user.id}/role",
            json={"role": "superadmin"},
            headers=admin_header,
        )
        assert response.status_code == 422

    def test_creates_audit_log(self, client, admin_header, member_user, db_session):
        client.put(
            f"/api/v1/admin/users/{member_user.id}/role",
            json={"role": "viewer"},
            headers=admin_header,
        )
        audit = db_session.query(AuditLog).filter(
            AuditLog.resource_id == str(member_user.id),
            AuditLog.action == "role_changed",
        ).first()
        assert audit is not None
        assert audit.details["old_role"] == "member"
        assert audit.details["new_role"] == "viewer"


class TestAdminAuditLog:
    def test_returns_audit_entries(self, client, admin_header):
        response = client.get("/api/v1/admin/audit-log", headers=admin_header)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_audit_log_item_fields(self, client, admin_header, admin_user, member_user, db_session):
        audit = AuditLog(
            user_id=str(admin_user.id),
            action="test_action",
            resource_type="test_resource",
            resource_id="test-123",
            details={"key": "value"},
        )
        db_session.add(audit)
        db_session.commit()

        response = client.get("/api/v1/admin/audit-log", headers=admin_header)
        data = response.json()
        found = [item for item in data["items"] if item["action"] == "test_action"]
        assert len(found) >= 1
        item = found[0]
        assert item["resource_type"] == "test_resource"
        assert item["resource_id"] == "test-123"
        assert item["details"]["key"] == "value"

    def test_filter_by_action(self, client, admin_header, admin_user, db_session):
        audit = AuditLog(
            user_id=str(admin_user.id),
            action="login",
            resource_type="session",
        )
        db_session.add(audit)
        db_session.commit()

        response = client.get(
            "/api/v1/admin/audit-log",
            params={"action": "login"},
            headers=admin_header,
        )
        data = response.json()
        assert len(data["items"]) >= 1
        for item in data["items"]:
            assert item["action"] == "login"

    def test_filter_by_resource_type(self, client, admin_header, admin_user, db_session):
        audit = AuditLog(
            user_id=str(admin_user.id),
            action="update",
            resource_type="content",
        )
        db_session.add(audit)
        db_session.commit()

        response = client.get(
            "/api/v1/admin/audit-log",
            params={"resource_type": "content"},
            headers=admin_header,
        )
        data = response.json()
        for item in data["items"]:
            assert item["resource_type"] == "content"

    def test_pagination(self, client, admin_header):
        response = client.get(
            "/api/v1/admin/audit-log",
            params={"page": 1, "page_size": 5},
            headers=admin_header,
        )
        data = response.json()
        assert data["page"] == 1
        assert len(data["items"]) <= 5
