from pydantic import BaseModel
from typing import Optional


class IncidentResponse(BaseModel):
    incident_id: str
    device_id: str
    device_name: str
    severity: str
    status: str
    title: str
    description: str
    risk_score: int
    created_at: str
    resolved_at: Optional[str] = None
