import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.identity import User, UserRole
from backend.app.schemas.assessment import AssessmentReportRead, RecoveryEstimateInput
from backend.app.services.assessment_service import AssessmentService

router = APIRouter(prefix="/assessments", tags=["Assessments & NRV"])


@router.post("/publish/{inspection_id}", response_model=AssessmentReportRead, status_code=status.HTTP_201_CREATED)
async def publish_assessment_report(
    inspection_id: uuid.UUID,
    estimates_in: RecoveryEstimateInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OPERATIONS_SPECIALIST, UserRole.PLATFORM_ADMIN))
):
    """Calculates comparative NRV across eligible recovery routes and publishes the finalized report, triggering the 5-Day SLA clock."""
    return await AssessmentService.calculate_and_publish_report(
        db=db,
        inspection_id=inspection_id,
        estimates_input=estimates_in,
        published_by_user_id=current_user.id
    )


@router.get("/reports/{id}", response_model=AssessmentReportRead)
async def get_assessment_report(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await AssessmentService.get_report(db=db, report_id=id)
