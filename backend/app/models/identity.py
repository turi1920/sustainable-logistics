import enum
import uuid
from typing import List, Optional
from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, GUID, TimestampMixin, UUIDMixin


class OrgType(str, enum.Enum):
    MANUFACTURER = "MANUFACTURER"
    LOGISTICS_PARTNER = "LOGISTICS_PARTNER"
    RECOVERY_FACILITY = "RECOVERY_FACILITY"
    PLATFORM_OPERATOR = "PLATFORM_OPERATOR"


class UserRole(str, enum.Enum):
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    RETURN_AGENT = "RETURN_AGENT"
    OPERATIONS_SPECIALIST = "OPERATIONS_SPECIALIST"
    MANUFACTURER_APPROVER = "MANUFACTURER_APPROVER"
    FINANCE_SUSTAINABILITY_ANALYST = "FINANCE_SUSTAINABILITY_ANALYST"


class FacilityType(str, enum.Enum):
    CENTRAL_WAREHOUSE = "CENTRAL_WAREHOUSE"
    INSPECTION_HUB = "INSPECTION_HUB"
    REPAIR_DEPOT = "REPAIR_DEPOT"
    RECYCLING_PLANT = "RECYCLING_PLANT"


class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    org_type: Mapped[OrgType] = mapped_column(Enum(OrgType), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[List["User"]] = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    facilities: Mapped[List["Facility"]] = relationship("Facility", back_populates="organization")


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id"), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")


class Facility(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "facilities"

    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id"), nullable=False)
    facility_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    facility_name: Mapped[str] = mapped_column(String(255), nullable=False)
    facility_type: Mapped[FacilityType] = mapped_column(Enum(FacilityType), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(50), default="US", nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="facilities")
