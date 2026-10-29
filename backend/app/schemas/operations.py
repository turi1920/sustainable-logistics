import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict
from backend.app.models.operations import RefundStatus


class RefundUpdate(BaseModel):
    status: RefundStatus
    external_payout_ref: Optional[str] = None
    manual_processing_notes: Optional[str] = None


class RefundRead(BaseModel):
    id: uuid.UUID
    return_request_id: uuid.UUID
    refund_amount: Decimal
    status: RefundStatus
    initiated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    external_payout_ref: Optional[str] = None
    manual_processing_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuditEventRead(BaseModel):
    id: uuid.UUID
    actor_user_id: Optional[uuid.UUID] = None
    action: str
    entity_name: str
    entity_id: uuid.UUID
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
