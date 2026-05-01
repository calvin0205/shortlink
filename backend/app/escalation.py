"""
escalation.py — OT Sentinel alert escalation.

Runs every heartbeat tick. Scans open incidents and sends SNS email
notifications when high/critical incidents go unacknowledged too long.

Escalation thresholds:
  L1 — Critical: open > 15 min without acknowledgement
  L1 — High:     open > 30 min without acknowledgement
  L2 — Critical: open > 45 min (still unresolved after L1)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3

from .config import settings
from .storage.base import get_resource

logger = logging.getLogger(__name__)

# Thresholds (minutes)
L1_CRITICAL_MIN = 15
L1_HIGH_MIN     = 30
L2_CRITICAL_MIN = 45


def _sns_client():
    return boto3.client("sns", region_name=settings.aws_region)


def _scan_open_incidents(table) -> list[dict]:
    items: list[dict] = []
    kwargs: dict[str, Any] = {}
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        last = resp.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    return [i for i in items if i.get("PK", "").startswith("INCIDENT#")
            and i.get("status") in ("open", "investigating")]


def _minutes_open(incident: dict, now: datetime) -> float:
    created = incident.get("created_at", "")
    if not created:
        return 0.0
    try:
        dt = datetime.fromisoformat(created)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).total_seconds() / 60
    except ValueError:
        return 0.0


def _send_alert(subject: str, message: str) -> None:
    if not settings.sns_topic_arn:
        logger.debug("SNS_TOPIC_ARN not set — skipping alert: %s", subject)
        return
    try:
        _sns_client().publish(
            TopicArn=settings.sns_topic_arn,
            Subject=subject[:100],
            Message=message,
        )
        logger.info("SNS alert sent: %s", subject)
    except Exception:
        logger.exception("Failed to send SNS alert: %s", subject)


def _update_incident_flag(table, pk: str, field: str, value: str) -> None:
    try:
        table.update_item(
            Key={"PK": pk},
            UpdateExpression="SET #f = :v",
            ExpressionAttributeNames={"#f": field},
            ExpressionAttributeValues={":v": value},
        )
    except Exception:
        logger.exception("Failed to update escalation flag on %s", pk)


def check_escalations() -> dict:
    """
    Scan open/investigating incidents and send SNS alerts for those
    that have exceeded escalation thresholds.

    Returns {"l1_sent": int, "l2_sent": int}
    """
    if not settings.sns_topic_arn:
        return {"l1_sent": 0, "l2_sent": 0}

    dynamodb = get_resource()
    incidents_table = dynamodb.Table(settings.incidents_table)
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    incidents = _scan_open_incidents(incidents_table)
    l1_sent = 0
    l2_sent = 0

    for inc in incidents:
        severity  = inc.get("severity", "")
        status    = inc.get("status", "open")
        pk        = inc.get("PK", "")
        device    = inc.get("device_name", "Unknown")
        title     = inc.get("title", "Incident")
        risk      = inc.get("risk_score", 0)
        inc_id    = inc.get("incident_id", pk.replace("INCIDENT#", "", 1))
        age_min   = _minutes_open(inc, now)

        has_l1 = bool(inc.get("escalated_l1_at"))
        has_l2 = bool(inc.get("escalated_l2_at"))

        # ── L2: Critical still open after 45 min (already had L1) ────────────
        if (severity == "critical"
                and has_l1
                and not has_l2
                and age_min >= L2_CRITICAL_MIN):
            _send_alert(
                subject=f"[OT Sentinel L2] CRITICAL — {title}",
                message=(
                    f"ESCALATION LEVEL 2 — CRITICAL INCIDENT STILL UNRESOLVED\n\n"
                    f"Incident ID : {inc_id}\n"
                    f"Device      : {device}\n"
                    f"Title       : {title}\n"
                    f"Risk Score  : {risk}\n"
                    f"Status      : {status}\n"
                    f"Open for    : {age_min:.0f} minutes\n\n"
                    f"This incident has exceeded the L2 escalation threshold ({L2_CRITICAL_MIN} min).\n"
                    f"Immediate management attention required.\n\n"
                    f"Dashboard: https://d25q7wq8kn7oag.cloudfront.net/incidents.html"
                ),
            )
            _update_incident_flag(incidents_table, pk, "escalated_l2_at", now_iso)
            l2_sent += 1
            continue

        # ── L1: Critical > 15 min or High > 30 min, not yet escalated ────────
        if has_l1:
            continue  # already escalated

        should_escalate = (
            (severity == "critical" and age_min >= L1_CRITICAL_MIN) or
            (severity == "high"     and age_min >= L1_HIGH_MIN)
        )

        if should_escalate:
            level_label = "CRITICAL" if severity == "critical" else "HIGH"
            threshold   = L1_CRITICAL_MIN if severity == "critical" else L1_HIGH_MIN
            _send_alert(
                subject=f"[OT Sentinel L1] {level_label} — {title}",
                message=(
                    f"ESCALATION LEVEL 1 — {level_label} INCIDENT UNACKNOWLEDGED\n\n"
                    f"Incident ID : {inc_id}\n"
                    f"Device      : {device}\n"
                    f"Title       : {title}\n"
                    f"Risk Score  : {risk}\n"
                    f"Status      : {status}\n"
                    f"Open for    : {age_min:.0f} minutes\n\n"
                    f"This incident has exceeded the L1 escalation threshold ({threshold} min).\n"
                    f"Please acknowledge and investigate immediately.\n\n"
                    f"Dashboard: https://d25q7wq8kn7oag.cloudfront.net/incidents.html"
                ),
            )
            _update_incident_flag(incidents_table, pk, "escalated_l1_at", now_iso)
            l1_sent += 1

    logger.info("Escalation check complete: l1_sent=%d l2_sent=%d", l1_sent, l2_sent)
    return {"l1_sent": l1_sent, "l2_sent": l2_sent}
