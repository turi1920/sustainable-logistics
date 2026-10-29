import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, GUID, TimestampMixin, UUIDMixin
from backend.app.models.returns import ProductCategory, RecoveryClassification


class DecisionPath(str, enum.Enum):
    POLICY_PRE_AUTHORIZED = "POLICY_PRE_AUTHORIZED"
    BATCH_HUMAN_APPROVAL = "BATCH_HUMAN_APPROVAL"
    INDIVIDUAL_HUMAN_APPROVAL = "INDIVIDUAL_HUMAN_APPROVAL"
    TIMEOUT_NON_RESPONSE_ACTION = "TIMEOUT_NON_RESPONSE_ACTION"


class ApproverAction(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_MORE_INFORMATION = "REQUEST_MORE_INFORMATION"


class PartnerContract(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "partner_contracts"

    manufacturer_org_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id"), unique=True, index=True, nullable=False)
    auto_return_on_timeout_authorized: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    contract_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    contract_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    default_return_shipping_carrier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    manufacturer_org: Mapped["Organization"] = relationship("Organization")


class AuthorizationPolicy(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "authorization_policies"

    manufacturer_org_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id"), index=True, nullable=False)
    policy_code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    product_category: Mapped[Optional[ProductCategory]] = mapped_column(Enum(ProductCategory), nullable=True) # None = all
    permitted_action: Mapped[RecoveryClassification] = mapped_column(Enum(RecoveryClassification), nullable=False)
    max_repair_cost_threshold: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    min_expected_nrv_threshold: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    requires_safety_pass: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    manufacturer_org: Mapped["Organization"] = relationship("Organization")


class ApprovalRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "approval_requests"

    batch_reference: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    manufacturer_org_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id"), index=True, nullable=False)
    first_reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    second_reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    items: Mapped[List["ApprovalRequestItem"]] = relationship("ApprovalRequestItem", back_populates="approval_request", cascade="all, delete-orphan", lazy="selectin")


class ApprovalRequestItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "approval_request_items"

    approval_request_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("approval_requests.id"), index=True, nullable=False)
    return_item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("return_items.id"), index=True, nullable=False)
    assessment_report_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("assessment_reports.id"), nullable=False)
    is_decided: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    approval_request: Mapped["ApprovalRequest"] = relationship("ApprovalRequest", back_populates="items", lazy="selectin")
    return_item: Mapped["ReturnItem"] = relationship("ReturnItem", lazy="selectin")
    decision: Mapped[Optional["AuthorizationDecision"]] = relationship("AuthorizationDecision", back_populates="request_item", uselist=False, lazy="selectin")

    @property
    def item_tag(self) -> Optional[str]:
        return self.return_item.item_tag if self.return_item else None

    @property
    def product_name(self) -> Optional[str]:
        return self.return_item.product_name if self.return_item else None

    @property
    def recommended_option(self) -> Optional[RecoveryClassification]:
        return self.return_item.recovery_classification if self.return_item else None


class AuthorizationDecision(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "authorization_decisions"

    approval_request_item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("approval_request_items.id"), unique=True, index=True, nullable=False)
    decided_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True) # None if policy pre-authorized
    policy_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("authorization_policies.id"), nullable=True)
    decision_path: Mapped[DecisionPath] = mapped_column(Enum(DecisionPath), nullable=False)
    action_approved: Mapped[RecoveryClassification] = mapped_column(Enum(RecoveryClassification), nullable=False)
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    request_item: Mapped["ApprovalRequestItem"] = relationship("ApprovalRequestItem", back_populates="decision")
    decided_by: Mapped[Optional["User"]] = relationship("User")
    policy: Mapped[Optional["AuthorizationPolicy"]] = relationship("AuthorizationPolicy")
