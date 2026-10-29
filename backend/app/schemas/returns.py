import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from backend.app.models.returns import (
    ApprovalStatus,
    CustodyLocation,
    DamageClassification,
    ProductCategory,
    RecoveryClassification,
    ReturnCaseStatus,
    VerificationOutcome,
)


class ReturnItemCreate(BaseModel):
    manufacturer_org_id: uuid.UUID
    product_name: str
    product_category: ProductCategory
    model_number: str
    declared_serial_number: Optional[str] = None
    return_reason: str
    requires_data_sanitization: bool = True


class ReturnItemRead(BaseModel):
    id: uuid.UUID
    return_request_id: uuid.UUID
    manufacturer_org_id: uuid.UUID
    item_tag: str
    product_name: str
    product_category: ProductCategory
    model_number: str
    declared_serial_number: Optional[str] = None
    verified_serial_number: Optional[str] = None
    return_reason: str
    recovery_classification: RecoveryClassification
    approval_status: ApprovalStatus
    current_custody_location: CustodyLocation
    requires_data_sanitization: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReturnRequestCreate(BaseModel):
    external_order_ref: str
    customer_name: str
    customer_email: EmailStr
    customer_phone: str
    pickup_address: str
    pickup_city: str
    pickup_postal_code: str
    items: List[ReturnItemCreate]


class ReturnRequestRead(BaseModel):
    id: uuid.UUID
    case_number: str
    external_order_ref: str
    customer_name: str
    customer_email: EmailStr
    customer_phone: str
    pickup_address: str
    pickup_city: str
    pickup_postal_code: str
    status: ReturnCaseStatus
    created_at: datetime
    items: List[ReturnItemRead] = []

    model_config = ConfigDict(from_attributes=True)


class PickupAssignRequest(BaseModel):
    return_item_id: uuid.UUID
    agent_user_id: uuid.UUID
    scheduled_date: date


class PickupVerifyRequest(BaseModel):
    observed_product_code: str
    verified_serial_number: Optional[str] = None
    initial_damage: DamageClassification
    verification_outcome: VerificationOutcome
    verification_notes: Optional[str] = None
    agent_signature_ref: Optional[str] = None


class PickupAssignmentRead(BaseModel):
    id: uuid.UUID
    return_item_id: uuid.UUID
    agent_user_id: uuid.UUID
    scheduled_date: date
    completed_at: Optional[datetime] = None
    initial_damage: Optional[DamageClassification] = None
    verification_outcome: Optional[VerificationOutcome] = None
    verification_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
