import asyncio
from datetime import datetime, timezone
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.session import async_session_factory
from backend.app.models.authorization import ApprovalRequest, ApprovalRequestItem, PartnerContract
from backend.app.models.operations import NotificationLog
from backend.app.models.returns import ApprovalStatus, RecoveryClassification, ReturnItem
from backend.app.services.audit_service import AuditService


class TimeoutWorker:
    """Background worker that reliably processes the 5-Day SLA Non-Response workflow.
    Guarantees idempotency so repeated executions do not generate duplicate reminders or actions.
    """

    @classmethod
    async def process_sla_checks(cls, db: AsyncSession) -> int:
        now_utc = datetime.now(timezone.utc)
        
        # Query open approval requests
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.is_closed == False)
            .options(
                selectinload(ApprovalRequest.items).selectinload(ApprovalRequestItem.return_item)
            )
        )
        requests = list((await db.execute(stmt)).scalars().all())
        processed_count = 0

        for req in requests:
            created_at = req.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            elapsed_seconds = (now_utc - created_at).total_seconds()
            elapsed_hours = elapsed_seconds / 3600.0

            deadline = req.deadline_at
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)

            # 1. First Reminder (e.g. at 48 hours)
            if elapsed_hours >= settings.REMINDER_1_HOURS and req.first_reminder_sent_at is None:
                log_1 = NotificationLog(
                    recipient_email="manufacturer-approvals@example.com",
                    subject=f"[REMINDER 1] Pending Authorization Request {req.id}",
                    content=f"Friendly reminder: {len(req.items)} items await your authorization. Deadline: {deadline.isoformat()}",
                    notification_type="SLA_REMINDER_1",
                    reference_id=str(req.id)
                )
                db.add(log_1)
                req.first_reminder_sent_at = now_utc
                processed_count += 1
                logger.info(f"Dispatched 1st SLA reminder for ApprovalRequest {req.id}")

            # 2. Second Reminder (e.g. at 96 hours)
            elif elapsed_hours >= settings.REMINDER_2_HOURS and req.second_reminder_sent_at is None:
                log_2 = NotificationLog(
                    recipient_email="manufacturer-approvals@example.com",
                    subject=f"[URGENT REMINDER 2] Pending Authorization Request {req.id}",
                    content=f"Urgent reminder: Final 24 hours to review {len(req.items)} items. Deadline: {deadline.isoformat()}",
                    notification_type="SLA_REMINDER_2",
                    reference_id=str(req.id)
                )
                db.add(log_2)
                req.second_reminder_sent_at = now_utc
                processed_count += 1
                logger.info(f"Dispatched 2nd SLA reminder for ApprovalRequest {req.id}")

            # 3. Five-Day Deadline Exceeded (>= 120 hours or now >= deadline_at)
            elif now_utc >= deadline:
                # Fetch partner contract
                stmt_contract = select(PartnerContract).where(PartnerContract.manufacturer_org_id == req.manufacturer_org_id)
                contract = (await db.execute(stmt_contract)).scalar_one_or_none()

                auto_return_permitted = contract.auto_return_on_timeout_authorized if contract else False

                for item_req in req.items:
                    if not item_req.is_decided:
                        item = item_req.return_item
                        if auto_return_permitted:
                            # Predefined contract authorizes automatic return to manufacturer
                            item.approval_status = ApprovalStatus.OVERDUE
                            item.recovery_classification = RecoveryClassification.RETURN_TO_MANUFACTURER
                            reason = "5-Day SLA deadline expired with no response. Auto-return initiated per partner contract agreement."
                            action_name = "TIMEOUT_AUTO_RETURN_INITIATED"
                        else:
                            # Not authorized for auto-return -> Secure HOLD & escalation
                            item.approval_status = ApprovalStatus.ESCALATED
                            item.recovery_classification = RecoveryClassification.ON_HOLD
                            reason = "5-Day SLA deadline expired without response. Auto-return not pre-authorized by contract. Item placed ON_HOLD."
                            action_name = "TIMEOUT_ESCALATED_HOLD"

                        item_req.is_decided = True

                        await AuditService.log_event(
                            db=db,
                            action=action_name,
                            entity_name="ReturnItem",
                            entity_id=item.id,
                            reason=reason,
                            new_state={
                                "approval_status": item.approval_status.value,
                                "recovery_classification": item.recovery_classification.value
                            }
                        )

                req.is_closed = True
                processed_count += 1
                logger.info(f"Closed ApprovalRequest {req.id} after 5-day SLA deadline expiration. Auto-return authorized: {auto_return_permitted}")

        await db.flush()
        return processed_count

    @classmethod
    async def run_periodic_worker(cls, stop_event: asyncio.Event):
        """Asynchronous runner that ticks periodically in the background."""
        logger.info("Starting SLA Timeout background worker loop...")
        while not stop_event.is_set():
            try:
                async with async_session_factory() as db:
                    await cls.process_sla_checks(db)
                    await db.commit()
            except Exception as e:
                logger.error(f"Error in SLA Timeout worker loop: {e}", exc_info=True)

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=settings.SLA_CHECK_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass
        logger.info("SLA Timeout background worker stopped.")
