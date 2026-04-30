"""End-to-end API smoke tests via FastAPI TestClient (moto DynamoDB)."""
import pytest


class TestHealth:
    def test_health_returns_200(self, api_client):
        resp = api_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["app"] == "OT Sentinel"


class TestAuth:
    def test_login_with_valid_credentials(self, seeded_user, api_client):
        resp = api_client.post(
            "/api/auth/login",
            json={"email": "admin@otsentinel.com", "password": "Admin1234!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "admin@otsentinel.com"
        assert data["user"]["role"] == "admin"

    def test_login_with_wrong_password_returns_401(self, seeded_user, api_client):
        resp = api_client.post(
            "/api/auth/login",
            json={"email": "admin@otsentinel.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_login_with_unknown_email_returns_401(self, api_client):
        resp = api_client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "whatever"},
        )
        assert resp.status_code == 401

    def test_me_returns_current_user(self, authed_client):
        resp = authed_client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@otsentinel.com"

    def test_me_without_token_returns_403(self, api_client):
        resp = api_client.get("/api/auth/me")
        assert resp.status_code == 403


class TestDevices:
    def test_list_devices_without_auth_returns_403(self, api_client):
        resp = api_client.get("/api/devices")
        assert resp.status_code == 403

    def test_list_devices_with_auth_returns_list(self, authed_client):
        resp = authed_client.get("/api/devices")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_device_not_found(self, authed_client):
        resp = authed_client.get("/api/devices/nonexistent-device-id")
        assert resp.status_code == 404


class TestIncidents:
    def test_list_incidents_without_auth_returns_403(self, api_client):
        resp = api_client.get("/api/incidents")
        assert resp.status_code == 403

    def test_list_incidents_with_auth_returns_list(self, authed_client):
        resp = authed_client.get("/api/incidents")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestDashboard:
    def test_summary_without_auth_returns_403(self, api_client):
        resp = api_client.get("/api/dashboard/summary")
        assert resp.status_code == 403

    def test_summary_with_auth_returns_summary(self, authed_client):
        resp = authed_client.get("/api/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_devices" in data
        assert "active_incidents" in data
        assert "avg_risk_score" in data
        assert "recent_incidents" in data


class TestAudit:
    def test_audit_log_requires_admin(self, authed_client):
        resp = authed_client.get("/api/audit")
        assert resp.status_code == 200

    def test_audit_log_without_auth_returns_403(self, api_client):
        resp = api_client.get("/api/audit")
        assert resp.status_code == 403
