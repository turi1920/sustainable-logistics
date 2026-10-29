import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.exceptions import ResourceNotFoundError
from backend.app.models.assessment import Inspection
from backend.app.models.returns import CustodyLocation, ReturnCaseStatus, ReturnItem, ReturnRequest
from backend.app.schemas.assessment import InspectionCreate
from backend.app.services.audit_service import AuditService


class InspectionService:
    @classmethod
    async def record_inspection(
        cls,
        db: AsyncSession,
        insp_in: InspectionCreate,
        inspector_user_id: uuid.UUID
    ) -> Inspection:
        stmt = select(ReturnItem).where(ReturnItem.id == insp_in.return_item_id)
        item = (await db.execute(stmt)).scalar_one_or_none()
        if not item:
            raise ResourceNotFoundError("ReturnItem", str(insp_in.return_item_id))

        # Check existing inspection count to increment version
        stmt_count = select(Inspection).where(Inspection.return_item_id == insp_in.return_item_id)
        existing_inspections = list((await db.execute(stmt_count)).scalars().all())
        version = len(existing_inspections) + 1

        inspection = Inspection(
            return_item_id=insp_in.return_item_id,
            inspector_user_id=inspector_user_id,
            inspection_version=version,
            is_functional=insp_in.is_functional,
            powers_on=insp_in.powers_on,
            screen_condition=insp_in.screen_condition,
            enclosure_condition=insp_in.enclosure_condition,
            battery_health_pct=insp_in.battery_health_pct,
            has_safety_hazard=insp_in.has_safety_hazard,
            safety_hazard_details=insp_in.safety_hazard_details,
            technician_notes=insp_in.technician_notes
        )
        db.add(inspection)

        # Update custody & status
        item.current_custody_location = CustodyLocation.INSPECTION_FACILITY
        stmt_req = select(ReturnRequest).where(ReturnRequest.id == item.return_request_id)
        req = (await db.execute(stmt_req)).scalar_one()
        req.status = ReturnCaseStatus.INSPECTION_IN_PROGRESS

        await db.flush()

        await AuditService.log_event(
            db=db,
            action="INSPECTION_RECORDED",
            entity_name="Inspection",
            entity_id=inspection.id,
            actor_user_id=inspector_user_id,
            new_state={
                "version": version,
                "functional": insp_in.is_functional,
                "safety_hazard": insp_in.has_safety_hazard
            }
        )
        return inspection

    @classmethod
    async def get_inspection(
        cls,
        db: AsyncSession,
        inspection_id: uuid.UUID
    ) -> Inspection:
        stmt = (
            select(Inspection)
            .where(Inspection.id == inspection_id)
            .options(selectinload(Inspection.estimates))
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            raise ResourceNotFoundError("Inspection", str(inspection_id))
        return record
