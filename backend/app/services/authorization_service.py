import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.exceptions import DomainException, ResourceNotFoundError, UnauthorizedActionError
from backend.app.domain.policy_engine import PolicyEngine
from backend.app.models.assessment import AssessmentReport
from backend.app.models.authorization import (
    ApprovalRequest,
    ApprovalRequestItem,
    ApproverAction,
    AuthorizationDecision,
    AuthorizationPolicy,
    DecisionPath,
)
from backend.app.models.returns import ApprovalStatus, RecoveryClassification, ReturnItem
from backend.app.schemas.authorization import BatchDecisionSubmit, ItemDecisionSubmit, PolicyCreate
from backend.app.services.audit_service import AuditService


class AuthorizationService:
    @classmethod
    async def create_policy(
        cls,
        db: AsyncSession,
        manufacturer_org_id: uuid.UUID,
        policy_in: PolicyCreate,
        created_by_user_id: uuid.UUID
    ) -> AuthorizationPolicy:
        policy = AuthorizationPolicy(
            manufacturer_org_id=manufacturer_org_id,
            policy_code=policy_in.policy_code,
            description=policy_in.description,
            product_category=policy_in.product_category,
            permitted_action=policy_in.permitted_action,
            max_repair_cost_threshold=policy_in.max_repair_cost_threshold,
            min_expected_nrv_threshold=policy_in.min_expected_nrv_threshold,
            requires_safety_pass=policy_in.requires_safety_pass,
            valid_from=policy_in.valid_from,
            valid_to=policy_in.valid_to
        )
        db.add(policy)
        await db.flush()

        await AuditService.log_event(
            db=db,
            action="AUTHORIZATION_POLICY_CREATED",
            entity_name="AuthorizationPolicy",
            entity_id=policy.id,
            actor_user_id=created_by_user_id,
            new_state={"code": policy_in.policy_code, "action": policy_in.permitted_action.value}
        )
        return policy

    @classmethod
    async def evaluate_item_against_policies(
        cls,
        db: AsyncSession,
        return_item_id: uuid.UUID,
        operator_user_id: uuid.UUID
    ) -> Optional[AuthorizationDecision]:
        """Path A: Checks whether active manufacturer policies can pre-authorize the item's recommended action."""
        stmt = (
            select(ReturnItem)
            .where(ReturnItem.id == return_item_id)
            .options(
                selectinload(ReturnItem.assessment_reports),
                selectinload(ReturnItem.inspections)
            )
        )
        item = (await db.execute(stmt)).scalar_one_or_none()
        if not item:
            raise ResourceNotFoundError("ReturnItem", str(return_item_id))

        latest_report = next((r for r in item.assessment_reports if r.is_latest), None)
        if not latest_report:
            raise DomainException("Item has no published assessment report to authorize.", code="MISSING_REPORT")

        latest_inspection = next((i for i in item.inspections if i.inspection_version == latest_report.report_version), None)
        has_safety = latest_inspection.has_safety_hazard if latest_inspection else False

        # Extract costs from snapshot
        calc_snapshot = latest_report.calculation_snapshot
        options = calc_snapshot.get("options", [])
        recommended_opt_data = next((o for o in options if o["option_type"] == latest_report.recommended_option.value), {})
        
        parts_cost = Decimal(str(recommended_opt_data.get("parts_cost", "0.00")))
        labour_cost = Decimal(str(recommended_opt_data.get("labour_cost", "0.00")))
        total_repair_cost = parts_cost + labour_cost
        estimated_nrv = Decimal(str(recommended_opt_data.get("net_recovery_value", "0.00")))

        # Fetch active policies for manufacturer
        stmt_policies = (
            select(AuthorizationPolicy)
            .where(
                AuthorizationPolicy.manufacturer_org_id == item.manufacturer_org_id,
                AuthorizationPolicy.is_active == True
            )
        )
        policies = list((await db.execute(stmt_policies)).scalars().all())

        eval_result = PolicyEngine.evaluate(
            policies=policies,
            recommended_action=latest_report.recommended_option,
            product_category=item.product_category,
            estimated_repair_cost=total_repair_cost,
            estimated_nrv=estimated_nrv,
            has_safety_hazard=has_safety
        )

        if eval_result.is_authorized and eval_result.matching_policy:
            # Locate pending approval request item
            stmt_item = (
                select(ApprovalRequestItem)
                .where(
                    ApprovalRequestItem.return_item_id == item.id,
                    ApprovalRequestItem.assessment_report_id == latest_report.id,
                    ApprovalRequestItem.is_decided == False
                )
            )
            req_item = (await db.execute(stmt_item)).scalar_one_or_none()
            if req_item:
                decision = AuthorizationDecision(
                    approval_request_item_id=req_item.id,
                    policy_id=eval_result.matching_policy.id,
                    decision_path=DecisionPath.POLICY_PRE_AUTHORIZED,
                    action_approved=latest_report.recommended_option,
                    decision_reason=eval_result.reason
                )
                db.add(decision)
                req_item.is_decided = True

                item.approval_status = ApprovalStatus.NOT_REQUIRED_POLICY_AUTHORIZED
                await db.flush()

                await AuditService.log_event(
                    db=db,
                    action="POLICY_PRE_AUTHORIZED",
                    entity_name="ReturnItem",
                    entity_id=item.id,
                    actor_user_id=operator_user_id,
                    new_state={"status": item.approval_status.value, "policy": eval_result.matching_policy.policy_code},
                    reason=eval_result.reason
                )
                return decision

        return None

    @classmethod
    async def decide_item(
        cls,
        db: AsyncSession,
        decision_in: ItemDecisionSubmit,
        approver_user_id: uuid.UUID,
        approver_org_id: uuid.UUID,
        is_batch: bool = False
    ) -> AuthorizationDecision:
        """Path B & C: Human individual or batch item approval decision."""
        stmt = (
            select(ApprovalRequestItem)
            .where(ApprovalRequestItem.id == decision_in.approval_request_item_id)
            .options(
                selectinload(ApprovalRequestItem.return_item),
                selectinload(ApprovalRequestItem.approval_request)
            )
        )
        req_item = (await db.execute(stmt)).scalar_one_or_none()
        if not req_item:
            raise ResourceNotFoundError("ApprovalRequestItem", str(decision_in.approval_request_item_id))

        if req_item.is_decided:
            raise DomainException("This approval item has already been decided.", code="ALREADY_DECIDED")

        # Multi-tenancy check: Approver must belong to the item's manufacturer org
        if req_item.approval_request.manufacturer_org_id != approver_org_id:
            raise UnauthorizedActionError(
                action="DECIDE_APPROVAL",
                item_id=str(req_item.return_item_id),
                reason="Approver organization does not match the product manufacturer."
            )

        item = req_item.return_item
        decision_path = DecisionPath.BATCH_HUMAN_APPROVAL if is_batch else DecisionPath.INDIVIDUAL_HUMAN_APPROVAL

        if decision_in.action == ApproverAction.APPROVE:
            approved_action = decision_in.approved_recovery_option or item.recovery_classification
            item.approval_status = ApprovalStatus.APPROVED
            item.recovery_classification = approved_action
        elif decision_in.action == ApproverAction.REJECT:
            approved_action = RecoveryClassification.ON_HOLD
            item.approval_status = ApprovalStatus.REJECTED
            item.recovery_classification = RecoveryClassification.ON_HOLD
        else: # REQUEST_MORE_INFORMATION
            approved_action = RecoveryClassification.ON_HOLD
            item.approval_status = ApprovalStatus.PENDING_APPROVAL
            item.recovery_classification = RecoveryClassification.ON_HOLD

        decision = AuthorizationDecision(
            approval_request_item_id=req_item.id,
            decided_by_user_id=approver_user_id,
            decision_path=decision_path,
            action_approved=approved_action,
            decision_reason=decision_in.decision_reason
        )
        db.add(decision)
        req_item.is_decided = True
        await db.flush()

        await AuditService.log_event(
            db=db,
            action="MANUFACTURER_DECISION_RECORDED",
            entity_name="ReturnItem",
            entity_id=item.id,
            actor_user_id=approver_user_id,
            new_state={
                "action": decision_in.action.value,
                "approved_disposition": approved_action.value,
                "path": decision_path.value
            },
            reason=decision_in.decision_reason
        )
        return decision

    @classmethod
    async def decide_batch(
        cls,
        db: AsyncSession,
        batch_in: BatchDecisionSubmit,
        approver_user_id: uuid.UUID,
        approver_org_id: uuid.UUID
    ) -> List[AuthorizationDecision]:
        """Processes multiple items in a batch with atomic transactions and individual audit records."""
        results = []
        for item_decision in batch_in.items:
            decision = await cls.decide_item(
                db=db,
                decision_in=item_decision,
                approver_user_id=approver_user_id,
                approver_org_id=approver_org_id,
                is_batch=True
            )
            results.append(decision)
        return results

    @classmethod
    async def list_pending_approvals(
        cls,
        db: AsyncSession,
        manufacturer_org_id: uuid.UUID
    ) -> List[ApprovalRequestItem]:
        stmt = (
            select(ApprovalRequestItem)
            .join(ApprovalRequestItem.approval_request)
            .where(
                ApprovalRequest.manufacturer_org_id == manufacturer_org_id,
                ApprovalRequestItem.is_decided == False
            )
            .options(
                selectinload(ApprovalRequestItem.return_item),
                selectinload(ApprovalRequestItem.approval_request)
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
