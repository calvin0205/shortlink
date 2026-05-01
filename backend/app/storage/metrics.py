from datetime import datetime, timedelta, timezone

from boto3.dynamodb.conditions import Key

from ..config import settings
from .base import get_resource


def _table():
    return get_resource().Table(settings.metrics_table)


def record_metric(
    device_id: str,
    ts: str,
    cpu_pct: float,
    mem_pct: float,
    temp_c: float,
    net_in_kbps: float,
    net_out_kbps: float,
    risk_score: int,
) -> None:
    """Write one metric sample for a device."""
    # TTL: 7 days from now
    ttl = int(
        (datetime.now(timezone.utc) + timedelta(days=7)).timestamp()
    )
    _table().put_item(
        Item={
            "PK": f"DEVICE#{device_id}",
            "ts": ts,
            "cpu_pct": str(cpu_pct),
            "mem_pct": str(mem_pct),
            "temp_c": str(temp_c),
            "net_in_kbps": str(net_in_kbps),
            "net_out_kbps": str(net_out_kbps),
            "risk_score": risk_score,
            "ttl": ttl,
        }
    )


def get_recent_metrics(device_id: str, n: int = 30) -> list[dict]:
    """Return the most recent *n* metric readings for SPC baseline calculation.

    Queries newest-first (ScanIndexForward=False) then reverses the result so
    the returned list is chronological (oldest first) for baseline calculation.
    """
    resp = _table().query(
        KeyConditionExpression=Key("PK").eq(f"DEVICE#{device_id}"),
        ScanIndexForward=False,  # newest first
        Limit=n,
    )
    items = resp.get("Items", [])

    result = []
    for item in items:
        result.append(
            {
                "ts": item["ts"],
                "cpu_pct": float(item["cpu_pct"]),
                "mem_pct": float(item["mem_pct"]),
                "temp_c": float(item["temp_c"]),
                "net_in_kbps": float(item["net_in_kbps"]),
                "net_out_kbps": float(item["net_out_kbps"]),
                "risk_score": float(item["risk_score"]),
            }
        )

    # Reverse so the list is chronological (oldest → newest)
    result.reverse()
    return result


def get_device_metrics(device_id: str, hours: int = 24) -> list[dict]:
    """
    Return metric samples for *device_id* from the last *hours* hours,
    sorted ascending by timestamp.
    """
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    since_iso = since.isoformat()
    now_iso = now.isoformat()

    resp = _table().query(
        KeyConditionExpression=(
            Key("PK").eq(f"DEVICE#{device_id}")
            & Key("ts").between(since_iso, now_iso)
        ),
        ScanIndexForward=True,  # ascending by SK
    )
    items = resp.get("Items", [])

    # Coerce Decimal/string numeric fields back to float for JSON serialisation
    result = []
    for item in items:
        result.append(
            {
                "ts": item["ts"],
                "cpu_pct": float(item["cpu_pct"]),
                "mem_pct": float(item["mem_pct"]),
                "temp_c": float(item["temp_c"]),
                "net_in_kbps": float(item["net_in_kbps"]),
                "net_out_kbps": float(item["net_out_kbps"]),
                "risk_score": int(item["risk_score"]),
            }
        )
    return result
