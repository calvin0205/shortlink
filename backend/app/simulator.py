"""
simulator.py — OT Sentinel device heartbeat simulation.

Called by EventBridge on a 5-minute schedule. Scans all devices and:
  - Updates last_seen for non-offline devices
  - Applies small random risk_score drift (±5, clamped [5, 95])
  - Applies probabilistic status transitions
  - Computes recipe-cycle-aware telemetry metrics (running/cooling/idle)
  - Creates incidents when a device degrades to a worse status
  - Runs SPC violation checks and creates SPC incidents (max 1 per field per hour)
  - Writes a single audit log entry summarising the tick
"""

from __future__ import annotations

import hashlib
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from .config import settings
from .health_score import compute_health_score, compute_pm_status
from .risk_engine import ANOMALY_TYPES, DEVICE_MULTIPLIERS
from .spc import calculate_baseline, check_violations
from .storage.base import get_resource
from .storage.metrics import get_recent_metrics, record_metric

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
# Recipe-cycle phase
# ---------------------------------------------------------------------------
def _get_recipe_phase(device_id: str, now: datetime) -> str:
    """
    Return 'running', 'cooling', or 'idle' based on device_id and current time.

    Each device has a unique phase offset (derived from device_id hash) so
    they don't all cycle in sync.

    Cycle: 60 min = running(36 min) + cooling(6 min) + idle(18 min)
    """
    offset = int(hashlib.md5(device_id.encode()).hexdigest(), 16) % 60
    minute = (now.minute + offset) % 60
    if minute < 36:
        return "running"
    elif minute < 42:
        return "cooling"
    else:
        return "idle"


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
    now_dt = datetime.fromisoformat(now_iso)

    # Scan all device items (PK starts with "DEVICE#")
    all_items = _scan_all(devices_table)
    devices = [item for item in all_items if item.get("PK", "").startswith("DEVICE#")]

    updated_count = 0
    incidents_created = 0

    # ------------------------------------------------------------------
    # Build a set of (device_id, spc_field) pairs that already have an
    # open SPC incident created within the last 60 minutes.
    # This prevents SPC incident spam — max 1 per device+field per hour.
    # ------------------------------------------------------------------
    one_hour_ago_iso = (now_dt - timedelta(hours=1)).isoformat()
    recent_spc_incidents: set[tuple[str, str]] = set()
    try:
        # Scan the incidents table for open SPC incidents in the last hour.
        # We filter client-side to avoid a full scan needing a GSI.
        all_incidents = _scan_all(incidents_table)
        for inc in all_incidents:
            if (
                inc.get("source") == "spc"
                and inc.get("status") == "open"
                and inc.get("created_at", "") >= one_hour_ago_iso
            ):
                recent_spc_incidents.add(
                    (inc.get("device_id", ""), inc.get("spc_field", ""))
                )
    except Exception:
        logger.exception("Failed to scan recent SPC incidents; proceeding without spam guard")

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

        # ── PM status and health score recalculation ──────────────────────────
        next_pm_date: str | None = device.get("next_pm_date")
        new_pm_status = compute_pm_status(next_pm_date, now_dt)
        new_health_score = compute_health_score(
            risk_score=new_risk,
            status=new_status,
            pm_status=new_pm_status,
            next_pm_date=next_pm_date,
            now=now_dt,
        )
        # Each heartbeat tick = 5 minutes = 5/60 operating hours (non-offline only)
        _tick_hours: float = 5.0 / 60.0
        current_op_hours: float = float(device.get("operating_hours", 0))
        new_op_hours: float = round(current_op_hours + _tick_hours, 3) if new_status != "offline" else current_op_hours

        # ── build UpdateExpression (alias all names to avoid reserved words) ──
        update_parts = [
            "#rs = :risk_score",
            "#hs = :health_score",
            "#pst = :pm_status",
            "#oh = :operating_hours",
        ]
        expr_names: dict[str, str] = {
            "#rs":  "risk_score",
            "#hs":  "health_score",
            "#pst": "pm_status",
            "#oh":  "operating_hours",
        }
        expr_values: dict[str, Any] = {
            ":risk_score":      new_risk,
            ":health_score":    new_health_score,
            ":pm_status":       new_pm_status,
            ":operating_hours": str(round(new_op_hours, 3)),  # store as String to avoid Decimal issues
        }

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

        # ── record telemetry metrics (recipe-cycle aware) ─────────────────────
        try:
            recipe = _get_recipe_phase(device_id, now_dt)

            # Base ranges from recipe phase
            if recipe == "running":
                cpu_base = random.uniform(55, 80)
                temp_base = random.uniform(58, 75)
                net_in    = random.uniform(200, 800)
                net_out   = random.uniform(100, 400)
            elif recipe == "cooling":
                cpu_base = random.uniform(20, 40)
                temp_base = random.uniform(50, 65)
                net_in    = random.uniform(50, 200)
                net_out   = random.uniform(20, 100)
            else:  # idle
                cpu_base = random.uniform(10, 25)
                temp_base = random.uniform(35, 50)
                net_in    = random.uniform(10, 80)
                net_out   = random.uniform(5, 40)

            # Overlay device status (degraded devices run hotter/harder)
            status_cpu_add  = {"online": 0, "warning": 15, "critical": 30, "offline": -50}.get(new_status, 0)
            status_temp_add = {"online": 0, "warning": 8,  "critical": 18, "offline": -20}.get(new_status, 0)
            status_mem_add  = {"online": 0, "warning": 10, "critical": 20, "offline": -10}.get(new_status, 0)

            cpu_pct = max(0.0, min(100.0, cpu_base + status_cpu_add + random.uniform(-5, 5)))
            mem_pct = max(0.0, min(100.0, random.uniform(35, 55) + status_mem_add + random.uniform(-5, 5)))
            temp_c  = max(20.0, min(95.0, temp_base + status_temp_add + random.uniform(-3, 3)))

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
            # Skip SPC check if we couldn't even record the metric
            cpu_pct = 0.0
            temp_c = 0.0

        # ── SPC violation check ───────────────────────────────────────────────
        try:
            recent = get_recent_metrics(device_id, n=30)
            if len(recent) >= 10:
                current_vals = {
                    "cpu_pct":    cpu_pct,
                    "temp_c":     temp_c,
                    "risk_score": float(new_risk),
                }
                spc_field_map = [
                    ("cpu_pct",    "unusual_traffic"),
                    ("temp_c",     "sensor_manipulation"),
                    ("risk_score", "protocol_anomaly"),
                ]
                for field, anomaly_type in spc_field_map:
                    baseline = calculate_baseline(recent, field)
                    if not check_violations(current_vals, baseline, field):
                        continue

                    # Spam guard: skip if a recent SPC incident already exists
                    if (device_id, field) in recent_spc_incidents:
                        logger.debug(
                            "SPC violation for %s/%s suppressed (recent incident exists)",
                            device_id, field,
                        )
                        continue

                    anomaly_meta = ANOMALY_TYPES.get(anomaly_type)
                    if not anomaly_meta:
                        continue

                    _, _, title_tmpl, desc_tmpl = anomaly_meta
                    multiplier = DEVICE_MULTIPLIERS.get(device_type, 1.0)
                    spc_risk = min(100, int(new_risk * multiplier))
                    spc_severity = _severity_from_score(spc_risk)
                    spc_incident_id = str(uuid.uuid4())

                    try:
                        incidents_table.put_item(
                            Item={
                                "PK": f"INCIDENT#{spc_incident_id}",
                                "incident_id": spc_incident_id,
                                "device_id": device_id,
                                "device_name": device_name,
                                "severity": spc_severity,
                                "status": "open",
                                "title": f"[SPC] {title_tmpl}",
                                "description": (
                                    f"[SPC Out-of-Control] {field} = {current_vals[field]:.1f} "
                                    f"exceeded control limit "
                                    f"(UCL={baseline['ucl']:.1f}, LCL={baseline['lcl']:.1f}). "
                                    f"{desc_tmpl.format(device_name=device_name)}"
                                ),
                                "risk_score": spc_risk,
                                "anomaly_type": anomaly_type,
                                "created_at": now_iso,
                                "resolved_at": None,
                                "source": "spc",
                                "spc_field": field,
                                "spc_value": str(current_vals[field]),
                                "spc_ucl": str(baseline["ucl"]),
                                "spc_lcl": str(baseline["lcl"]),
                            }
                        )
                        incidents_created += 1
                        # Register in local cache so subsequent fields in this
                        # same tick for the same device don't double-fire
                        recent_spc_incidents.add((device_id, field))
                        logger.info(
                            "SPC incident created: device=%s field=%s value=%.1f ucl=%.1f lcl=%.1f",
                            device_name, field, current_vals[field],
                            baseline["ucl"], baseline["lcl"],
                        )
                    except Exception:
                        logger.exception(
                            "Failed to create SPC incident for device %s field %s",
                            device_id, field,
                        )
        except Exception:
            logger.exception("SPC check failed for device %s", device_id)

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
