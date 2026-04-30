"""Tests for incident lifecycle — acknowledge and resolve endpoints."""
import uuid

import pytest


def _seed_incident(status: str = "open") -> dict:
    """Insert a test incident directly into DynamoDB."""
    import boto3
    from app.config import settings
    from datetime import datetime, timezone

    incident_id = str(uuid.uuid4())
    device_id = str(uuid.uuid4())
    resource = boto3.resource("dynamodb", region_name="ap-northeast-1")
    table = resource.Table(settings.incidents_table)
    item = {
        "PK": f"INCIDENT#{incident_id}",
        "incident_id": incident_id,
        "device_id": device_id,
        "device_name": "Test PLC",
        "severity": "critical",
        "status": status,
        "title": "Test Incident",
        "description": "Test incident description",
        "risk_score": 90,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
    }
    table.put_item(Item=item)
    return item


def _seed_device(device_id: str):
    """Insert a test device into DynamoDB."""
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
            "status": "critical",
            "risk_score": 90,
        }
    )


class TestAcknowledgeIncident:
    def test_acknowledge_open_incident_changes_status_to_investigating(self, authed_client):
        incident = _seed_incident(status="open")
        incident_id = incident["incident_id"]

        resp = authed_client.post(
            f"/api/incidents/{incident_id}/acknowledge",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "investigating"
        assert "acknowledged_at" in data

    def test_acknowledge_resolved_incident_returns_400(self, authed_client):
        incident = _seed_incident(status="resolved")
        incident_id = incident["incident_id"]

        resp = authed_client.post(
            f"/api/incidents/{incident_id}/acknowledge",
            json={},
        )
        assert resp.status_code == 400
        assert "resolved" in resp.json()["detail"].lower()

    def test_acknowledge_nonexistent_incident_returns_404(self, authed_client):
        resp = authed_client.post(
            "/api/incidents/does-not-exist/acknowledge",
            json={},
        )
        assert resp.status_code == 404

    def test_acknowledge_requires_auth(self, api_client, dynamo_tables):
        resp = api_client.post(
            "/api/incidents/some-id/acknowledge",
            json={},
        )
        assert resp.status_code == 403

    def test_acknowledge_returns_full_incident(self, authed_client):
        incident = _seed_incident(status="open")
        incident_id = incident["incident_id"]

        resp = authed_client.post(
            f"/api/incidents/{incident_id}/acknowledge",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should contain all incident fields
        assert "incident_id" in data
        assert "device_id" in data
        assert "severity" in data
        assert "title" in data


class TestResolveIncident:
    def test_resolve_incident_changes_status_to_resolved(self, authed_client):
        incident = _seed_incident(status="open")
        incident_id = incident["incident_id"]

        resp = authed_client.post(
            f"/api/incidents/{incident_id}/resolve",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "resolved"
        assert data.get("resolved_at") is not None

    def test_resolve_investigating_incident_works(self, authed_client):
        incident = _seed_incident(status="investigating")
        incident_id = incident["incident_id"]

        resp = authed_client.post(
            f"/api/incidents/{incident_id}/resolve",
            json={},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    def test_resolve_updates_device_status_to_online(self, authed_client):
        incident = _seed_incident(status="open")
        incident_id = incident["incident_id"]
        device_id = incident["device_id"]
        _seed_device(device_id)

        resp = authed_client.post(
            f"/api/incidents/{incident_id}/resolve",
            json={},
        )
        assert resp.status_code == 200

        device_resp = authed_client.get(f"/api/devices/{device_id}")
        assert device_resp.status_code == 200
        assert device_resp.json()["status"] == "online"

    def test_resolve_nonexistent_incident_returns_404(self, authed_client):
        resp = authed_client.post(
            "/api/incidents/does-not-exist/resolve",
            json={},
        )
        assert resp.status_code == 404

    def test_resolve_requires_auth(self, api_client, dynamo_tables):
        resp = api_client.post(
            "/api/incidents/some-id/resolve",
            json={},
        )
        assert resp.status_code == 403

    def test_resolve_returns_full_incident(self, authed_client):
        incident = _seed_incident(status="open")
        incident_id = incident["incident_id"]

        resp = authed_client.post(
            f"/api/incidents/{incident_id}/resolve",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "incident_id" in data
        assert "device_id" in data
        assert "severity" in data
