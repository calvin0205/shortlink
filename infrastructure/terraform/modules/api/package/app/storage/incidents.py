from datetime import datetime, timezone
from typing import Optional

from boto3.dynamodb.conditions import Attr

from ..config import settings
from .base import get_resource


def _table():
    return get_resource().Table(settings.incidents_table)


def list_incidents(severity: str = None, status_filter: str = None) -> list:
    filter_expr = None

    if severity and status_filter:
        filter_expr = Attr("severity").eq(severity) & Attr("status").eq(status_filter)
    elif severity:
        filter_expr = Attr("severity").eq(severity)
    elif status_filter:
        filter_expr = Attr("status").eq(status_filter)

    if filter_expr is not None:
        resp = _table().scan(FilterExpression=filter_expr)
    else:
        resp = _table().scan()

    return resp.get("Items", [])


def get_incident(incident_id: str) -> Optional[dict]:
    resp = _table().get_item(Key={"PK": f"INCIDENT#{incident_id}"})
    return resp.get("Item")


def create_incident(
    incident_id: str,
    device_id: str,
    device_name: str,
    severity: str,
    title: str,
    description: str,
    risk_score: int,
) -> dict:
    """Create a new incident record."""
    item = {
        "PK": f"INCIDENT#{incident_id}",
        "incident_id": incident_id,
        "device_id": device_id,
        "device_name": device_name,
        "severity": severity,
        "status": "open",
        "title": title,
        "description": description,
        "risk_score": risk_score,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
    }
    _table().put_item(Item=item)
    return item


def update_incident(incident_id: str, updates: dict) -> Optional[dict]:
    """Update arbitrary fields on an incident and return the updated item."""
    if not updates:
        return get_incident(incident_id)

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
        Key={"PK": f"INCIDENT#{incident_id}"},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ReturnValues="ALL_NEW",
    )
    return resp.get("Attributes")
