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
