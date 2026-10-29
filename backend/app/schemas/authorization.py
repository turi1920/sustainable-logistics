import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.models.authorization import ApproverAction, DecisionPath
from backend.app.models.returns import ProductCategory, RecoveryClassification


class PolicyCreate(BaseModel):
    policy_code: str
    description: str
    product_category: Optional[ProductCategory] = None
    permitted_action: RecoveryClassification
    max_repair_cost_threshold: Optional[Decimal] = None
    min_expected_nrv_threshold: Optional[Decimal] = None
    requires_safety_pass: bool = True
    valid_from: date
    valid_to: date


class PolicyRead(PolicyCreate):
    id: uuid.UUID
    manufacturer_org_id: uuid.UUID
    is_active: bool
    version: int

    model_config = ConfigDict(from_attributes=True)


class ApprovalRequestItemRead(BaseModel):
    id: uuid.UUID
    return_item_id: uuid.UUID
    assessment_report_id: uuid.UUID
    is_decided: bool
    item_tag: Optional[str] = None
    product_name: Optional[str] = None
    recommended_option: Optional[RecoveryClassification] = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalRequestRead(BaseModel):
    id: uuid.UUID
    batch_reference: Optional[str] = None
    manufacturer_org_id: uuid.UUID
    deadline_at: datetime
    is_closed: bool
    items: List[ApprovalRequestItemRead] = []

    model_config = ConfigDict(from_attributes=True)


class ItemDecisionSubmit(BaseModel):
    approval_request_item_id: uuid.UUID
    action: ApproverAction
    approved_recovery_option: Optional[RecoveryClassification] = None
    decision_reason: str


class BatchDecisionSubmit(BaseModel):
    batch_reference: Optional[str] = None
    items: List[ItemDecisionSubmit]
