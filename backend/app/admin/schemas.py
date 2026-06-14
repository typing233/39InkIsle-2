from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class AuditLogResponse(BaseModel):
    id: int
    user_id: UUID | None
    action: str
    resource_type: str | None
    resource_id: UUID | None
    details: dict | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
