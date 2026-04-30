from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..storage.devices import list_devices
from ..storage.incidents import list_incidents

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_summary(current_user=Depends(get_current_user)):
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
    }
