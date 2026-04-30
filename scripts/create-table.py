"""
Create all OT Sentinel DynamoDB tables locally.
Run before starting the dev server.

Environment variables (all optional):
    DYNAMODB_ENDPOINT_URL   — default: http://localhost:8001
    USERS_TABLE             — default: otsentinel-prod-users
    DEVICES_TABLE           — default: otsentinel-prod-devices
    INCIDENTS_TABLE         — default: otsentinel-prod-incidents
    AUDIT_TABLE             — default: otsentinel-prod-audit
"""
import os
import sys

import boto3
from botocore.exceptions import ClientError

ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT_URL", "http://localhost:8001")
REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-1")

USERS_TABLE = os.environ.get("USERS_TABLE", "otsentinel-prod-users")
DEVICES_TABLE = os.environ.get("DEVICES_TABLE", "otsentinel-prod-devices")
INCIDENTS_TABLE = os.environ.get("INCIDENTS_TABLE", "otsentinel-prod-incidents")
AUDIT_TABLE = os.environ.get("AUDIT_TABLE", "otsentinel-prod-audit")

dynamo = boto3.client(
    "dynamodb",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="local",
    aws_secret_access_key="local",
)

TABLE_DEFINITIONS = {
    USERS_TABLE: {
        "KeySchema": [{"AttributeName": "PK", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "email-index",
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    },
    DEVICES_TABLE: {
        "KeySchema": [{"AttributeName": "PK", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
            {"AttributeName": "last_seen", "AttributeType": "S"},
            {"AttributeName": "site_id", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
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
    },
    INCIDENTS_TABLE: {
        "KeySchema": [{"AttributeName": "PK", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "device_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
            {"AttributeName": "severity", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
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
    },
    AUDIT_TABLE: {
        "KeySchema": [{"AttributeName": "PK", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "timestamp", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "user-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "timestamp", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    },
}


def main():
    for table_name, schema in TABLE_DEFINITIONS.items():
        try:
            dynamo.create_table(
                TableName=table_name,
                KeySchema=schema["KeySchema"],
                AttributeDefinitions=schema["AttributeDefinitions"],
                BillingMode="PAY_PER_REQUEST",
                GlobalSecondaryIndexes=schema["GlobalSecondaryIndexes"],
            )
            print(f"Table '{table_name}' created.")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                print(f"Table '{table_name}' already exists, skipping.")
            else:
                print(f"Error creating '{table_name}': {e}", file=sys.stderr)
                sys.exit(1)


if __name__ == "__main__":
    main()
