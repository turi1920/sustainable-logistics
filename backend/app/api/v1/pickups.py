import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.identity import User, UserRole
from backend.app.schemas.returns import PickupAssignRequest, PickupAssignmentRead, PickupVerifyRequest
from backend.app.services.pickup_service import PickupService

router = APIRouter(prefix="/pickups", tags=["Pickups"])


@router.post("/assign", response_model=PickupAssignmentRead, status_code=status.HTTP_201_CREATED)
async def assign_pickup(
    assign_in: PickupAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN))
):
    return await PickupService.assign_pickup(
        db=db,
        assign_in=assign_in,
        assigned_by_user_id=current_user.id
    )


@router.get("/my-tasks", response_model=List[PickupAssignmentRead])
async def list_agent_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.RETURN_AGENT))
):
    """Scoped endpoint: Agents can ONLY see their own assigned pickup tasks."""
    return await PickupService.list_agent_tasks(db=db, agent_user_id=current_user.id)


@router.post("/{assignment_id}/verify", response_model=PickupAssignmentRead)
async def verify_and_collect_pickup(
    assignment_id: uuid.UUID,
    verify_in: PickupVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.RETURN_AGENT))
):
    return await PickupService.verify_and_collect(
        db=db,
        assignment_id=assignment_id,
        verify_in=verify_in,
        agent_user_id=current_user.id
    )
