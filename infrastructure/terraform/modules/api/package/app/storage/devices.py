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


def update_device(device_id: str, updates: dict) -> Optional[dict]:
    """Update arbitrary fields on a device and return the updated item."""
    if not updates:
        return get_device(device_id)

    # Build UpdateExpression dynamically, using aliases to avoid reserved words
    set_parts = []
    expr_names = {}
    expr_values = {}

    for i, (key, value) in enumerate(updates.items()):
        alias = f"#f{i}"
        val_alias = f":v{i}"
        expr_names[alias] = key
        expr_values[val_alias] = value
        set_parts.append(f"{alias} = {val_alias}")

    update_expr = "SET " + ", ".join(set_parts)

    resp = _table().update_item(
        Key={"PK": f"DEVICE#{device_id}"},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ReturnValues="ALL_NEW",
    )
    return resp.get("Attributes")
