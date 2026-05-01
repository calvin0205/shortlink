from typing import Optional

from pydantic import BaseModel


class DeviceResponse(BaseModel):
    device_id: str
    name: str
    type: str
    site_id: str
    site_name: str
    status: str
    ip_address: str
    firmware_version: str
    last_seen: str
    risk_score: int = 0
    bay_id: str = ""
    bay_name: str = ""
    # Predictive maintenance fields
    health_score: Optional[int] = None
    pm_status: str = "ok"
    last_pm_date: Optional[str] = None
    next_pm_date: Optional[str] = None
    pm_interval_days: Optional[int] = None
    operating_hours: float = 0.0
