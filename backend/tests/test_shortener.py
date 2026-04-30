"""Unit tests for auth utilities (no AWS needed)."""
import pytest

from app.auth import hash_password, verify_password, create_access_token, decode_token
from fastapi import HTTPException


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("MyPassword123!")
        assert verify_password("MyPassword123!", hashed) is True

    def test_wrong_password_fails_verify(self):
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_hash_is_not_plaintext(self):
        hashed = hash_password("plaintext")
        assert hashed != "plaintext"
        assert len(hashed) > 20


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token({"sub": "user-123", "email": "test@example.com"})
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("this.is.not.a.valid.token")
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self):
        token = create_access_token({"sub": "user-123"})
        tampered = token[:-5] + "xxxxx"
        with pytest.raises(HTTPException) as exc_info:
            decode_token(tampered)
        assert exc_info.value.status_code == 401
