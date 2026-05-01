"""
maintenance.py — Predictive maintenance overview endpoint.

GET /api/devices/maintenance
Returns all PM-configured devices sorted by health score ascending (worst first).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..health_score import compute_health_score, compute_pm_status
from ..storage.devices import list_devices

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("/maintenance")
def get_maintenance_overview(current_user=Depends(get_current_user)):
    """
    Return all PM-configured devices sorted by health_score ascending.

    Only devices that have `pm_interval_days` set are included.
    """
    devices = list_devices()
    result = []

    for d in devices:
        if not d.get("PK", "").startswith("DEVICE#"):
            continue

        pm_interval = d.get("pm_interval_days")
        if not pm_interval:
            continue  # device has no PM schedule

        next_pm = d.get("next_pm_date")
        pm_status: str = d.get("pm_status") or compute_pm_status(next_pm)

        # Use stored health_score if available; recompute otherwise
        health = d.get("health_score")
        if health is None:
            health = compute_health_score(
                risk_score=int(d.get("risk_score", 50)),
                status=d.get("status", "online"),
                pm_status=pm_status,
                next_pm_date=next_pm,
            )

        result.append(
            {
                "device_id": d.get("device_id", ""),
                "name": d.get("name", ""),
                "type": d.get("type", ""),
                "site_name": d.get("site_name", ""),
                "bay_name": d.get("bay_name", ""),
                "status": d.get("status", ""),
                "risk_score": int(d.get("risk_score", 0)),
                "health_score": int(health),
                "pm_status": pm_status,
                "last_pm_date": d.get("last_pm_date"),
                "next_pm_date": next_pm,
                "pm_interval_days": int(pm_interval),
                "operating_hours": float(d.get("operating_hours", 0)),
            }
        )

    # Sort worst-first (lowest health), break ties alphabetically
    result.sort(key=lambda x: (x["health_score"], x["name"]))
    return result
