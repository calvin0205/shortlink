from datetime import datetime, timezone
from uuid import uuid4

from ..config import settings
from .base import get_resource


def _table():
    return get_resource().Table(settings.audit_table)


def list_audit_logs(limit: int = 50) -> list:
    resp = _table().scan()
    items = resp.get("Items", [])
    items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return items[:limit]


def create_audit_log(
    user_id: str,
    user_email: str,
    action: str,
    resource_type: str,
    resource_id: str,
    detail: str,
    ip_address: str,
) -> dict:
    log_id = str(uuid4())
    item = {
        "PK": f"LOG#{log_id}",
        "log_id": log_id,
        "user_id": user_id,
        "user_email": user_email,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "detail": detail,
        "ip_address": ip_address,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _table().put_item(Item=item)
    return item
