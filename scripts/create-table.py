"""Create the DynamoDB Local table. Run before starting the dev server."""
import sys
import boto3
from botocore.exceptions import ClientError

ENDPOINT = "http://localhost:8001"
TABLE    = "shortlink-links"
REGION   = "ap-northeast-1"

dynamo = boto3.client(
    "dynamodb",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="local",
    aws_secret_access_key="local",
)

try:
    dynamo.create_table(
        TableName=TABLE,
        KeySchema=[{"AttributeName": "code", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "code", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    print(f"Table '{TABLE}' created.")
except ClientError as e:
    if e.response["Error"]["Code"] == "ResourceInUseException":
        print(f"Table '{TABLE}' already exists, skipping.")
    else:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
