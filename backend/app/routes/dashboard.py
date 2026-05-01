from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..storage.devices import list_devices
from ..storage.incidents import list_incidents

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


_BAY_ORDER = ["bay1", "bay2", "bay3", "subfab"]


def _compute_bay_status(online: int, warning: int, critical: int, offline: int) -> str:
    if critical > 0 or offline > 0:
        return "critical"
    if warning > 0:
        return "degraded"
    return "healthy"


@router.get("/summary")
async def get_summary(current_user=Depends(get_current_user)):
    """Get dashboard summary statistics including device counts, incident counts, and recent incidents."""
    devices = list_devices()
    incidents = list_incidents()

    total_devices = len(devices)
    online_devices = sum(1 for d in devices if d.get("status") == "online")
    offline_devices = sum(1 for d in devices if d.get("status") == "offline")
    warning_devices = sum(1 for d in devices if d.get("status") == "warning")
    critical_devices = sum(1 for d in devices if d.get("status") == "critical")

    active_incidents = sum(1 for i in incidents if i.get("status") in ("open", "investigating"))
    critical_incidents = sum(1 for i in incidents if i.get("severity") == "critical")

    risk_scores = [int(d.get("risk_score", 0)) for d in devices]
    avg_risk_score = round(sum(risk_scores) / len(risk_scores)) if risk_scores else 0

    open_incidents = [i for i in incidents if i.get("status") in ("open", "investigating")]
    open_incidents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    recent_incidents = open_incidents[:5]

    # Build bay summary grouped by bay_id
    bay_map: dict = {}
    for d in devices:
        bid = d.get("bay_id")
        if not bid:
            continue
        if bid not in bay_map:
            bay_map[bid] = {
                "bay_id": bid,
                "bay_name": d.get("bay_name", ""),
                "total": 0,
                "online": 0,
                "warning": 0,
                "critical": 0,
                "offline": 0,
            }
        entry = bay_map[bid]
        entry["total"] += 1
        s = d.get("status", "")
        if s in entry:
            entry[s] += 1

    bays = []
    for bid in _BAY_ORDER:
        if bid in bay_map:
            entry = bay_map[bid]
            entry["status"] = _compute_bay_status(
                entry["online"], entry["warning"], entry["critical"], entry["offline"]
            )
            bays.append(entry)
    # Append any bays not in the canonical order
    for bid, entry in bay_map.items():
        if bid not in _BAY_ORDER:
            entry["status"] = _compute_bay_status(
                entry["online"], entry["warning"], entry["critical"], entry["offline"]
            )
            bays.append(entry)

    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": offline_devices,
        "warning_devices": warning_devices,
        "critical_devices": critical_devices,
        "active_incidents": active_incidents,
        "critical_incidents": critical_incidents,
        "avg_risk_score": avg_risk_score,
        "recent_incidents": recent_incidents,
        "bays": bays,
    }
