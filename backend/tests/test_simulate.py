"""Tests for the anomaly simulation endpoint."""
import uuid

import pytest


def _seed_device(dynamo_tables, device_id: str = None):
    """Insert a test device directly into DynamoDB."""
    import boto3
    from app.config import settings

    device_id = device_id or str(uuid.uuid4())
    resource = boto3.resource("dynamodb", region_name="ap-northeast-1")
    table = resource.Table(settings.devices_table)
    table.put_item(
        Item={
            "PK": f"DEVICE#{device_id}",
            "device_id": device_id,
            "name": "Test PLC",
            "type": "PLC",
            "status": "online",
            "risk_score": 0,
            "site_id": "site-001",
            "site_name": "Plant A",
            "ip_address": "192.168.1.10",
            "firmware_version": "1.0.0",
            "last_seen": "2026-01-01T00:00:00+00:00",
        }
    )
    return device_id


class TestSimulateEndpoint:
    def test_simulate_creates_incident_and_updates_device(self, authed_client):
        device_id = _seed_device(authed_client.app.state.__dict__.get("_fixtures", {}))
        # Re-seed via dynamo directly since authed_client already has dynamo_tables
        import boto3
        from app.config import settings
        resource = boto3.resource("dynamodb", region_name="ap-northeast-1")
        table = resource.Table(settings.devices_table)
        table.put_item(
            Item={
                "PK": f"DEVICE#{device_id}",
                "device_id": device_id,
                "name": "Test PLC",
                "type": "PLC",
                "status": "online",
                "risk_score": 0,
                "site_id": "site-001",
                "last_seen": "2026-01-01T00:00:00+00:00",
            }
        )

        resp = authed_client.post(
            f"/api/devices/{device_id}/simulate",
            json={"anomaly_type": "unauthorized_access"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["device_id"] == device_id
        assert data["anomaly_type"] == "unauthorized_access"
        assert isinstance(data["risk_score"], int)
        assert data["severity"] in ("critical", "high", "medium", "low")
        assert "incident_id" in data
        assert data["incident_id"]

        # Verify device status updated
        device_resp = authed_client.get(f"/api/devices/{device_id}")
        assert device_resp.status_code == 200
        device = device_resp.json()
        assert device["status"] in ("critical", "warning")

        # Verify incident created
        incident_id = data["incident_id"]
        inc_resp = authed_client.get(f"/api/incidents/{incident_id}")
        assert inc_resp.status_code == 200
        incident = inc_resp.json()
        assert incident["device_id"] == device_id
        assert incident["status"] == "open"

    def test_simulate_with_invalid_anomaly_type_returns_422(self, authed_client):
        import boto3
        from app.config import settings
        device_id = str(uuid.uuid4())
        resource = boto3.resource("dynamodb", region_name="ap-northeast-1")
        table = resource.Table(settings.devices_table)
        table.put_item(
            Item={
                "PK": f"DEVICE#{device_id}",
                "device_id": device_id,
                "name": "Test Device",
                "type": "Sensor",
                "status": "online",
            }
        )

        resp = authed_client.post(
            f"/api/devices/{device_id}/simulate",
            json={"anomaly_type": "not_a_real_anomaly"},
        )
        assert resp.status_code == 422

    def test_simulate_with_unknown_device_returns_404(self, authed_client):
        resp = authed_client.post(
            "/api/devices/does-not-exist/simulate",
            json={"anomaly_type": "unauthorized_access"},
        )
        assert resp.status_code == 404

    def test_simulate_requires_auth(self, api_client, dynamo_tables):
        resp = api_client.post(
            "/api/devices/some-device/simulate",
            json={"anomaly_type": "unauthorized_access"},
        )
        assert resp.status_code == 403

    def test_simulate_high_severity_sets_device_critical(self, authed_client):
        """unauthorized_access on PLC always yields critical severity."""
        import random
        import boto3
        from app.config import settings
        device_id = str(uuid.uuid4())
        resource = boto3.resource("dynamodb", region_name="ap-northeast-1")
        table = resource.Table(settings.devices_table)
        table.put_item(
            Item={
                "PK": f"DEVICE#{device_id}",
                "device_id": device_id,
                "name": "Test PLC",
                "type": "PLC",
                "status": "online",
                "risk_score": 0,
            }
        )

        resp = authed_client.post(
            f"/api/devices/{device_id}/simulate",
            json={"anomaly_type": "unauthorized_access"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # unauthorized_access on PLC always yields >= 80 → critical
        assert data["severity"] == "critical"
        device_resp = authed_client.get(f"/api/devices/{device_id}")
        assert device_resp.json()["status"] == "critical"

    def test_get_anomaly_types_requires_auth(self, api_client, dynamo_tables):
        resp = api_client.get("/api/devices/anomaly-types")
        assert resp.status_code == 403

    def test_get_anomaly_types_returns_list(self, authed_client):
        resp = authed_client.get("/api/devices/anomaly-types")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "value" in data[0]
        assert "label" in data[0]
