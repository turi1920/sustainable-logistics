import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.identity import User, UserRole
from backend.app.schemas.assessment import InspectionCreate, InspectionRead
from backend.app.services.inspection_service import InspectionService

router = APIRouter(prefix="/inspections", tags=["Inspections"])


@router.post("", response_model=InspectionRead, status_code=status.HTTP_201_CREATED)
async def record_inspection(
    insp_in: InspectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OPERATIONS_SPECIALIST, UserRole.PLATFORM_ADMIN))
):
    return await InspectionService.record_inspection(
        db=db,
        insp_in=insp_in,
        inspector_user_id=current_user.id
    )


@router.get("/{id}", response_model=InspectionRead)
async def get_inspection(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await InspectionService.get_inspection(db=db, inspection_id=id)
