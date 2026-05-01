"""
simulator.py — OT Sentinel device heartbeat simulation.

Called by EventBridge on a 5-minute schedule. Scans all devices and:
  - Updates last_seen for non-offline devices
  - Applies small random risk_score drift (±5, clamped [5, 95])
  - Applies probabilistic status transitions
  - Creates incidents when a device degrades to a worse status
  - Writes a single audit log entry summarising the tick
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any

from .config import settings
from .risk_engine import ANOMALY_TYPES, DEVICE_MULTIPLIERS
from .storage.base import get_resource
from .storage.metrics import record_metric

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status ordering — higher index = worse state
# ---------------------------------------------------------------------------
STATUS_ORDER: dict[str, int] = {
    "online": 0,
    "warning": 1,
    "critical": 2,
    "offline": 3,
}


def _is_degradation(old_status: str, new_status: str) -> bool:
    return STATUS_ORDER.get(new_status, -1) > STATUS_ORDER.get(old_status, -1)


# ---------------------------------------------------------------------------
# Anomaly-type pools per transition
# ---------------------------------------------------------------------------
_TRANSITION_ANOMALIES: dict[tuple[str, str], list[str]] = {
    ("online", "warning"): [
        "protocol_anomaly",
        "unusual_traffic",
        "comm_timeout",
        "network_scan",
    ],
    ("warning", "critical"): [
        "unauthorized_access",
        "brute_force",
        "firmware_tamper",
        "sensor_manipulation",
    ],
}


def _pick_anomaly(old_status: str, new_status: str) -> str:
    pool = _TRANSITION_ANOMALIES.get((old_status, new_status))
    if pool:
        return random.choice(pool)
    return random.choice(list(ANOMALY_TYPES.keys()))


# ---------------------------------------------------------------------------
# Severity from risk score
# ---------------------------------------------------------------------------
def _severity_from_score(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Full table scan (handles pagination)
# ---------------------------------------------------------------------------
def _scan_all(table) -> list[dict]:
    items: list[dict] = []
    kwargs: dict[str, Any] = {}
    while True:
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        last = response.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    return items


# ---------------------------------------------------------------------------
# Core heartbeat logic
# ---------------------------------------------------------------------------
def run_heartbeat() -> dict:
    """
    Execute one simulation tick for all devices.

    Returns
    -------
    dict
        {"updated": <int>, "incidents_created": <int>}
    """
    dynamodb = get_resource()
    devices_table = dynamodb.Table(settings.devices_table)
    incidents_table = dynamodb.Table(settings.incidents_table)
    audit_table = dynamodb.Table(settings.audit_table)

    now_iso = datetime.now(timezone.utc).isoformat()

    # Scan all device items (PK starts with "DEVICE#")
    all_items = _scan_all(devices_table)
    devices = [item for item in all_items if item.get("PK", "").startswith("DEVICE#")]

    updated_count = 0
    incidents_created = 0

    for device in devices:
        pk: str = device["PK"]
        device_id: str = pk.replace("DEVICE#", "", 1)
        device_name: str = device.get("name", device_id)
        device_type: str = device.get("type", "Sensor")
        old_status: str = device.get("status", "online")
        current_risk: int = int(device.get("risk_score", 50))

        # ── risk score drift ±5, clamped to [5, 95] ──────────────────────────
        drift = random.randint(-5, 5)
        new_risk = max(5, min(95, current_risk + drift))

        # ── status transition ─────────────────────────────────────────────────
        new_status = old_status
        roll = random.random()

        if old_status == "online":
            if roll < 0.04:
                new_status = "warning"
        elif old_status == "warning":
            if roll < 0.15:
                new_status = "online"           # recovery
            elif roll < 0.18:
                new_status = "critical"         # degradation
        elif old_status == "critical":
            if roll < 0.10:
                new_status = "warning"          # partial recovery
        elif old_status == "offline":
            if roll < 0.05:
                new_status = "online"           # device comes back

        # ── build UpdateExpression (alias all names to avoid reserved words) ──
        update_parts = ["#rs = :risk_score"]
        expr_names: dict[str, str] = {"#rs": "risk_score"}
        expr_values: dict[str, Any] = {":risk_score": new_risk}

        if old_status != "offline":
            update_parts.append("#ls = :last_seen")
            expr_names["#ls"] = "last_seen"
            expr_values[":last_seen"] = now_iso

        if new_status != old_status:
            update_parts.append("#st = :status")
            expr_names["#st"] = "status"
            expr_values[":status"] = new_status

        try:
            devices_table.update_item(
                Key={"PK": pk},
                UpdateExpression="SET " + ", ".join(update_parts),
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
            updated_count += 1
        except Exception:
            logger.exception("Failed to update device %s", device_id)
            continue

        # ── record telemetry metrics ──────────────────────────────────────────
        try:
            # Baseline ranges vary by status
            if new_status == "critical":
                cpu_base   = random.uniform(60, 80)
                mem_base   = random.uniform(50, 70)
                temp_base  = random.uniform(55, 75)
                net_in     = random.uniform(200, 1200)
                net_out    = random.uniform(100, 600)
            elif new_status == "warning":
                cpu_base   = random.uniform(40, 60)
                mem_base   = random.uniform(40, 60)
                temp_base  = random.uniform(45, 65)
                net_in     = random.uniform(100, 800)
                net_out    = random.uniform(50, 400)
            else:  # online / offline
                cpu_base   = random.uniform(20, 40)
                mem_base   = random.uniform(30, 50)
                temp_base  = random.uniform(35, 55)
                net_in     = random.uniform(50, 500)
                net_out    = random.uniform(20, 200)

            cpu_pct  = max(0.0, min(100.0, cpu_base  + random.uniform(-10, 10)))
            mem_pct  = max(0.0, min(100.0, mem_base  + random.uniform(-8,  8)))
            temp_c   = max(20.0, min(95.0, temp_base + random.uniform(-5,  5)))

            record_metric(
                device_id=device_id,
                ts=now_iso,
                cpu_pct=round(cpu_pct, 1),
                mem_pct=round(mem_pct, 1),
                temp_c=round(temp_c, 1),
                net_in_kbps=round(net_in, 1),
                net_out_kbps=round(net_out, 1),
                risk_score=new_risk,
            )
        except Exception:
            logger.exception("Failed to record metrics for device %s", device_id)

        # ── create incident on degradation ────────────────────────────────────
        if _is_degradation(old_status, new_status):
            anomaly_type = _pick_anomaly(old_status, new_status)
            anomaly_meta = ANOMALY_TYPES.get(anomaly_type)
            if anomaly_meta is None:
                continue

            _base_min, _base_max, title_tmpl, desc_tmpl = anomaly_meta
            multiplier = DEVICE_MULTIPLIERS.get(device_type, 1.0)
            incident_risk = min(100, int(new_risk * multiplier))
            severity = _severity_from_score(incident_risk)
            description = desc_tmpl.format(device_name=device_name)

            incident_id = str(uuid.uuid4())
            try:
                incidents_table.put_item(
                    Item={
                        "PK": f"INCIDENT#{incident_id}",
                        "incident_id": incident_id,
                        "device_id": device_id,
                        "device_name": device_name,
                        "severity": severity,
                        "status": "open",
                        "title": title_tmpl,
                        "description": f"[Auto-detected] {description}",
                        "risk_score": incident_risk,
                        "anomaly_type": anomaly_type,
                        "created_at": now_iso,
                        "resolved_at": None,
                        "source": "heartbeat",
                    }
                )
                incidents_created += 1
                logger.info(
                    "Incident created: device=%s %s→%s anomaly=%s sev=%s",
                    device_name, old_status, new_status, anomaly_type, severity,
                )
            except Exception:
                logger.exception("Failed to create incident for device %s", device_id)

    # ── audit log entry ───────────────────────────────────────────────────────
    log_id = str(uuid.uuid4())
    try:
        audit_table.put_item(
            Item={
                "PK": f"LOG#{log_id}",
                "log_id": log_id,
                "user_id": "SYSTEM",
                "user_email": "system@otsentinel",
                "action": "HEARTBEAT_TICK",
                "resource_type": "system",
                "resource_id": "scheduler",
                "detail": (
                    f"Heartbeat tick: {len(devices)} devices scanned, "
                    f"{updated_count} updated, {incidents_created} incidents created"
                ),
                "ip_address": "internal",
                "timestamp": now_iso,
            }
        )
    except Exception:
        logger.exception("Failed to write audit log for heartbeat tick")

    logger.info(
        "Heartbeat tick complete: updated=%d incidents_created=%d",
        updated_count,
        incidents_created,
    )
    return {"updated": updated_count, "incidents_created": incidents_created}
