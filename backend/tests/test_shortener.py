"""Unit tests for the code-generation logic (no AWS needed)."""
import string

import pytest

from app.shortener import generate_code, is_valid_url

VALID_CHARS = set(string.ascii_letters + string.digits)


class TestGenerateCode:
    def test_default_length(self):
        assert len(generate_code()) == 7

    def test_custom_length(self):
        assert len(generate_code(length=12)) == 12

    def test_only_alphanumeric(self):
        for _ in range(200):
            code = generate_code()
            assert set(code).issubset(VALID_CHARS), f"Non-alphanumeric char in {code!r}"

    def test_randomness(self):
        # Probability of collision in 1000 draws from 62^7 space ≈ 0
        codes = {generate_code() for _ in range(1000)}
        assert len(codes) > 990

    def test_minimum_length_one(self):
        assert len(generate_code(length=1)) == 1


class TestIsValidUrl:
    @pytest.mark.parametrize("url", [
        "https://example.com",
        "http://example.com/path?q=1",
        "https://sub.domain.io:8080/a/b",
    ])
    def test_valid_urls(self, url):
        assert is_valid_url(url) is True

    @pytest.mark.parametrize("url", [
        "ftp://example.com",
        "example.com",
        "",
        "javascript:alert(1)",
    ])
    def test_invalid_urls(self, url):
        assert is_valid_url(url) is False
