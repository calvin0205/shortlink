from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from ..dependencies import get_current_user
from ..models.simulate import SimulateRequest, SimulateResponse
from ..risk_engine import calculate_risk, get_anomaly_types
from ..storage.audit import create_audit_log
from ..storage.devices import get_device, update_device
from ..storage.incidents import create_incident

router = APIRouter(prefix="/api/devices", tags=["simulate"])


@router.get("/anomaly-types")
async def list_anomaly_types(current_user=Depends(get_current_user)):
    """Return available anomaly types for the frontend dropdown."""
    return get_anomaly_types()


@router.post("/{device_id}/simulate", response_model=SimulateResponse)
async def simulate_anomaly(
    device_id: str,
    body: SimulateRequest,
    request: Request,
    current_user=Depends(get_current_user),
):
    # 1. Get device (404 if not found)
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device_name = device.get("name", device_id)
    device_type = device.get("type", "Sensor")

    # 2. Calculate risk score
    try:
        risk_score, severity, title_tmpl, desc_tmpl = calculate_risk(
            body.anomaly_type, device_type
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 3. Format title and description
    title = title_tmpl
    description = desc_tmpl.format(device_name=device_name)

    # 4. Create incident
    incident_id = str(uuid4())
    create_incident(
        incident_id=incident_id,
        device_id=device_id,
        device_name=device_name,
        severity=severity,
        title=title,
        description=description,
        risk_score=risk_score,
    )

    # 5. Update device status and risk score
    if severity in ("critical", "high"):
        device_status = "critical"
    else:
        device_status = "warning"

    update_device(
        device_id,
        {
            "status": device_status,
            "risk_score": risk_score,
            "last_seen": datetime.now(timezone.utc).isoformat(),
        },
    )

    # 6. Write audit log
    ip_address = request.client.host if request.client else "unknown"
    create_audit_log(
        user_id=current_user.get("user_id", ""),
        user_email=current_user.get("email", ""),
        action="SIMULATE_ANOMALY",
        resource_type="DEVICE",
        resource_id=device_id,
        detail=f"Simulated {body.anomaly_type} on {device_name}, risk_score={risk_score}",
        ip_address=ip_address,
    )

    # 7. Return response
    return SimulateResponse(
        incident_id=incident_id,
        device_id=device_id,
        device_name=device_name,
        anomaly_type=body.anomaly_type,
        risk_score=risk_score,
        severity=severity,
        title=title,
        message=description,
    )
