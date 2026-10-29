import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.identity import User, UserRole
from backend.app.schemas.execution import (
    QualityCheckSubmit,
    ReleaseAuthorizationSubmit,
    SanitizationCompleteRequest,
    SanitizationRecordRead,
    SanitizationStartRequest,
    WorkOrderCreate,
)
from backend.app.services.execution_service import ExecutionService

router = APIRouter(prefix="/executions", tags=["Recovery Execution & Sanitization"])


# 1. Sanitization Endpoints
@router.post("/sanitization/start", response_model=SanitizationRecordRead, status_code=status.HTTP_201_CREATED)
async def start_sanitization(
    start_in: SanitizationStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OPERATIONS_SPECIALIST, UserRole.PLATFORM_ADMIN))
):
    return await ExecutionService.start_sanitization(
        db=db,
        start_in=start_in,
        technician_user_id=current_user.id
    )


@router.post("/sanitization/complete", response_model=SanitizationRecordRead)
async def complete_sanitization(
    complete_in: SanitizationCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OPERATIONS_SPECIALIST, UserRole.PLATFORM_ADMIN))
):
    return await ExecutionService.complete_sanitization(
        db=db,
        complete_in=complete_in,
        technician_user_id=current_user.id
    )


# 2. Work Order Endpoints
@router.post("/work-orders", status_code=status.HTTP_201_CREATED)
async def create_work_order(
    wo_in: WorkOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OPERATIONS_SPECIALIST, UserRole.PLATFORM_ADMIN))
):
    wo = await ExecutionService.create_work_order(
        db=db,
        wo_in=wo_in,
        creator_user_id=current_user.id
    )
    return {"status": "SUCCESS", "work_order_id": str(wo.id), "type": wo.work_order_type.value}


@router.post("/work-orders/quality-check", status_code=status.HTTP_201_CREATED)
async def record_quality_check(
    qc_in: QualityCheckSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OPERATIONS_SPECIALIST, UserRole.PLATFORM_ADMIN))
):
    qc = await ExecutionService.record_quality_check(
        db=db,
        qc_in=qc_in,
        inspector_user_id=current_user.id
    )
    return {"status": "SUCCESS", "qc_id": str(qc.id), "passed": qc.passed}


# 3. Resale Release Gate Endpoint
@router.post("/items/release", status_code=status.HTTP_201_CREATED)
async def release_item_for_disposition(
    release_in: ReleaseAuthorizationSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OPERATIONS_SPECIALIST, UserRole.PLATFORM_ADMIN))
):
    """Enforces the device data sanitization gate. Rejects resale with HTTP 422 if sanitization != PASSED."""
    release = await ExecutionService.release_item_for_disposition(
        db=db,
        release_in=release_in,
        authorizer_user_id=current_user.id
    )
    return {
        "status": "RELEASE_AUTHORIZED",
        "release_id": str(release.id),
        "disposition": release.authorized_disposition.value
    }
