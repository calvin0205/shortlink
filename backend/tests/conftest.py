"""
Shared pytest fixtures for OT Sentinel tests.

moto intercepts all boto3 calls so tests never touch real AWS.
All DynamoDB tables are recreated fresh for every test function.
"""
import os

import boto3
import pytest
from moto import mock_aws

# Point boto3 at fake AWS before any app code imports it
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("USERS_TABLE", "otsentinel-prod-users")
os.environ.setdefault("DEVICES_TABLE", "otsentinel-prod-devices")
os.environ.setdefault("INCIDENTS_TABLE", "otsentinel-prod-incidents")
os.environ.setdefault("AUDIT_TABLE", "otsentinel-prod-audit")
os.environ.setdefault("JWT_SECRET", "test-secret")


@pytest.fixture()
def aws():
    """Activate moto mock for the duration of one test."""
    with mock_aws():
        yield


@pytest.fixture()
def dynamo_tables(aws):
    """Create all four DynamoDB tables inside the moto context."""
    client = boto3.client("dynamodb", region_name="ap-northeast-1")

    # Users table
    client.create_table(
        TableName="otsentinel-prod-users",
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": "email-index",
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )

    # Devices table
    client.create_table(
        TableName="otsentinel-prod-devices",
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
            {"AttributeName": "last_seen", "AttributeType": "S"},
            {"AttributeName": "site_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": "status-index",
                "KeySchema": [
                    {"AttributeName": "status", "KeyType": "HASH"},
                    {"AttributeName": "last_seen", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "site-index",
                "KeySchema": [
                    {"AttributeName": "site_id", "KeyType": "HASH"},
                    {"AttributeName": "PK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    )

    # Incidents table
    client.create_table(
        TableName="otsentinel-prod-incidents",
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "device_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
            {"AttributeName": "severity", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": "device-index",
                "KeySchema": [
                    {"AttributeName": "device_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "severity-index",
                "KeySchema": [
                    {"AttributeName": "severity", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    )

    # Audit table
    client.create_table(
        TableName="otsentinel-prod-audit",
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "timestamp", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": "user-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "timestamp", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    yield


@pytest.fixture()
def seeded_user(dynamo_tables):
    """Create an admin user in the users table and return credentials."""
    from app.auth import hash_password
    from app.storage.users import create_user
    import uuid

    user_id = str(uuid.uuid4())
    create_user(
        user_id=user_id,
        email="admin@otsentinel.com",
        password_hash=hash_password("Admin1234!"),
        role="admin",
        name="Admin User",
    )
    return {
        "user_id": user_id,
        "email": "admin@otsentinel.com",
        "password": "Admin1234!",
        "role": "admin",
    }


@pytest.fixture()
def api_client(dynamo_tables):
    """TestClient wired to the FastAPI app with DynamoDB ready."""
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture()
def authed_client(seeded_user):
    """TestClient with a valid JWT token pre-injected."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import create_access_token

    token = create_access_token({
        "sub": seeded_user["user_id"],
        "email": seeded_user["email"],
        "role": seeded_user["role"],
    })
    client = TestClient(app, raise_server_exceptions=True)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
