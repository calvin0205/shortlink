from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_current_user
from ..storage.devices import get_device
from ..storage.metrics import get_device_metrics

router = APIRouter(prefix="/api/devices", tags=["metrics"])


@router.get("/{device_id}/metrics")
async def get_metrics(
    device_id: str,
    hours: int = Query(24, ge=1, le=168),
    current_user=Depends(get_current_user),
):
    """Return telemetry metric history for a device over the last *hours* hours."""
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return get_device_metrics(device_id, hours=hours)
