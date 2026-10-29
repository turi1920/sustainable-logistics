import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.exceptions import DomainException, ResourceNotFoundError
from backend.app.domain.state_machines import StateMachineValidator
from backend.app.models.logistics import CustodyEvent, CustodyEventType
from backend.app.models.returns import (
    CustodyLocation,
    DamageClassification,
    PickupAssignment,
    ReturnCaseStatus,
    ReturnItem,
    ReturnRequest,
    VerificationOutcome,
)
from backend.app.schemas.returns import PickupAssignRequest, PickupVerifyRequest
from backend.app.services.audit_service import AuditService


class PickupService:
    @classmethod
    async def assign_pickup(
        cls,
        db: AsyncSession,
        assign_in: PickupAssignRequest,
        assigned_by_user_id: uuid.UUID
    ) -> PickupAssignment:
        # Check return item exists
        stmt = select(ReturnItem).where(ReturnItem.id == assign_in.return_item_id)
        item = (await db.execute(stmt)).scalar_one_or_none()
        if not item:
            raise ResourceNotFoundError("ReturnItem", str(assign_in.return_item_id))

        # Check existing assignment
        stmt_assign = select(PickupAssignment).where(PickupAssignment.return_item_id == assign_in.return_item_id)
        existing = (await db.execute(stmt_assign)).scalar_one_or_none()
        if existing:
            existing.agent_user_id = assign_in.agent_user_id
            existing.scheduled_date = assign_in.scheduled_date
            assignment = existing
        else:
            assignment = PickupAssignment(
                return_item_id=assign_in.return_item_id,
                agent_user_id=assign_in.agent_user_id,
                scheduled_date=assign_in.scheduled_date
            )
            db.add(assignment)

        # Update parent return request status
        stmt_req = select(ReturnRequest).where(ReturnRequest.id == item.return_request_id)
        parent_req = (await db.execute(stmt_req)).scalar_one_or_none()
        if parent_req and parent_req.status == ReturnCaseStatus.RETURN_REQUESTED:
            StateMachineValidator.validate_return_case_transition(
                parent_req.status, ReturnCaseStatus.PICKUP_ASSIGNED, str(item.id)
            )
            parent_req.status = ReturnCaseStatus.PICKUP_ASSIGNED

        await db.flush()

        await AuditService.log_event(
            db=db,
            action="PICKUP_ASSIGNED",
            entity_name="PickupAssignment",
            entity_id=assignment.id,
            actor_user_id=assigned_by_user_id,
            new_state={"agent_id": str(assign_in.agent_user_id), "date": str(assign_in.scheduled_date)}
        )
        return assignment

    @classmethod
    async def verify_and_collect(
        cls,
        db: AsyncSession,
        assignment_id: uuid.UUID,
        verify_in: PickupVerifyRequest,
        agent_user_id: uuid.UUID
    ) -> PickupAssignment:
        stmt = (
            select(PickupAssignment)
            .where(PickupAssignment.id == assignment_id)
            .options(selectinload(PickupAssignment.return_item))
        )
        assignment = (await db.execute(stmt)).scalar_one_or_none()
        if not assignment:
            raise ResourceNotFoundError("PickupAssignment", str(assignment_id))

        if assignment.agent_user_id != agent_user_id:
            raise DomainException("You can only verify pickups assigned to your account.", code="UNAUTHORIZED_PICKUP_AGENT")

        item = assignment.return_item
        stmt_req = select(ReturnRequest).where(ReturnRequest.id == item.return_request_id)
        parent_req = (await db.execute(stmt_req)).scalar_one()

        assignment.completed_at = datetime.now(timezone.utc)
        assignment.initial_damage = verify_in.initial_damage
        assignment.verification_outcome = verify_in.verification_outcome
        assignment.verification_notes = verify_in.verification_notes
        assignment.agent_signature_ref = verify_in.agent_signature_ref

        if verify_in.verified_serial_number:
            item.verified_serial_number = verify_in.verified_serial_number

        if verify_in.verification_outcome == VerificationOutcome.VERIFIED:
            # Collection successful
            parent_req.status = ReturnCaseStatus.PICKED_UP
            item.current_custody_location = CustodyLocation.WITH_RETURN_AGENT
            
            # Record custody event
            custody_event = CustodyEvent(
                return_item_id=item.id,
                actor_user_id=agent_user_id,
                event_type=CustodyEventType.PICKUP_COLLECTION,
                from_location=f"Customer ({parent_req.pickup_city})",
                to_location="With Return Agent",
                notes=f"Product verified matching tag {item.item_tag}. Initial damage: {verify_in.initial_damage.value}"
            )
            db.add(custody_event)
        else:
            # Mismatch or unable to verify -> Exception hold
            parent_req.status = ReturnCaseStatus.ON_HOLD
            item.current_custody_location = CustodyLocation.WITH_RETURN_AGENT
            
            await AuditService.log_event(
                db=db,
                action="PICKUP_VERIFICATION_EXCEPTION",
                entity_name="ReturnItem",
                entity_id=item.id,
                actor_user_id=agent_user_id,
                reason=f"Verification {verify_in.verification_outcome.value}: {verify_in.verification_notes}"
            )

        await db.flush()
        return assignment

    @classmethod
    async def list_agent_tasks(
        cls,
        db: AsyncSession,
        agent_user_id: uuid.UUID
    ) -> List[PickupAssignment]:
        stmt = (
            select(PickupAssignment)
            .where(PickupAssignment.agent_user_id == agent_user_id)
            .options(selectinload(PickupAssignment.return_item))
            .order_by(PickupAssignment.scheduled_date.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
