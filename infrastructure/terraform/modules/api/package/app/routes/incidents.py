from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..dependencies import get_current_user
from ..models.simulate import AcknowledgeRequest, ResolveRequest
from ..storage.audit import create_audit_log
from ..storage.devices import update_device
from ..storage.incidents import get_incident, list_incidents, update_incident

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("")
async def get_incidents(
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    """List all security incidents. Filter by severity and/or status."""
    incidents = list_incidents(severity=severity, status_filter=status)
    return incidents


@router.get("/{incident_id}")
async def get_incident_by_id(
    incident_id: str,
    current_user=Depends(get_current_user),
):
    """Get detailed information about a specific incident."""
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/{incident_id}/acknowledge")
async def acknowledge_incident(
    incident_id: str,
    body: AcknowledgeRequest,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Acknowledge an incident — changes status from 'open' to 'investigating'."""
    # 1. Get incident
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # 2. Check if already resolved
    if incident.get("status") == "resolved":
        raise HTTPException(status_code=400, detail="Already resolved")

    # 3. Update incident status
    now = datetime.now(timezone.utc).isoformat()
    updated = update_incident(incident_id, {"status": "investigating", "acknowledged_at": now})

    # 4. Write audit log
    ip_address = request.client.host if request.client else "unknown"
    create_audit_log(
        user_id=current_user.get("user_id", ""),
        user_email=current_user.get("email", ""),
        action="ACKNOWLEDGE_INCIDENT",
        resource_type="INCIDENT",
        resource_id=incident_id,
        detail=f"Acknowledged: {incident.get('title', incident_id)}",
        ip_address=ip_address,
    )

    return updated


@router.post("/{incident_id}/resolve")
async def resolve_incident(
    incident_id: str,
    body: ResolveRequest,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Resolve an incident — changes status to 'resolved' and resets device status to 'online'."""
    # 1. Get incident
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # 2. Update incident status
    now = datetime.now(timezone.utc).isoformat()
    updated = update_incident(incident_id, {"status": "resolved", "resolved_at": now})

    # 3. Set device back to "online" when incident is resolved
    device_id = incident.get("device_id")
    if device_id:
        update_device(device_id, {"status": "online"})

    # 4. Write audit log
    ip_address = request.client.host if request.client else "unknown"
    create_audit_log(
        user_id=current_user.get("user_id", ""),
        user_email=current_user.get("email", ""),
        action="RESOLVE_INCIDENT",
        resource_type="INCIDENT",
        resource_id=incident_id,
        detail=f"Resolved: {incident.get('title', incident_id)}",
        ip_address=ip_address,
    )

    return updated
