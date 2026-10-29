from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.jobs.timeout_worker import TimeoutWorker
from backend.app.models.execution import RecoveryWorkOrder, ReleaseAuthorization
from backend.app.models.identity import User, UserRole
from backend.app.models.operations import AuditEvent
from backend.app.models.returns import ReturnItem
from backend.app.schemas.operations import AuditEventRead

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


@router.get("/recovery-summary")
async def get_recovery_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(
        UserRole.FINANCE_SUSTAINABILITY_ANALYST,
        UserRole.PLATFORM_ADMIN,
        UserRole.MANUFACTURER_APPROVER
    ))
):
    # Aggregated analytics
    stmt_total_items = select(func.count(ReturnItem.id))
    total_items = (await db.execute(stmt_total_items)).scalar() or 0

    stmt_work_orders = select(
        func.count(RecoveryWorkOrder.id),
        func.sum(RecoveryWorkOrder.actual_parts_cost),
        func.sum(RecoveryWorkOrder.actual_labour_cost)
    )
    res_wo = (await db.execute(stmt_work_orders)).one()
    total_wos = res_wo[0] or 0
    total_parts_cost = res_wo[1] or Decimal("0.00")
    total_labour_cost = res_wo[2] or Decimal("0.00")

    stmt_proceeds = select(func.sum(ReleaseAuthorization.resale_proceeds_actual))
    actual_proceeds = (await db.execute(stmt_proceeds)).scalar() or Decimal("0.00")

    net_financial_outcome = actual_proceeds - (total_parts_cost + total_labour_cost)

    return {
        "total_returned_items": total_items,
        "completed_recovery_orders": total_wos,
        "total_recovery_expenses": float(total_parts_cost + total_labour_cost),
        "total_actual_resale_proceeds": float(actual_proceeds),
        "net_financial_recovery": float(net_financial_outcome),
        "currency": "USD"
    }


@router.get("/audit-events", response_model=List[AuditEventRead])
async def list_audit_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.FINANCE_SUSTAINABILITY_ANALYST))
):
    stmt = select(AuditEvent).offset(skip).limit(limit).order_by(AuditEvent.timestamp.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/trigger-sla-check")
async def trigger_sla_check(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN))
):
    """Admin trigger to execute an immediate SLA check iteration."""
    processed = await TimeoutWorker.process_sla_checks(db)
    return {"status": "SUCCESS", "processed_sla_requests": processed}
