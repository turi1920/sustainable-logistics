import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.identity import User, UserRole
from backend.app.models.returns import ReturnCaseStatus
from backend.app.schemas.returns import ReturnRequestCreate, ReturnRequestRead
from backend.app.services.return_service import ReturnService

router = APIRouter(prefix="/returns", tags=["Returns"])


@router.post("", response_model=ReturnRequestRead, status_code=status.HTTP_201_CREATED)
async def create_return_request(
    request_in: ReturnRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN))
):
    """Admin-only manual return intake (designed to accept future ecommerce webhooks cleanly)."""
    return await ReturnService.create_return_request(
        db=db,
        request_in=request_in,
        created_by_user_id=current_user.id
    )


@router.get("", response_model=List[ReturnRequestRead])
async def list_return_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[ReturnCaseStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.PLATFORM_ADMIN,
        UserRole.OPERATIONS_SPECIALIST,
        UserRole.FINANCE_SUSTAINABILITY_ANALYST
    ))
):
    return await ReturnService.list_return_requests(
        db=db,
        skip=skip,
        limit=limit,
        status_filter=status_filter
    )


@router.get("/{id}", response_model=ReturnRequestRead)
async def get_return_request(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await ReturnService.get_return_request(db=db, request_id=id)
