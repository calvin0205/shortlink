"""End-to-end API tests via FastAPI TestClient (moto DynamoDB)."""
import pytest


class TestCreateLink:
    def test_creates_short_link(self, api_client):
        resp = api_client.post("/api/links", json={"url": "https://google.com"})
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["code"]) == 7
        assert data["url"] == "https://google.com/"
        assert data["hits"] == 0

    def test_custom_code(self, api_client):
        resp = api_client.post("/api/links", json={"url": "https://github.com", "custom_code": "ghub"})
        assert resp.status_code == 201
        assert resp.json()["code"] == "ghub"

    def test_duplicate_custom_code_returns_409(self, api_client):
        api_client.post("/api/links", json={"url": "https://a.com", "custom_code": "taken"})
        resp = api_client.post("/api/links", json={"url": "https://b.com", "custom_code": "taken"})
        assert resp.status_code == 409

    def test_invalid_url_returns_422(self, api_client):
        resp = api_client.post("/api/links", json={"url": "not-a-url"})
        assert resp.status_code == 422

    def test_custom_code_with_special_chars_returns_422(self, api_client):
        resp = api_client.post("/api/links", json={"url": "https://a.com", "custom_code": "bad code!"})
        assert resp.status_code == 422


class TestRedirect:
    def test_redirects_to_original(self, api_client):
        api_client.post("/api/links", json={"url": "https://example.com", "custom_code": "redir1"})
        resp = api_client.get("/redir1", follow_redirects=False)
        assert resp.status_code == 301
        assert resp.headers["location"] == "https://example.com/"

    def test_missing_code_returns_404(self, api_client):
        resp = api_client.get("/nosuchcode", follow_redirects=False)
        assert resp.status_code == 404

    def test_increments_hit_count(self, api_client):
        api_client.post("/api/links", json={"url": "https://example.com", "custom_code": "hits01"})
        api_client.get("/hits01", follow_redirects=False)
        api_client.get("/hits01", follow_redirects=False)
        stats = api_client.get("/api/links/hits01/stats").json()
        assert stats["hits"] == 2


class TestStats:
    def test_returns_stats(self, api_client):
        api_client.post("/api/links", json={"url": "https://stats.com", "custom_code": "stat01"})
        resp = api_client.get("/api/links/stat01/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "stat01"
        assert "created_at" in data

    def test_missing_returns_404(self, api_client):
        resp = api_client.get("/api/links/ghost99/stats")
        assert resp.status_code == 404
