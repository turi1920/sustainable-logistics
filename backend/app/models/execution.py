import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, GUID, TimestampMixin, UUIDMixin
from backend.app.models.returns import RecoveryClassification


class SanitizationStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    EXCEPTION_REVIEW = "EXCEPTION_REVIEW"


class SanitizationMethod(str, enum.Enum):
    NIST_800_88_CLEAR = "NIST_800_88_CLEAR"
    NIST_800_88_PURGE = "NIST_800_88_PURGE"
    CRYPTOGRAPHIC_ERASE = "CRYPTOGRAPHIC_ERASE"
    PHYSICAL_DESTRUCTION = "PHYSICAL_DESTRUCTION"
    NOT_APPLICABLE_NO_STORAGE = "NOT_APPLICABLE_NO_STORAGE"


class WorkOrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    QUALITY_CHECK = "QUALITY_CHECK"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AuthorizedDisposition(str, enum.Enum):
    RESALE_SECONDARY_MARKET = "RESALE_SECONDARY_MARKET"
    RESALE_OUTLET = "RESALE_OUTLET"
    DISPATCHED_TO_MANUFACTURER = "DISPATCHED_TO_MANUFACTURER"
    RECYCLED_CERTIFIED = "RECYCLED_CERTIFIED"


class SanitizationRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sanitization_records"

    return_item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("return_items.id"), index=True, nullable=False)
    technician_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    sanitization_status: Mapped[SanitizationStatus] = mapped_column(Enum(SanitizationStatus), default=SanitizationStatus.NOT_STARTED, nullable=False)
    method: Mapped[SanitizationMethod] = mapped_column(Enum(SanitizationMethod), nullable=False)
    verification_tool: Mapped[str] = mapped_column(String(100), nullable=False)
    certificate_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    exception_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    return_item: Mapped["ReturnItem"] = relationship("ReturnItem", back_populates="sanitization_records")
    technician: Mapped["User"] = relationship("User")


class RecoveryWorkOrder(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "recovery_work_orders"

    return_item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("return_items.id"), index=True, nullable=False)
    facility_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("facilities.id"), nullable=False)
    assigned_technician_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    work_order_type: Mapped[RecoveryClassification] = mapped_column(Enum(RecoveryClassification), nullable=False)
    status: Mapped[WorkOrderStatus] = mapped_column(Enum(WorkOrderStatus), default=WorkOrderStatus.PENDING, index=True, nullable=False)
    
    # Actual Incurred Financials
    actual_parts_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    actual_labour_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    actual_packaging_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    actual_shipping_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    work_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    return_item: Mapped["ReturnItem"] = relationship("ReturnItem", back_populates="work_orders")
    facility: Mapped["Facility"] = relationship("Facility")
    technician: Mapped[Optional["User"]] = relationship("User")
    parts_used: Mapped[List["PartsUsage"]] = relationship("PartsUsage", back_populates="work_order", cascade="all, delete-orphan")
    quality_checks: Mapped[List["QualityCheck"]] = relationship("QualityCheck", back_populates="work_order", cascade="all, delete-orphan")


class PartsUsage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "parts_usage"

    work_order_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("recovery_work_orders.id"), index=True, nullable=False)
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)
    part_description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    work_order: Mapped["RecoveryWorkOrder"] = relationship("RecoveryWorkOrder", back_populates="parts_used")


class QualityCheck(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "quality_checks"

    work_order_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("recovery_work_orders.id"), index=True, nullable=False)
    inspector_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    functional_test_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cosmetic_standard_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    packaging_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    defects_observed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    work_order: Mapped["RecoveryWorkOrder"] = relationship("RecoveryWorkOrder", back_populates="quality_checks")
    inspector: Mapped["User"] = relationship("User")


class ReleaseAuthorization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "release_authorizations"

    return_item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("return_items.id"), unique=True, index=True, nullable=False)
    authorized_disposition: Mapped[AuthorizedDisposition] = mapped_column(Enum(AuthorizedDisposition), nullable=False)
    resale_proceeds_actual: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    verified_sanitization_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("sanitization_records.id"), nullable=True)
    authorized_by_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    released_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    return_item: Mapped["ReturnItem"] = relationship("ReturnItem")
    sanitization_record: Mapped[Optional["SanitizationRecord"]] = relationship("SanitizationRecord")
    authorized_by: Mapped["User"] = relationship("User")
