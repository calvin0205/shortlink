"""Integration tests for DynamoDB storage layer (moto)."""
import uuid
import pytest

from app.auth import hash_password
from app.storage.users import create_user, get_user_by_email, get_user_by_id
from app.storage.devices import list_devices, get_device
from app.storage.incidents import list_incidents, get_incident
from app.storage.audit import create_audit_log, list_audit_logs


class TestUsersStorage:
    def test_create_and_get_user_by_email(self, dynamo_tables):
        user_id = str(uuid.uuid4())
        create_user(user_id, "test@example.com", hash_password("pass"), "admin", "Test User")
        user = get_user_by_email("test@example.com")
        assert user is not None
        assert user["email"] == "test@example.com"
        assert user["role"] == "admin"

    def test_get_user_by_id(self, dynamo_tables):
        user_id = str(uuid.uuid4())
        create_user(user_id, "test2@example.com", hash_password("pass"), "operator", "Ops User")
        user = get_user_by_id(user_id)
        assert user is not None
        assert user["user_id"] == user_id

    def test_missing_user_returns_none(self, dynamo_tables):
        assert get_user_by_email("nobody@example.com") is None
        assert get_user_by_id("nonexistent-id") is None


class TestDevicesStorage:
    def test_list_devices_empty(self, dynamo_tables):
        devices = list_devices()
        assert devices == []

    def test_get_device_not_found(self, dynamo_tables):
        device = get_device("nonexistent")
        assert device is None


class TestIncidentsStorage:
    def test_list_incidents_empty(self, dynamo_tables):
        incidents = list_incidents()
        assert incidents == []

    def test_get_incident_not_found(self, dynamo_tables):
        incident = get_incident("nonexistent")
        assert incident is None


class TestAuditStorage:
    def test_create_and_list_audit_log(self, dynamo_tables):
        log = create_audit_log(
            user_id="user-123",
            user_email="admin@example.com",
            action="LOGIN",
            resource_type="AUTH",
            resource_id="session-1",
            detail="User logged in",
            ip_address="127.0.0.1",
        )
        assert log["action"] == "LOGIN"
        assert "log_id" in log
        assert "timestamp" in log

        logs = list_audit_logs()
        assert len(logs) == 1
        assert logs[0]["action"] == "LOGIN"

    def test_audit_log_sorted_by_timestamp_desc(self, dynamo_tables):
        for i in range(3):
            create_audit_log(
                user_id=f"user-{i}",
                user_email=f"user{i}@example.com",
                action="VIEW_DEVICE",
                resource_type="DEVICE",
                resource_id=f"device-{i}",
                detail=f"Viewed device {i}",
                ip_address="10.0.0.1",
            )
        logs = list_audit_logs()
        assert len(logs) == 3
        timestamps = [log["timestamp"] for log in logs]
        assert timestamps == sorted(timestamps, reverse=True)
