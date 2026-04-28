"""Integration tests for DynamoDB storage layer (moto)."""
import pytest
from botocore.exceptions import ClientError

from app.storage import code_exists, get_link, increment_hits, put_link


class TestPutLink:
    def test_creates_item(self, dynamo_table):
        item = put_link("abc1234", "https://example.com")
        assert item["code"] == "abc1234"
        assert item["url"] == "https://example.com"
        assert item["hits"] == 0
        assert "created_at" in item

    def test_duplicate_code_raises(self, dynamo_table):
        put_link("dup0001", "https://a.com")
        with pytest.raises(ClientError) as exc_info:
            put_link("dup0001", "https://b.com")
        assert exc_info.value.response["Error"]["Code"] == "ConditionalCheckFailedException"


class TestGetLink:
    def test_returns_item(self, dynamo_table):
        put_link("get0001", "https://example.com")
        item = get_link("get0001")
        assert item is not None
        assert item["url"] == "https://example.com"

    def test_missing_code_returns_none(self, dynamo_table):
        assert get_link("nope999") is None


class TestIncrementHits:
    def test_increments_counter(self, dynamo_table):
        put_link("hit0001", "https://example.com")
        increment_hits("hit0001")
        increment_hits("hit0001")
        item = get_link("hit0001")
        assert int(item["hits"]) == 2


class TestCodeExists:
    def test_true_when_present(self, dynamo_table):
        put_link("ex00001", "https://example.com")
        assert code_exists("ex00001") is True

    def test_false_when_absent(self, dynamo_table):
        assert code_exists("absent1") is False
