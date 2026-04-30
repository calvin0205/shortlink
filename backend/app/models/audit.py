from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    log_id: str
    user_id: str
    user_email: str
    action: str
    resource_type: str
    resource_id: str
    detail: str
    ip_address: str
    timestamp: str
