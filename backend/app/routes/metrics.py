from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_current_user
from ..spc import calculate_baseline
from ..storage.devices import get_device
from ..storage.metrics import get_device_metrics, get_recent_metrics

router = APIRouter(prefix="/api/devices", tags=["metrics"])


@router.get("/{device_id}/metrics")
async def get_metrics(
    device_id: str,
    hours: int = Query(24, ge=1, le=168),
    current_user=Depends(get_current_user),
):
    """Return telemetry metric history and SPC baselines for a device."""
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    data = get_device_metrics(device_id, hours=hours)
    recent = get_recent_metrics(device_id, n=30)

    # Calculate SPC baselines for the three chart fields
    baselines: dict = {}
    for field in ["cpu_pct", "temp_c", "risk_score"]:
        baselines[field] = calculate_baseline(recent, field)

    return {"metrics": data, "baselines": baselines}
