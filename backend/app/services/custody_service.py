import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.exceptions import ResourceNotFoundError
from backend.app.domain.state_machines import StateMachineValidator
from backend.app.models.logistics import CustodyEvent, CustodyEventType, WarehouseReceipt
from backend.app.models.returns import CustodyLocation, ReturnCaseStatus, ReturnItem, ReturnRequest
from backend.app.schemas.logistics import CustodyEventCreate, WarehouseReceiptCreate
from backend.app.services.audit_service import AuditService


class CustodyService:
    @classmethod
    async def record_custody_transfer(
        cls,
        db: AsyncSession,
        event_in: CustodyEventCreate,
        actor_user_id: uuid.UUID
    ) -> CustodyEvent:
        stmt = select(ReturnItem).where(ReturnItem.id == event_in.return_item_id)
        item = (await db.execute(stmt)).scalar_one_or_none()
        if not item:
            raise ResourceNotFoundError("ReturnItem", str(event_in.return_item_id))

        # Validate custody transition
        StateMachineValidator.validate_custody_transition(
            item.current_custody_location,
            event_in.new_custody_location,
            str(item.id)
        )

        item.current_custody_location = event_in.new_custody_location

        # If transitioning to IN_TRANSIT, update return case status if appropriate
        if event_in.new_custody_location == CustodyLocation.IN_TRANSIT:
            stmt_req = select(ReturnRequest).where(ReturnRequest.id == item.return_request_id)
            req = (await db.execute(stmt_req)).scalar_one()
            if req.status == ReturnCaseStatus.PICKED_UP:
                req.status = ReturnCaseStatus.IN_TRANSIT

        event = CustodyEvent(
            return_item_id=item.id,
            actor_user_id=actor_user_id,
            event_type=event_in.event_type,
            from_location=event_in.from_location,
            to_location=event_in.to_location,
            carrier_tracking_ref=event_in.carrier_tracking_ref,
            notes=event_in.notes
        )
        db.add(event)
        await db.flush()

        await AuditService.log_event(
            db=db,
            action="CUSTODY_TRANSFERRED",
            entity_name="ReturnItem",
            entity_id=item.id,
            actor_user_id=actor_user_id,
            new_state={"location": event_in.new_custody_location.value}
        )
        return event

    @classmethod
    async def receive_at_warehouse(
        cls,
        db: AsyncSession,
        receipt_in: WarehouseReceiptCreate,
        receiver_user_id: uuid.UUID
    ) -> WarehouseReceipt:
        stmt = select(ReturnItem).where(ReturnItem.id == receipt_in.return_item_id)
        item = (await db.execute(stmt)).scalar_one_or_none()
        if not item:
            raise ResourceNotFoundError("ReturnItem", str(receipt_in.return_item_id))

        item.current_custody_location = CustodyLocation.WAREHOUSE
        item.current_facility_id = receipt_in.facility_id

        stmt_req = select(ReturnRequest).where(ReturnRequest.id == item.return_request_id)
        req = (await db.execute(stmt_req)).scalar_one()
        req.status = ReturnCaseStatus.WAREHOUSE_RECEIVED

        receipt = WarehouseReceipt(
            return_item_id=item.id,
            facility_id=receipt_in.facility_id,
            receiver_user_id=receiver_user_id,
            intake_barcode=receipt_in.intake_barcode,
            storage_bin=receipt_in.storage_bin,
            packaging_intact=receipt_in.packaging_intact,
            intake_notes=receipt_in.intake_notes
        )
        db.add(receipt)

        # Record warehouse custody event
        custody_event = CustodyEvent(
            return_item_id=item.id,
            actor_user_id=receiver_user_id,
            event_type=CustodyEventType.WAREHOUSE_ARRIVAL,
            from_location="In Transit",
            to_location=f"Warehouse Bin {receipt_in.storage_bin}",
            notes=f"Intake scanned. Packaging intact: {receipt_in.packaging_intact}."
        )
        db.add(custody_event)
        await db.flush()

        await AuditService.log_event(
            db=db,
            action="WAREHOUSE_RECEIVED",
            entity_name="ReturnItem",
            entity_id=item.id,
            actor_user_id=receiver_user_id,
            new_state={"bin": receipt_in.storage_bin, "status": ReturnCaseStatus.WAREHOUSE_RECEIVED.value}
        )
        return receipt

    @classmethod
    async def get_timeline(
        cls,
        db: AsyncSession,
        return_item_id: uuid.UUID
    ) -> List[CustodyEvent]:
        stmt = (
            select(CustodyEvent)
            .where(CustodyEvent.return_item_id == return_item_id)
            .order_by(CustodyEvent.event_timestamp.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
