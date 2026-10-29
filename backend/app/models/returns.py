import enum
import uuid
from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, GUID, TimestampMixin, UUIDMixin


class ReturnCaseStatus(str, enum.Enum):
    RETURN_REQUESTED = "RETURN_REQUESTED"
    PICKUP_ASSIGNED = "PICKUP_ASSIGNED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    WAREHOUSE_RECEIVED = "WAREHOUSE_RECEIVED"
    INSPECTION_IN_PROGRESS = "INSPECTION_IN_PROGRESS"
    ASSESSED = "ASSESSED"
    RECOVERY_IN_PROGRESS = "RECOVERY_IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ON_HOLD = "ON_HOLD"


class ProductCategory(str, enum.Enum):
    LAPTOP = "LAPTOP"
    SMARTPHONE = "SMARTPHONE"
    TABLET = "TABLET"
    AUDIO = "AUDIO"
    MONITOR = "MONITOR"
    COMPONENT = "COMPONENT"
    ACCESSORY = "ACCESSORY"


class RecoveryClassification(str, enum.Enum):
    REPAIR = "REPAIR"
    REFURBISHMENT = "REFURBISHMENT"
    RESALE_AS_NEW_ELIGIBLE = "RESALE_AS_NEW_ELIGIBLE"
    RETURN_TO_MANUFACTURER = "RETURN_TO_MANUFACTURER"
    RECYCLING = "RECYCLING"
    ON_HOLD = "ON_HOLD"


class ApprovalStatus(str, enum.Enum):
    NOT_REQUIRED_POLICY_AUTHORIZED = "NOT_REQUIRED_POLICY_AUTHORIZED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OVERDUE = "OVERDUE"
    ESCALATED = "ESCALATED"


class CustodyLocation(str, enum.Enum):
    WITH_RETURN_AGENT = "WITH_RETURN_AGENT"
    IN_TRANSIT = "IN_TRANSIT"
    WAREHOUSE = "WAREHOUSE"
    INSPECTION_FACILITY = "INSPECTION_FACILITY"
    REPAIR_FACILITY = "REPAIR_FACILITY"
    WITH_CARRIER = "WITH_CARRIER"
    DELIVERED_TO_MANUFACTURER = "DELIVERED_TO_MANUFACTURER"


class DamageClassification(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class VerificationOutcome(str, enum.Enum):
    VERIFIED = "VERIFIED"
    MISMATCH = "MISMATCH"
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY"


class ReturnRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "return_requests"

    case_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    external_order_ref: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    pickup_address: Mapped[str] = mapped_column(Text, nullable=False)
    pickup_city: Mapped[str] = mapped_column(String(100), nullable=False)
    pickup_postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[ReturnCaseStatus] = mapped_column(
        Enum(ReturnCaseStatus),
        default=ReturnCaseStatus.RETURN_REQUESTED,
        index=True,
        nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)

    items: Mapped[List["ReturnItem"]] = relationship("ReturnItem", back_populates="return_request", cascade="all, delete-orphan", lazy="selectin")
    refund_record: Mapped[Optional["RefundRecord"]] = relationship("RefundRecord", back_populates="return_request", uselist=False, lazy="selectin")


class ReturnItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "return_items"

    return_request_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("return_requests.id", ondelete="RESTRICT"), index=True, nullable=False)
    manufacturer_org_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id"), index=True, nullable=False)
    item_tag: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_category: Mapped[ProductCategory] = mapped_column(Enum(ProductCategory), index=True, nullable=False)
    model_number: Mapped[str] = mapped_column(String(100), nullable=False)
    declared_serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    verified_serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    return_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # 6-Dimensional State Models on Item
    recovery_classification: Mapped[RecoveryClassification] = mapped_column(
        Enum(RecoveryClassification),
        default=RecoveryClassification.ON_HOLD,
        nullable=False
    )
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus),
        default=ApprovalStatus.PENDING_APPROVAL,
        nullable=False
    )
    current_custody_location: Mapped[CustodyLocation] = mapped_column(
        Enum(CustodyLocation),
        default=CustodyLocation.WITH_RETURN_AGENT,
        nullable=False
    )
    current_facility_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("facilities.id"), nullable=True)
    requires_data_sanitization: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    return_request: Mapped["ReturnRequest"] = relationship("ReturnRequest", back_populates="items")
    pickup_assignment: Mapped[Optional["PickupAssignment"]] = relationship("PickupAssignment", back_populates="return_item", uselist=False)
    inspections: Mapped[List["Inspection"]] = relationship("Inspection", back_populates="return_item", lazy="selectin")
    assessment_reports: Mapped[List["AssessmentReport"]] = relationship("AssessmentReport", back_populates="return_item", lazy="selectin")
    sanitization_records: Mapped[List["SanitizationRecord"]] = relationship("SanitizationRecord", back_populates="return_item", lazy="selectin")
    work_orders: Mapped[List["RecoveryWorkOrder"]] = relationship("RecoveryWorkOrder", back_populates="return_item", lazy="selectin")
    custody_events: Mapped[List["CustodyEvent"]] = relationship("CustodyEvent", back_populates="return_item", lazy="selectin")


class PickupAssignment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pickup_assignments"

    return_item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("return_items.id"), unique=True, index=True, nullable=False)
    agent_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True, nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    initial_damage: Mapped[Optional[DamageClassification]] = mapped_column(Enum(DamageClassification), nullable=True)
    verification_outcome: Mapped[Optional[VerificationOutcome]] = mapped_column(Enum(VerificationOutcome), nullable=True)
    verification_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_signature_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    return_item: Mapped["ReturnItem"] = relationship("ReturnItem", back_populates="pickup_assignment")
    agent: Mapped["User"] = relationship("User")
