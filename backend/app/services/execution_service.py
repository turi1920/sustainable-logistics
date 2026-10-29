import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.exceptions import DomainException, ResourceNotFoundError, SanitizationGateError, UnauthorizedActionError
from backend.app.domain.sanitization_gate import SanitizationGate
from backend.app.domain.state_machines import StateMachineValidator
from backend.app.models.execution import (
    AuthorizedDisposition,
    QualityCheck,
    RecoveryWorkOrder,
    ReleaseAuthorization,
    SanitizationRecord,
    SanitizationStatus,
    WorkOrderStatus,
)
from backend.app.models.returns import ApprovalStatus, RecoveryClassification, ReturnCaseStatus, ReturnItem, ReturnRequest
from backend.app.schemas.execution import (
    QualityCheckSubmit,
    ReleaseAuthorizationSubmit,
    SanitizationCompleteRequest,
    SanitizationStartRequest,
    WorkOrderCreate,
)
from backend.app.services.audit_service import AuditService


class ExecutionService:
    # 1. Data Sanitization Workflow
    @classmethod
    async def start_sanitization(
        cls,
        db: AsyncSession,
        start_in: SanitizationStartRequest,
        technician_user_id: uuid.UUID
    ) -> SanitizationRecord:
        stmt = select(ReturnItem).where(ReturnItem.id == start_in.return_item_id)
        item = (await db.execute(stmt)).scalar_one_or_none()
        if not item:
            raise ResourceNotFoundError("ReturnItem", str(start_in.return_item_id))

        record = SanitizationRecord(
            return_item_id=item.id,
            technician_user_id=technician_user_id,
            sanitization_status=SanitizationStatus.IN_PROGRESS,
            method=start_in.method,
            verification_tool=start_in.verification_tool
        )
        db.add(record)
        await db.flush()

        await AuditService.log_event(
            db=db,
            action="SANITIZATION_STARTED",
            entity_name="SanitizationRecord",
            entity_id=record.id,
            actor_user_id=technician_user_id,
            new_state={"method": start_in.method.value, "status": SanitizationStatus.IN_PROGRESS.value}
        )
        return record

    @classmethod
    async def complete_sanitization(
        cls,
        db: AsyncSession,
        complete_in: SanitizationCompleteRequest,
        technician_user_id: uuid.UUID
    ) -> SanitizationRecord:
        stmt = (
            select(SanitizationRecord)
            .where(SanitizationRecord.id == complete_in.sanitization_record_id)
            .options(selectinload(SanitizationRecord.return_item))
        )
        record = (await db.execute(stmt)).scalar_one_or_none()
        if not record:
            raise ResourceNotFoundError("SanitizationRecord", str(complete_in.sanitization_record_id))

        now_utc = datetime.now(timezone.utc)
        record.sanitization_status = complete_in.status
        record.completed_at = now_utc
        record.certificate_ref = complete_in.certificate_ref
        record.exception_reason = complete_in.exception_reason

        item = record.return_item
        if complete_in.status == SanitizationStatus.PASSED:
            record.verified_at = now_utc
        elif complete_in.status in [SanitizationStatus.FAILED, SanitizationStatus.EXCEPTION_REVIEW]:
            # Place item on hold
            item.recovery_classification = RecoveryClassification.ON_HOLD

        await db.flush()

        await AuditService.log_event(
            db=db,
            action="SANITIZATION_COMPLETED",
            entity_name="SanitizationRecord",
            entity_id=record.id,
            actor_user_id=technician_user_id,
            new_state={"status": complete_in.status.value, "cert": complete_in.certificate_ref},
            reason=complete_in.exception_reason or "Sanitization finished"
        )
        return record

    # 2. Recovery Work Orders (Repair, Refurbishment, Recycling, Return)
    @classmethod
    async def create_work_order(
        cls,
        db: AsyncSession,
        wo_in: WorkOrderCreate,
        creator_user_id: uuid.UUID
    ) -> RecoveryWorkOrder:
        stmt = select(ReturnItem).where(ReturnItem.id == wo_in.return_item_id)
        item = (await db.execute(stmt)).scalar_one_or_none()
        if not item:
            raise ResourceNotFoundError("ReturnItem", str(wo_in.return_item_id))

        # Check authorization gate: item MUST be approved by policy or human
        authorized_statuses = {
            ApprovalStatus.APPROVED,
            ApprovalStatus.NOT_REQUIRED_POLICY_AUTHORIZED,
        }
        if item.approval_status not in authorized_statuses:
            raise UnauthorizedActionError(
                action=f"CREATE_WORK_ORDER_{wo_in.work_order_type.value}",
                item_id=str(item.id),
                reason=f"Item approval status is '{item.approval_status.value}'. Cannot execute unauthorized recovery work."
            )

        wo = RecoveryWorkOrder(
            return_item_id=item.id,
            facility_id=wo_in.facility_id,
            assigned_technician_id=creator_user_id,
            work_order_type=wo_in.work_order_type,
            status=WorkOrderStatus.IN_PROGRESS,
            work_summary=wo_in.work_summary,
            started_at=datetime.now(timezone.utc)
        )
        db.add(wo)

        stmt_req = select(ReturnRequest).where(ReturnRequest.id == item.return_request_id)
        req = (await db.execute(stmt_req)).scalar_one()
        req.status = ReturnCaseStatus.RECOVERY_IN_PROGRESS

        await db.flush()

        await AuditService.log_event(
            db=db,
            action="WORK_ORDER_CREATED",
            entity_name="RecoveryWorkOrder",
            entity_id=wo.id,
            actor_user_id=creator_user_id,
            new_state={"type": wo_in.work_order_type.value, "status": WorkOrderStatus.IN_PROGRESS.value}
        )
        return wo

    @classmethod
    async def record_quality_check(
        cls,
        db: AsyncSession,
        qc_in: QualityCheckSubmit,
        inspector_user_id: uuid.UUID
    ) -> QualityCheck:
        stmt = (
            select(RecoveryWorkOrder)
            .where(RecoveryWorkOrder.id == qc_in.work_order_id)
            .options(selectinload(RecoveryWorkOrder.return_item))
        )
        wo = (await db.execute(stmt)).scalar_one_or_none()
        if not wo:
            raise ResourceNotFoundError("RecoveryWorkOrder", str(qc_in.work_order_id))

        passed = qc_in.functional_test_passed and qc_in.cosmetic_standard_passed and qc_in.packaging_verified

        qc = QualityCheck(
            work_order_id=wo.id,
            inspector_user_id=inspector_user_id,
            functional_test_passed=qc_in.functional_test_passed,
            cosmetic_standard_passed=qc_in.cosmetic_standard_passed,
            packaging_verified=qc_in.packaging_verified,
            passed=passed,
            defects_observed=qc_in.defects_observed
        )
        db.add(qc)

        if passed:
            wo.status = WorkOrderStatus.COMPLETED
            wo.completed_at = datetime.now(timezone.utc)
        else:
            wo.status = WorkOrderStatus.FAILED

        await db.flush()

        await AuditService.log_event(
            db=db,
            action="QUALITY_CHECK_RECORDED",
            entity_name="QualityCheck",
            entity_id=qc.id,
            actor_user_id=inspector_user_id,
            new_state={"passed": passed, "wo_status": wo.status.value}
        )
        return qc

    # 3. Resale Release Gate
    @classmethod
    async def release_item_for_disposition(
        cls,
        db: AsyncSession,
        release_in: ReleaseAuthorizationSubmit,
        authorizer_user_id: uuid.UUID
    ) -> ReleaseAuthorization:
        stmt = select(ReturnItem).where(ReturnItem.id == release_in.return_item_id)
        item = (await db.execute(stmt)).scalar_one_or_none()
        if not item:
            raise ResourceNotFoundError("ReturnItem", str(release_in.return_item_id))

        # Fetch latest sanitization record directly
        stmt_san = (
            select(SanitizationRecord)
            .where(SanitizationRecord.return_item_id == release_in.return_item_id)
            .order_by(SanitizationRecord.created_at.desc())
        )
        latest_san = (await db.execute(stmt_san)).scalars().first()

        # Hard Gate: Raises SanitizationGateError if resale is attempted without verified PASSED sanitization
        SanitizationGate.verify_release_eligibility(
            item=item,
            target_disposition=release_in.authorized_disposition,
            latest_sanitization=latest_san
        )

        release_auth = ReleaseAuthorization(
            return_item_id=item.id,
            authorized_disposition=release_in.authorized_disposition,
            resale_proceeds_actual=release_in.resale_proceeds_actual,
            verified_sanitization_id=latest_san.id if latest_san else None,
            authorized_by_user_id=authorizer_user_id
        )
        db.add(release_auth)

        # Complete parent return request
        stmt_req = select(ReturnRequest).where(ReturnRequest.id == item.return_request_id)
        req = (await db.execute(stmt_req)).scalar_one()
        req.status = ReturnCaseStatus.COMPLETED

        await db.flush()

        await AuditService.log_event(
            db=db,
            action="ITEM_RELEASED_FOR_DISPOSITION",
            entity_name="ReleaseAuthorization",
            entity_id=release_auth.id,
            actor_user_id=authorizer_user_id,
            new_state={
                "disposition": release_in.authorized_disposition.value,
                "proceeds": str(release_in.resale_proceeds_actual)
            },
            reason="All operational, quality, and data sanitization checks passed successfully."
        )
        return release_auth
