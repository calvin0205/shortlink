from typing import Optional

from boto3.dynamodb.conditions import Attr

from ..config import settings
from .base import get_resource


def _table():
    return get_resource().Table(settings.devices_table)


def list_devices(status_filter: str = None) -> list:
    if status_filter:
        resp = _table().scan(FilterExpression=Attr("status").eq(status_filter))
    else:
        resp = _table().scan()
    return resp.get("Items", [])


def get_device(device_id: str) -> Optional[dict]:
    resp = _table().get_item(Key={"PK": f"DEVICE#{device_id}"})
    return resp.get("Item")
