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
