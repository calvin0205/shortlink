from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_current_user
from ..storage.devices import get_device, list_devices

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("")
async def get_devices(
    status: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    devices = list_devices(status_filter=status)
    return devices


@router.get("/{device_id}")
async def get_device_by_id(
    device_id: str,
    current_user=Depends(get_current_user),
):
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device
