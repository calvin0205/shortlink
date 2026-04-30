from pydantic import BaseModel
from typing import Optional


class SimulateRequest(BaseModel):
    anomaly_type: str


class SimulateResponse(BaseModel):
    incident_id: str
    device_id: str
    device_name: str
    anomaly_type: str
    risk_score: int
    severity: str
    title: str
    message: str


class AcknowledgeRequest(BaseModel):
    note: Optional[str] = None


class ResolveRequest(BaseModel):
    resolution_note: Optional[str] = None
