import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.models.assessment import EnclosureCondition, ScreenCondition
from backend.app.models.returns import RecoveryClassification


class InspectionCreate(BaseModel):
    return_item_id: uuid.UUID
    is_functional: bool
    powers_on: bool
    screen_condition: ScreenCondition
    enclosure_condition: EnclosureCondition
    battery_health_pct: Optional[int] = Field(None, ge=0, le=100)
    has_safety_hazard: bool = False
    safety_hazard_details: Optional[str] = None
    technician_notes: str


class InspectionRead(InspectionCreate):
    id: uuid.UUID
    inspector_user_id: uuid.UUID
    inspection_version: int
    completed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecoveryEstimateInput(BaseModel):
    expected_resale_value: Decimal = Field(default=Decimal("0.00"))
    parts_cost: Decimal = Field(default=Decimal("0.00"))
    labour_cost: Decimal = Field(default=Decimal("0.00"))
    packaging_cost: Optional[Decimal] = None
    transportation_cost: Optional[Decimal] = None
    sanitization_cost: Optional[Decimal] = None
    applicable_return_credit: Decimal = Field(default=Decimal("0.00"))
    remaining_return_shipping_cost: Optional[Decimal] = None
    is_open_box_resale_eligible: bool = False


class AssessmentReportRead(BaseModel):
    id: uuid.UUID
    return_item_id: uuid.UUID
    report_version: int
    recommended_option: RecoveryClassification
    recommendation_rationale: str
    calculation_snapshot: Dict[str, Any]
    published_at: datetime
    is_latest: bool
    approval_deadline: datetime

    model_config = ConfigDict(from_attributes=True)
