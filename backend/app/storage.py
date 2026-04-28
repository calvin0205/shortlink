from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .config import settings


def _table():
    dynamo = boto3.resource("dynamodb", region_name=settings.aws_region)
    return dynamo.Table(settings.dynamodb_table)


def put_link(code: str, url: str) -> dict:
    item = {
        "code": code,
        "url": url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "hits": 0,
    }
    _table().put_item(Item=item, ConditionExpression="attribute_not_exists(code)")
    return item


def get_link(code: str) -> Optional[dict]:
    resp = _table().get_item(Key={"code": code})
    return resp.get("Item")


def increment_hits(code: str) -> None:
    _table().update_item(
        Key={"code": code},
        UpdateExpression="ADD hits :one",
        ExpressionAttributeValues={":one": 1},
    )


def code_exists(code: str) -> bool:
    return get_link(code) is not None
