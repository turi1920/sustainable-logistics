import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.identity import User, UserRole
from backend.app.schemas.logistics import (
    CustodyEventCreate,
    CustodyEventRead,
    WarehouseReceiptCreate,
    WarehouseReceiptRead,
)
from backend.app.services.custody_service import CustodyService

router = APIRouter(prefix="/custody", tags=["Custody & Logistics"])


@router.post("/events", response_model=CustodyEventRead, status_code=status.HTTP_201_CREATED)
async def record_custody_transfer(
    event_in: CustodyEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.RETURN_AGENT,
        UserRole.OPERATIONS_SPECIALIST,
        UserRole.PLATFORM_ADMIN
    ))
):
    return await CustodyService.record_custody_transfer(
        db=db,
        event_in=event_in,
        actor_user_id=current_user.id
    )


@router.post("/warehouse-receipt", response_model=WarehouseReceiptRead, status_code=status.HTTP_201_CREATED)
async def receive_at_warehouse(
    receipt_in: WarehouseReceiptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OPERATIONS_SPECIALIST, UserRole.PLATFORM_ADMIN))
):
    return await CustodyService.receive_at_warehouse(
        db=db,
        receipt_in=receipt_in,
        receiver_user_id=current_user.id
    )


@router.get("/items/{item_id}/timeline", response_model=List[CustodyEventRead])
async def get_item_timeline(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await CustodyService.get_timeline(db=db, return_item_id=item_id)
