from fastapi import APIRouter, Depends

from ..dependencies import require_admin
from ..storage.audit import list_audit_logs

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
async def get_audit_logs(current_user=Depends(require_admin)):
    """Get the audit log of all security-relevant actions. Admin only."""
    logs = list_audit_logs(limit=50)
    return logs
