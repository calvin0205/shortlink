from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_current_user
from ..storage.incidents import get_incident, list_incidents

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("")
async def get_incidents(
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    incidents = list_incidents(severity=severity, status_filter=status)
    return incidents


@router.get("/{incident_id}")
async def get_incident_by_id(
    incident_id: str,
    current_user=Depends(get_current_user),
):
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
