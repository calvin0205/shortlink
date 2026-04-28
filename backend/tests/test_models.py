"""Unit tests for Pydantic request/response models."""
import pytest
from pydantic import ValidationError

from app.models import CreateLinkRequest


class TestCreateLinkRequest:
    def test_valid_http_url(self):
        req = CreateLinkRequest(url="https://example.com")
        assert str(req.url) == "https://example.com/"

    def test_rejects_non_url(self):
        with pytest.raises(ValidationError):
            CreateLinkRequest(url="not-a-url")

    def test_custom_code_alphanumeric(self):
        req = CreateLinkRequest(url="https://example.com", custom_code="abc123")
        assert req.custom_code == "abc123"

    def test_custom_code_too_short(self):
        with pytest.raises(ValidationError):
            CreateLinkRequest(url="https://example.com", custom_code="ab")

    def test_custom_code_too_long(self):
        with pytest.raises(ValidationError):
            CreateLinkRequest(url="https://example.com", custom_code="a" * 21)

    def test_custom_code_special_chars(self):
        with pytest.raises(ValidationError):
            CreateLinkRequest(url="https://example.com", custom_code="bad-code")

    def test_no_custom_code_is_fine(self):
        req = CreateLinkRequest(url="https://example.com")
        assert req.custom_code is None
