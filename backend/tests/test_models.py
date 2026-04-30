"""Unit tests for Pydantic models."""
import pytest
from pydantic import ValidationError

from app.models.auth import LoginRequest, TokenResponse
from app.models.device import DeviceResponse
from app.models.incident import IncidentResponse
from app.models.audit import AuditLogResponse


class TestLoginRequest:
    def test_valid_login_request(self):
        req = LoginRequest(email="user@example.com", password="secret123")
        assert req.email == "user@example.com"
        assert req.password == "secret123"

    def test_missing_email_raises(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="secret123")

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com")


class TestTokenResponse:
    def test_defaults_to_bearer(self):
        resp = TokenResponse(access_token="tok123", user={"user_id": "u1"})
        assert resp.token_type == "bearer"


class TestDeviceResponse:
    def test_valid_device(self):
        device = DeviceResponse(
            device_id="d1",
            name="PLC-001",
            type="PLC",
            site_id="site-a",
            site_name="Site Alpha",
            status="online",
            ip_address="192.168.10.1",
            firmware_version="v2.1.0",
            last_seen="2026-04-30T00:00:00Z",
            risk_score=15,
        )
        assert device.device_id == "d1"
        assert device.risk_score == 15

    def test_risk_score_defaults_to_zero(self):
        device = DeviceResponse(
            device_id="d1",
            name="PLC-001",
            type="PLC",
            site_id="site-a",
            site_name="Site Alpha",
            status="online",
            ip_address="192.168.10.1",
            firmware_version="v2.1.0",
            last_seen="2026-04-30T00:00:00Z",
        )
        assert device.risk_score == 0


class TestIncidentResponse:
    def test_valid_incident(self):
        incident = IncidentResponse(
            incident_id="i1",
            device_id="d1",
            device_name="PLC-001",
            severity="critical",
            status="open",
            title="Unauthorized access attempt",
            description="Multiple failed login attempts detected",
            risk_score=85,
            created_at="2026-04-30T00:00:00Z",
        )
        assert incident.incident_id == "i1"
        assert incident.resolved_at is None

    def test_optional_resolved_at(self):
        incident = IncidentResponse(
            incident_id="i1",
            device_id="d1",
            device_name="PLC-001",
            severity="low",
            status="resolved",
            title="Minor alert",
            description="Resolved alert",
            risk_score=10,
            created_at="2026-04-30T00:00:00Z",
            resolved_at="2026-04-30T01:00:00Z",
        )
        assert incident.resolved_at == "2026-04-30T01:00:00Z"
