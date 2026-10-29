import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.identity import User, UserRole
from backend.app.schemas.authorization import (
    ApprovalRequestItemRead,
    BatchDecisionSubmit,
    ItemDecisionSubmit,
    PolicyCreate,
    PolicyRead,
)
from backend.app.services.authorization_service import AuthorizationService

router = APIRouter(prefix="/authorizations", tags=["Authorizations"])


@router.post("/policies", response_model=PolicyRead, status_code=status.HTTP_201_CREATED)
async def create_policy(
    policy_in: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANUFACTURER_APPROVER, UserRole.PLATFORM_ADMIN))
):
    return await AuthorizationService.create_policy(
        db=db,
        manufacturer_org_id=current_user.organization_id,
        policy_in=policy_in,
        created_by_user_id=current_user.id
    )


@router.post("/evaluate-policy/{item_id}")
async def evaluate_item_against_policies(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OPERATIONS_SPECIALIST, UserRole.PLATFORM_ADMIN))
):
    """Path A pre-authorization engine check."""
    decision = await AuthorizationService.evaluate_item_against_policies(
        db=db,
        return_item_id=item_id,
        operator_user_id=current_user.id
    )
    if decision:
        return {"status": "PRE_AUTHORIZED", "decision_id": str(decision.id), "reason": decision.decision_reason}
    return {"status": "HUMAN_APPROVAL_REQUIRED", "message": "No active policy matched item conditions."}


@router.get("/pending", response_model=List[ApprovalRequestItemRead])
async def list_pending_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANUFACTURER_APPROVER))
):
    """Multi-tenancy enforced: Manufacturer approver can ONLY view pending items for their own organization."""
    return await AuthorizationService.list_pending_approvals(
        db=db,
        manufacturer_org_id=current_user.organization_id
    )


@router.post("/decide-item")
async def decide_individual_item(
    decision_in: ItemDecisionSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANUFACTURER_APPROVER))
):
    """Path C: Individual item approval."""
    decision = await AuthorizationService.decide_item(
        db=db,
        decision_in=decision_in,
        approver_user_id=current_user.id,
        approver_org_id=current_user.organization_id,
        is_batch=False
    )
    return {"status": "SUCCESS", "decision_id": str(decision.id), "action_approved": decision.action_approved.value}


@router.post("/decide-batch")
async def decide_batch_items(
    batch_in: BatchDecisionSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.MANUFACTURER_APPROVER))
):
    """Path B: Batch approval recording atomic item-level decisions."""
    decisions = await AuthorizationService.decide_batch(
        db=db,
        batch_in=batch_in,
        approver_user_id=current_user.id,
        approver_org_id=current_user.organization_id
    )
    return {
        "status": "SUCCESS",
        "processed_count": len(decisions),
        "decision_ids": [str(d.id) for d in decisions]
    }
