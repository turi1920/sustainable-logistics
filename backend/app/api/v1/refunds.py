import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.identity import User, UserRole
from backend.app.schemas.operations import RefundRead, RefundUpdate
from backend.app.services.refund_service import RefundService

router = APIRouter(prefix="/refunds", tags=["Refunds"])


@router.patch("/{id}", response_model=RefundRead)
async def update_refund(
    id: uuid.UUID,
    update_in: RefundUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FINANCE_SUSTAINABILITY_ANALYST, UserRole.PLATFORM_ADMIN))
):
    return await RefundService.update_refund(
        db=db,
        refund_id=id,
        update_in=update_in,
        operator_user_id=current_user.id
    )


@router.get("/by-request/{request_id}", response_model=RefundRead)
async def get_refund_by_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await RefundService.get_by_request_id(db=db, return_request_id=request_id)
