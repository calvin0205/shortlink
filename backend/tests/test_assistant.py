"""Tests for POST /api/assistant/query and GET /api/assistant/suggested-queries."""
import pytest
from app.storage.incidents import create_incident
from app.storage.audit import list_audit_logs
import uuid


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seed_incident(title="Unauthorized Access Attempt", severity="high", risk_score=75):
    """Create and return an incident dict."""
    incident_id = str(uuid.uuid4())
    return create_incident(
        incident_id=incident_id,
        device_id="device-001",
        device_name="PLC-01",
        severity=severity,
        title=title,
        description="Multiple failed login attempts detected on PLC-01",
        risk_score=risk_score,
    )


# ── POST /api/assistant/query ─────────────────────────────────────────────────

class TestQueryAssistant:

    def test_requires_auth_returns_403(self, api_client):
        """Unauthenticated request should return 403."""
        resp = api_client.post(
            "/api/assistant/query",
            json={"message": "What is firmware tampering?"},
        )
        assert resp.status_code == 403

    def test_valid_query_returns_200(self, authed_client):
        resp = authed_client.post(
            "/api/assistant/query",
            json={"message": "What should I do about unauthorized access?"},
        )
        assert resp.status_code == 200

    def test_response_has_required_fields(self, authed_client):
        resp = authed_client.post(
            "/api/assistant/query",
            json={"message": "Explain firmware tampering"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "recommendations" in data
        assert "references" in data
        assert "source" in data

    def test_source_is_rule_based_without_api_key(self, authed_client):
        """Without ANTHROPIC_API_KEY set, source should be rule-based."""
        resp = authed_client.post(
            "/api/assistant/query",
            json={"message": "How do I handle a brute force attack?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "rule-based"

    def test_recommendations_is_list(self, authed_client):
        resp = authed_client.post(
            "/api/assistant/query",
            json={"message": "How to handle protocol anomaly?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) > 0

    def test_references_is_list(self, authed_client):
        resp = authed_client.post(
            "/api/assistant/query",
            json={"message": "What is network scanning?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["references"], list)

    def test_answer_is_nonempty_string(self, authed_client):
        resp = authed_client.post(
            "/api/assistant/query",
            json={"message": "Tell me about sensor manipulation"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 10

    def test_without_incident_id_context_is_none(self, authed_client):
        resp = authed_client.post(
            "/api/assistant/query",
            json={"message": "General security question"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["incident_context"] is None

    def test_with_valid_incident_id_includes_context(self, authed_client, dynamo_tables):
        incident = _seed_incident()
        resp = authed_client.post(
            "/api/assistant/query",
            json={
                "message": "Analyze this incident",
                "incident_id": incident["incident_id"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["incident_context"] is not None
        ctx = data["incident_context"]
        assert ctx["incident_id"] == incident["incident_id"]
        assert ctx["title"] == incident["title"]
        assert ctx["severity"] == incident["severity"]
        assert ctx["device_name"] == incident["device_name"]
        assert ctx["risk_score"] == incident["risk_score"]
        assert ctx["status"] == incident["status"]

    def test_with_nonexistent_incident_id_still_responds(self, authed_client):
        """If incident_id not found, query still returns a valid response (no crash)."""
        resp = authed_client.post(
            "/api/assistant/query",
            json={
                "message": "Analyze this incident",
                "incident_id": "nonexistent-id-00000",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data

    def test_incident_context_has_correct_risk_score(self, authed_client, dynamo_tables):
        incident = _seed_incident(risk_score=92)
        resp = authed_client.post(
            "/api/assistant/query",
            json={
                "message": "What is the risk for this incident?",
                "incident_id": incident["incident_id"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["incident_context"]["risk_score"] == 92

    def test_query_creates_audit_log(self, authed_client, dynamo_tables):
        """Each query should create an audit log entry."""
        authed_client.post(
            "/api/assistant/query",
            json={"message": "Audit log test query for assistant"},
        )
        logs = list_audit_logs(limit=50)
        ai_logs = [l for l in logs if l.get("action") == "AI_QUERY"]
        assert len(ai_logs) >= 1

    def test_audit_log_records_query_message(self, authed_client, dynamo_tables):
        unique_msg = "unique-test-query-" + str(uuid.uuid4())[:8]
        authed_client.post(
            "/api/assistant/query",
            json={"message": unique_msg},
        )
        logs = list_audit_logs(limit=100)
        matching = [l for l in logs if unique_msg[:50] in l.get("detail", "")]
        assert len(matching) >= 1

    def test_audit_log_resource_type_is_assistant(self, authed_client, dynamo_tables):
        authed_client.post(
            "/api/assistant/query",
            json={"message": "Test resource type in audit"},
        )
        logs = list_audit_logs(limit=50)
        ai_logs = [l for l in logs if l.get("action") == "AI_QUERY"]
        assert any(l.get("resource_type") == "ASSISTANT" for l in ai_logs)

    def test_empty_message_returns_422(self, authed_client):
        """Empty/missing message field should fail validation."""
        resp = authed_client.post(
            "/api/assistant/query",
            json={},
        )
        assert resp.status_code == 422

    def test_incident_id_none_is_valid(self, authed_client):
        resp = authed_client.post(
            "/api/assistant/query",
            json={"message": "test query", "incident_id": None},
        )
        assert resp.status_code == 200


# ── GET /api/assistant/suggested-queries ─────────────────────────────────────

class TestSuggestedQueries:

    def test_requires_auth_returns_403(self, api_client):
        resp = api_client.get("/api/assistant/suggested-queries")
        assert resp.status_code == 403

    def test_returns_200(self, authed_client):
        resp = authed_client.get("/api/assistant/suggested-queries")
        assert resp.status_code == 200

    def test_response_has_queries_key(self, authed_client):
        resp = authed_client.get("/api/assistant/suggested-queries")
        data = resp.json()
        assert "queries" in data

    def test_queries_is_nonempty_list(self, authed_client):
        resp = authed_client.get("/api/assistant/suggested-queries")
        data = resp.json()
        assert isinstance(data["queries"], list)
        assert len(data["queries"]) > 0

    def test_queries_are_strings(self, authed_client):
        resp = authed_client.get("/api/assistant/suggested-queries")
        data = resp.json()
        for q in data["queries"]:
            assert isinstance(q, str)
            assert len(q) > 0

    def test_queries_cover_key_topics(self, authed_client):
        """Suggested queries should mention at least firmware, protocol, and brute force."""
        resp = authed_client.get("/api/assistant/suggested-queries")
        data = resp.json()
        combined = " ".join(data["queries"]).lower()
        assert "firmware" in combined
        assert "protocol" in combined or "brute" in combined
