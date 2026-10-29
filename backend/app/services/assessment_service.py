import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.config import settings
from backend.app.core.exceptions import ResourceNotFoundError
from backend.app.domain.nrv_calculator import NRVCalculator, OptionEconomics
from backend.app.models.assessment import AssessmentReport, Inspection, RecoveryEstimate
from backend.app.models.authorization import ApprovalRequest, ApprovalRequestItem
from backend.app.models.returns import ApprovalStatus, RecoveryClassification, ReturnCaseStatus, ReturnItem, ReturnRequest
from backend.app.schemas.assessment import RecoveryEstimateInput
from backend.app.services.audit_service import AuditService


class AssessmentService:
    @classmethod
    async def calculate_and_publish_report(
        cls,
        db: AsyncSession,
        inspection_id: uuid.UUID,
        estimates_input: RecoveryEstimateInput,
        published_by_user_id: uuid.UUID
    ) -> AssessmentReport:
        stmt = (
            select(Inspection)
            .where(Inspection.id == inspection_id)
            .options(selectinload(Inspection.return_item))
        )
        inspection = (await db.execute(stmt)).scalar_one_or_none()
        if not inspection:
            raise ResourceNotFoundError("Inspection", str(inspection_id))

        item = inspection.return_item

        # Compute all 5 recovery options using NRVCalculator
        opt_repair = NRVCalculator.calculate_repair_nrv(
            expected_resale_value=estimates_input.expected_resale_value,
            parts_cost=estimates_input.parts_cost,
            labour_cost=estimates_input.labour_cost,
            packaging_cost=estimates_input.packaging_cost,
            transportation_cost=estimates_input.transportation_cost,
            sanitization_cost=estimates_input.sanitization_cost,
            requires_sanitization=item.requires_data_sanitization
        )

        opt_refurb = NRVCalculator.calculate_refurbishment_nrv(
            expected_resale_value=estimates_input.expected_resale_value,
            parts_cost=estimates_input.parts_cost,
            labour_cost=estimates_input.labour_cost,
            packaging_cost=estimates_input.packaging_cost,
            transportation_cost=estimates_input.transportation_cost,
            sanitization_cost=estimates_input.sanitization_cost,
            requires_sanitization=item.requires_data_sanitization
        )

        opt_resale_new = NRVCalculator.calculate_resale_as_new_nrv(
            expected_resale_value=estimates_input.expected_resale_value,
            packaging_cost=estimates_input.packaging_cost,
            transportation_cost=estimates_input.transportation_cost,
            sanitization_cost=estimates_input.sanitization_cost,
            is_contractually_eligible=estimates_input.is_open_box_resale_eligible and inspection.is_functional and not inspection.has_safety_hazard,
            requires_sanitization=item.requires_data_sanitization
        )

        opt_mfg_return = NRVCalculator.calculate_manufacturer_return_value(
            applicable_return_credit=estimates_input.applicable_return_credit,
            remaining_return_shipping_cost=estimates_input.remaining_return_shipping_cost
        )

        opt_recycle = NRVCalculator.calculate_recycling_value(
            transportation_cost=estimates_input.transportation_cost
        )

        all_options = [opt_repair, opt_refurb, opt_resale_new, opt_mfg_return, opt_recycle]

        # Evaluate against safety hazards and select optimal recommendation
        eval_result = NRVCalculator.evaluate_all(
            has_safety_hazard=inspection.has_safety_hazard,
            options=all_options
        )

        # Persist RecoveryEstimate rows
        for opt in all_options:
            db_estimate = RecoveryEstimate(
                inspection_id=inspection.id,
                option_type=opt.option_type,
                is_technically_eligible=opt.is_eligible,
                ineligibility_reason=opt.ineligibility_reason,
                expected_resale_value=opt.expected_resale_value,
                parts_cost=opt.parts_cost,
                labour_cost=opt.labour_cost,
                packaging_cost=opt.packaging_cost,
                transportation_cost=opt.transportation_cost,
                sanitization_cost=opt.sanitization_cost,
                applicable_return_credit=opt.applicable_return_credit,
                remaining_return_shipping_cost=opt.remaining_return_shipping_cost,
                net_recovery_value=opt.net_recovery_value,
                currency="USD"
            )
            db.add(db_estimate)

        # Version handling for AssessmentReport
        stmt_reports = select(AssessmentReport).where(AssessmentReport.return_item_id == item.id)
        existing_reports = list((await db.execute(stmt_reports)).scalars().all())
        for rep in existing_reports:
            rep.is_latest = False

        new_version = len(existing_reports) + 1
        now_utc = datetime.now(timezone.utc)
        deadline = now_utc + timedelta(days=settings.SLA_TIMEOUT_DAYS)

        # Serialized calculation snapshot
        snapshot = {
            "version": new_version,
            "calculated_at": now_utc.isoformat(),
            "recommended_option": eval_result.recommended_option.value,
            "rationale": eval_result.recommendation_rationale,
            "options": [opt.model_dump(mode="json") for opt in all_options]
        }

        report = AssessmentReport(
            return_item_id=item.id,
            report_version=new_version,
            recommended_option=eval_result.recommended_option,
            recommendation_rationale=eval_result.recommendation_rationale,
            calculation_snapshot=snapshot,
            is_latest=True,
            approval_deadline=deadline
        )
        db.add(report)
        await db.flush()

        # Update item classification & approval status
        item.recovery_classification = eval_result.recommended_option
        item.approval_status = ApprovalStatus.PENDING_APPROVAL

        stmt_req = select(ReturnRequest).where(ReturnRequest.id == item.return_request_id)
        req = (await db.execute(stmt_req)).scalar_one()
        req.status = ReturnCaseStatus.ASSESSED

        # Create ApprovalRequest & item for manufacturer approval workflow
        approval_req = ApprovalRequest(
            manufacturer_org_id=item.manufacturer_org_id,
            deadline_at=deadline
        )
        db.add(approval_req)
        await db.flush()

        approval_item = ApprovalRequestItem(
            approval_request_id=approval_req.id,
            return_item_id=item.id,
            assessment_report_id=report.id
        )
        db.add(approval_item)
        await db.flush()

        await AuditService.log_event(
            db=db,
            action="ASSESSMENT_REPORT_PUBLISHED",
            entity_name="AssessmentReport",
            entity_id=report.id,
            actor_user_id=published_by_user_id,
            new_state={
                "version": new_version,
                "recommended_option": eval_result.recommended_option.value,
                "deadline": deadline.isoformat()
            },
            reason="Completed technical assessment and recovery calculation"
        )
        return report

    @classmethod
    async def get_report(
        cls,
        db: AsyncSession,
        report_id: uuid.UUID
    ) -> AssessmentReport:
        stmt = select(AssessmentReport).where(AssessmentReport.id == report_id)
        report = (await db.execute(stmt)).scalar_one_or_none()
        if not report:
            raise ResourceNotFoundError("AssessmentReport", str(report_id))
        return report
