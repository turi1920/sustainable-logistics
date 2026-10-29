import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.exceptions import ResourceNotFoundError
from backend.app.domain.state_machines import StateMachineValidator
from backend.app.models.operations import RefundRecord, RefundStatus
from backend.app.schemas.operations import RefundUpdate
from backend.app.services.audit_service import AuditService


class RefundService:
    @classmethod
    async def update_refund(
        cls,
        db: AsyncSession,
        refund_id: uuid.UUID,
        update_in: RefundUpdate,
        operator_user_id: uuid.UUID
    ) -> RefundRecord:
        stmt = select(RefundRecord).where(RefundRecord.id == refund_id)
        refund = (await db.execute(stmt)).scalar_one_or_none()
        if not refund:
            raise ResourceNotFoundError("RefundRecord", str(refund_id))

        StateMachineValidator.validate_refund_transition(
            current=refund.status,
            attempted=update_in.status,
            item_id=str(refund.return_request_id)
        )

        now_utc = datetime.now(timezone.utc)
        if update_in.status == RefundStatus.INITIATED and not refund.initiated_at:
            refund.initiated_at = now_utc
        elif update_in.status == RefundStatus.COMPLETED:
            refund.completed_at = now_utc

        refund.status = update_in.status
        if update_in.external_payout_ref:
            refund.external_payout_ref = update_in.external_payout_ref
        if update_in.manual_processing_notes:
            refund.manual_processing_notes = update_in.manual_processing_notes

        await db.flush()

        await AuditService.log_event(
            db=db,
            action="REFUND_STATUS_UPDATED",
            entity_name="RefundRecord",
            entity_id=refund.id,
            actor_user_id=operator_user_id,
            new_state={
                "status": update_in.status.value,
                "external_ref": update_in.external_payout_ref
            },
            reason=update_in.manual_processing_notes or "Manual refund status update"
        )
        return refund

    @classmethod
    async def get_by_request_id(
        cls,
        db: AsyncSession,
        return_request_id: uuid.UUID
    ) -> Optional[RefundRecord]:
        stmt = select(RefundRecord).where(RefundRecord.return_request_id == return_request_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
