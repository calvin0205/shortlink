"""
Shared pytest fixtures.

moto intercepts all boto3 calls so tests never touch real AWS.
The DynamoDB table is recreated fresh for every test function.
"""
import os

import boto3
import pytest
from moto import mock_aws

# Point boto3 at fake AWS before any app code imports it
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("DYNAMODB_TABLE", "shortlink-links")


@pytest.fixture()
def aws():
    """Activate moto mock for the duration of one test."""
    with mock_aws():
        yield


@pytest.fixture()
def dynamo_table(aws):
    """Create the DynamoDB table inside the moto context."""
    client = boto3.client("dynamodb", region_name="ap-northeast-1")
    client.create_table(
        TableName="shortlink-links",
        KeySchema=[{"AttributeName": "code", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "code", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    yield


@pytest.fixture()
def api_client(dynamo_table):
    """TestClient wired to the FastAPI app with DynamoDB ready."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    import asyncio

    # Use sync TestClient for simplicity
    from fastapi.testclient import TestClient
    return TestClient(app, raise_server_exceptions=True)
