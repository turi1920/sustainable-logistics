import enum
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, GUID, TimestampMixin, UUIDMixin


class CustodyEventType(str, enum.Enum):
    PICKUP_COLLECTION = "PICKUP_COLLECTION"
    TRANSIT_DEPARTURE = "TRANSIT_DEPARTURE"
    WAREHOUSE_ARRIVAL = "WAREHOUSE_ARRIVAL"
    CUSTODY_HANDOVER = "CUSTODY_HANDOVER"
    FACILITY_TRANSFER = "FACILITY_TRANSFER"
    DISPATCH_TO_MANUFACTURER = "DISPATCH_TO_MANUFACTURER"
    FINAL_DELIVERY = "FINAL_DELIVERY"


class CustodyEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "custody_events"

    return_item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("return_items.id"), index=True, nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True, nullable=False)
    event_type: Mapped[CustodyEventType] = mapped_column(Enum(CustodyEventType), nullable=False)
    from_location: Mapped[str] = mapped_column(String(100), nullable=False)
    to_location: Mapped[str] = mapped_column(String(100), nullable=False)
    carrier_tracking_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    return_item: Mapped["ReturnItem"] = relationship("ReturnItem", back_populates="custody_events")
    actor: Mapped["User"] = relationship("User")


class WarehouseReceipt(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "warehouse_receipts"

    return_item_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("return_items.id"), unique=True, index=True, nullable=False)
    facility_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("facilities.id"), nullable=False)
    receiver_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    intake_barcode: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_bin: Mapped[str] = mapped_column(String(50), nullable=False)
    packaging_intact: Mapped[bool] = mapped_column(nullable=False)
    intake_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
