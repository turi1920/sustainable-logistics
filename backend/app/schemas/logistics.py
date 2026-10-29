import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from backend.app.models.logistics import CustodyEventType
from backend.app.models.returns import CustodyLocation


class CustodyEventCreate(BaseModel):
    return_item_id: uuid.UUID
    event_type: CustodyEventType
    from_location: str
    to_location: str
    new_custody_location: CustodyLocation
    carrier_tracking_ref: Optional[str] = None
    notes: Optional[str] = None


class CustodyEventRead(BaseModel):
    id: uuid.UUID
    return_item_id: uuid.UUID
    actor_user_id: uuid.UUID
    event_type: CustodyEventType
    from_location: str
    to_location: str
    carrier_tracking_ref: Optional[str] = None
    notes: Optional[str] = None
    event_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseReceiptCreate(BaseModel):
    return_item_id: uuid.UUID
    facility_id: uuid.UUID
    intake_barcode: str
    storage_bin: str
    packaging_intact: bool
    intake_notes: Optional[str] = None


class WarehouseReceiptRead(BaseModel):
    id: uuid.UUID
    return_item_id: uuid.UUID
    facility_id: uuid.UUID
    receiver_user_id: uuid.UUID
    intake_barcode: str
    storage_bin: str
    packaging_intact: bool
    intake_notes: Optional[str] = None
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)
