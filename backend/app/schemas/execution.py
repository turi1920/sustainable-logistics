import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.models.execution import (
    AuthorizedDisposition,
    SanitizationMethod,
    SanitizationStatus,
    WorkOrderStatus,
)
from backend.app.models.returns import RecoveryClassification


class SanitizationStartRequest(BaseModel):
    return_item_id: uuid.UUID
    method: SanitizationMethod
    verification_tool: str


class SanitizationCompleteRequest(BaseModel):
    sanitization_record_id: uuid.UUID
    status: SanitizationStatus
    certificate_ref: Optional[str] = None
    exception_reason: Optional[str] = None


class SanitizationRecordRead(BaseModel):
    id: uuid.UUID
    return_item_id: uuid.UUID
    technician_user_id: uuid.UUID
    sanitization_status: SanitizationStatus
    method: SanitizationMethod
    verification_tool: str
    certificate_ref: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class WorkOrderCreate(BaseModel):
    return_item_id: uuid.UUID
    facility_id: uuid.UUID
    work_order_type: RecoveryClassification
    work_summary: Optional[str] = None


class QualityCheckSubmit(BaseModel):
    work_order_id: uuid.UUID
    functional_test_passed: bool
    cosmetic_standard_passed: bool
    packaging_verified: bool
    defects_observed: Optional[str] = None


class ReleaseAuthorizationSubmit(BaseModel):
    return_item_id: uuid.UUID
    authorized_disposition: AuthorizedDisposition
    resale_proceeds_actual: Optional[Decimal] = None
