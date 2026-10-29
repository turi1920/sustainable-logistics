import uuid
from datetime import datetime, timezone
from decimal import Decimal
import random
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.exceptions import DomainException, ResourceNotFoundError
from backend.app.models.operations import RefundRecord, RefundStatus
from backend.app.models.returns import (
    ApprovalStatus,
    CustodyLocation,
    RecoveryClassification,
    ReturnCaseStatus,
    ReturnItem,
    ReturnRequest,
)
from backend.app.schemas.returns import ReturnRequestCreate
from backend.app.services.audit_service import AuditService


class ReturnService:
    @staticmethod
    def _generate_case_number() -> str:
        timestamp_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        rand_suffix = f"{random.randint(1000, 9999)}"
        return f"RET-{timestamp_part}-{rand_suffix}"

    @staticmethod
    def _generate_item_tag() -> str:
        rand_tag = f"{random.randint(100000, 999999)}"
        return f"TAG-{rand_tag}"

    @classmethod
    async def create_return_request(
        cls,
        db: AsyncSession,
        request_in: ReturnRequestCreate,
        created_by_user_id: uuid.UUID
    ) -> ReturnRequest:
        # Check duplicate external order reference
        stmt = select(ReturnRequest).where(ReturnRequest.external_order_ref == request_in.external_order_ref)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise DomainException(
                f"A return request already exists for order reference '{request_in.external_order_ref}'.",
                code="DUPLICATE_RETURN_REQUEST"
            )

        case_number = cls._generate_case_number()

        return_request = ReturnRequest(
            case_number=case_number,
            external_order_ref=request_in.external_order_ref,
            customer_name=request_in.customer_name,
            customer_email=request_in.customer_email,
            customer_phone=request_in.customer_phone,
            pickup_address=request_in.pickup_address,
            pickup_city=request_in.pickup_city,
            pickup_postal_code=request_in.pickup_postal_code,
            status=ReturnCaseStatus.RETURN_REQUESTED,
            created_by_user_id=created_by_user_id
        )
        db.add(return_request)
        await db.flush()

        # Add items
        for item_in in request_in.items:
            item_tag = cls._generate_item_tag()
            return_item = ReturnItem(
                return_request_id=return_request.id,
                manufacturer_org_id=item_in.manufacturer_org_id,
                item_tag=item_tag,
                product_name=item_in.product_name,
                product_category=item_in.product_category,
                model_number=item_in.model_number,
                declared_serial_number=item_in.declared_serial_number,
                return_reason=item_in.return_reason,
                recovery_classification=RecoveryClassification.ON_HOLD,
                approval_status=ApprovalStatus.PENDING_APPROVAL,
                current_custody_location=CustodyLocation.WITH_RETURN_AGENT,
                requires_data_sanitization=item_in.requires_data_sanitization
            )
            db.add(return_item)

        # Initialize refund record in PENDING status (Section 13)
        refund_record = RefundRecord(
            return_request_id=return_request.id,
            refund_amount=Decimal("0.00"),
            status=RefundStatus.PENDING,
            manual_processing_notes="Refund pending warehouse receipt and condition assessment."
        )
        db.add(refund_record)
        await db.flush()

        await db.flush()
        await db.refresh(return_request, ["items"])

        # Audit log
        await AuditService.log_event(
            db=db,
            action="RETURN_REGISTERED",
            entity_name="ReturnRequest",
            entity_id=return_request.id,
            actor_user_id=created_by_user_id,
            new_state={"case_number": case_number, "items_count": len(request_in.items)},
            reason="Manual return registration"
        )

        return return_request

    @classmethod
    async def get_return_request(
        cls,
        db: AsyncSession,
        request_id: uuid.UUID
    ) -> ReturnRequest:
        stmt = (
            select(ReturnRequest)
            .where(ReturnRequest.id == request_id)
            .options(selectinload(ReturnRequest.items))
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            raise ResourceNotFoundError("ReturnRequest", str(request_id))
        return record

    @classmethod
    async def list_return_requests(
        cls,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        status_filter: Optional[ReturnCaseStatus] = None
    ) -> List[ReturnRequest]:
        stmt = select(ReturnRequest).options(selectinload(ReturnRequest.items))
        if status_filter:
            stmt = stmt.where(ReturnRequest.status == status_filter)
        stmt = stmt.offset(skip).limit(limit).order_by(ReturnRequest.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())
