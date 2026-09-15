"""Tests for authentication system"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from backend.api.app import create_app
from backend.db.models import User
from backend.core.auth import hash_password, verify_password, create_access_token, decode_access_token
from backend.core.config import get_config


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_user(db_session):
    user = User(
        email="authtest@example.com",
        name="Test User",
        hashed_password=hash_password("password123"),
        role="member",
        is_active=True,
    )
    existing = db_session.query(User).filter(User.email == "authtest@example.com").first()
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


class TestPasswordHashing:
    def test_hash_password(self):
        hashed = hash_password("mypassword")
        assert hashed != "mypassword"
        assert "$" in hashed

    def test_verify_password_correct(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_malformed(self):
        assert verify_password("test", "nohash") is False


class TestJWTTokens:
    def test_create_and_decode_token(self):
        token = create_access_token({"sub": "user123", "role": "admin"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"

    def test_decode_invalid_token(self):
        payload = decode_access_token("invalid.token.here")
        assert payload is None

    def test_expired_token_is_rejected(self):
        """A token past its exp must not decode.

        decode_access_token returns None for every rejection, so an accepted
        expired token would look exactly like a valid one to every caller --
        which is an authentication bypass, not a test-only detail. The
        existing cases cover a valid token and a malformed one; neither would
        catch expiry verification being silently dropped.
        """
        token = create_access_token({"sub": "user123"}, expires_delta=timedelta(seconds=-60))
        assert decode_access_token(token) is None

    def test_token_signed_with_another_key_is_rejected(self):
        """The signature has to be checked against our key, not just parsed."""
        config = get_config()
        forged = jwt.encode(
            {"sub": "user123", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            "an-attacker-controlled-key",
            algorithm=config.security.algorithm,
        )
        assert decode_access_token(forged) is None

    def test_unsigned_token_is_rejected(self):
        """alg=none must not be honoured.

        decode() is called with an explicit algorithms= list, which is what
        makes this safe; the test exists so that removing the list fails here.
        """
        unsigned = jwt.encode(
            {"sub": "user123", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            key="",
            algorithm="none",
        )
        assert decode_access_token(unsigned) is None

    def test_a_tampered_signature_is_rejected(self):
        token = create_access_token({"sub": "user123"})
        tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
        assert decode_access_token(tampered) is None


class TestRegisterEndpoint:
    def test_register_success(self, client, db_session):
        response = client.post("/api/v1/auth/register", json={
            "email": "newreg@example.com",
            "name": "New User",
            "password": "securepass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "newreg@example.com"
        assert data["user"]["name"] == "New User"
        user = db_session.query(User).filter(User.email == "newreg@example.com").first()
        if user:
            db_session.delete(user)
            db_session.commit()

    def test_register_duplicate_email(self, client, test_user):
        response = client.post("/api/v1/auth/register", json={
            "email": "authtest@example.com",
            "name": "Another User",
            "password": "securepass123",
        })
        assert response.status_code == 409

    def test_register_short_password(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "short@example.com",
            "name": "User",
            "password": "short",
        })
        assert response.status_code == 422


class TestLoginEndpoint:
    def test_login_success(self, client, test_user):
        response = client.post("/api/v1/auth/login", json={
            "email": "authtest@example.com",
            "password": "password123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "authtest@example.com"

    def test_login_wrong_password(self, client, test_user):
        response = client.post("/api/v1/auth/login", json={
            "email": "authtest@example.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123",
        })
        assert response.status_code == 401


class TestMeEndpoint:
    def test_get_me_authenticated(self, client, test_user, auth_header):
        response = client.get("/api/v1/auth/me", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "authtest@example.com"
        assert data["name"] == "Test User"

    def test_get_me_unauthenticated(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client):
        response = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert response.status_code == 401


class TestChangePassword:
    def test_change_password_success(self, client, test_user, auth_header):
        response = client.post("/api/v1/auth/change-password", json={
            "current_password": "password123",
            "new_password": "newpassword456",
        }, headers=auth_header)
        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"

    def test_change_password_wrong_current(self, client, test_user, auth_header):
        response = client.post("/api/v1/auth/change-password", json={
            "current_password": "wrongpassword",
            "new_password": "newpassword456",
        }, headers=auth_header)
        assert response.status_code == 400
