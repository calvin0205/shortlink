from datetime import datetime, timezone
from typing import Optional

from boto3.dynamodb.conditions import Key

from ..config import settings
from .base import get_resource


def _table():
    return get_resource().Table(settings.users_table)


def get_user_by_email(email: str) -> Optional[dict]:
    resp = _table().query(
        IndexName="email-index",
        KeyConditionExpression=Key("email").eq(email),
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def get_user_by_id(user_id: str) -> Optional[dict]:
    resp = _table().get_item(Key={"PK": f"USER#{user_id}"})
    return resp.get("Item")


def create_user(user_id: str, email: str, password_hash: str, role: str, name: str) -> dict:
    item = {
        "PK": f"USER#{user_id}",
        "user_id": user_id,
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _table().put_item(Item=item)
    return item
