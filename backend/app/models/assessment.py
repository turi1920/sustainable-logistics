import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, GUID, TimestampMixin, UUIDMixin
from backend.app.models.returns import RecoveryClassification


class ScreenCondition(str, enum.Enum):
    PRISTINE = "PRISTINE"
    MINOR_SCRATCHES = "MINOR_SCRATCHES"
    CRACKED = "CRACKED"
    DEAD_PIXELS = "DEAD_PIXELS"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EnclosureCondition(str, enum.Enum):
    GRADE_A_MINT = "GRADE_A_MINT"
    GRADE_B_LIGHT_WEAR = "GRADE_B_LIGHT_WEAR"
    GRADE_C_HEAVY_WEAR = "GRADE_C_HEAVY_WEAR"
    STRUCTURAL_DAMAGE = "STRUCTURAL_DAMAGE"


class Inspection(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "inspections"

    return_item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("return_items.id"), index=True, nullable=False)
    inspector_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    inspection_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Technical Test Findings
    is_functional: Mapped[bool] = mapped_column(Boolean, nullable=False)
    powers_on: Mapped[bool] = mapped_column(Boolean, nullable=False)
    screen_condition: Mapped[ScreenCondition] = mapped_column(Enum(ScreenCondition), nullable=False)
    enclosure_condition: Mapped[EnclosureCondition] = mapped_column(Enum(EnclosureCondition), nullable=False)
    battery_health_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_safety_hazard: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    safety_hazard_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technician_notes: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    return_item: Mapped["ReturnItem"] = relationship("ReturnItem", back_populates="inspections")
    inspector: Mapped["User"] = relationship("User")
    estimates: Mapped[List["RecoveryEstimate"]] = relationship("RecoveryEstimate", back_populates="inspection", cascade="all, delete-orphan")


class RecoveryEstimate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "recovery_estimates"

    inspection_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("inspections.id"), index=True, nullable=False)
    option_type: Mapped[RecoveryClassification] = mapped_column(Enum(RecoveryClassification), nullable=False)
    is_technically_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ineligibility_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Financial Inputs strictly in Decimal
    expected_resale_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    parts_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    labour_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    packaging_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    transportation_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    sanitization_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    applicable_return_credit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    remaining_return_shipping_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    
    # Final Result
    net_recovery_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(20), default="v1.0", nullable=False)

    inspection: Mapped["Inspection"] = relationship("Inspection", back_populates="estimates")


class AssessmentReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assessment_reports"

    return_item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("return_items.id"), index=True, nullable=False)
    report_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    recommended_option: Mapped[RecoveryClassification] = mapped_column(Enum(RecoveryClassification), nullable=False)
    recommendation_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    calculation_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    approval_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    return_item: Mapped["ReturnItem"] = relationship("ReturnItem", back_populates="assessment_reports")
