from typing import Set, Tuple
from backend.app.core.exceptions import InvalidStateTransitionError
from backend.app.models.execution import SanitizationStatus, WorkOrderStatus
from backend.app.models.operations import RefundStatus
from backend.app.models.returns import (
    ApprovalStatus,
    CustodyLocation,
    RecoveryClassification,
    ReturnCaseStatus,
)


class StateMachineValidator:
    """Validates state transitions across the 6 independent reverse logistics lifecycle dimensions.
    Enforces that invalid state transitions raise InvalidStateTransitionError and cannot be forced.
    """

    # 1. Return Case Lifecycle
    VALID_RETURN_CASE_TRANSITIONS: Set[Tuple[ReturnCaseStatus, ReturnCaseStatus]] = {
        (ReturnCaseStatus.RETURN_REQUESTED, ReturnCaseStatus.PICKUP_ASSIGNED),
        (ReturnCaseStatus.RETURN_REQUESTED, ReturnCaseStatus.CANCELLED),
        (ReturnCaseStatus.PICKUP_ASSIGNED, ReturnCaseStatus.PICKED_UP),
        (ReturnCaseStatus.PICKUP_ASSIGNED, ReturnCaseStatus.ON_HOLD),
        (ReturnCaseStatus.PICKED_UP, ReturnCaseStatus.IN_TRANSIT),
        (ReturnCaseStatus.IN_TRANSIT, ReturnCaseStatus.WAREHOUSE_RECEIVED),
        (ReturnCaseStatus.WAREHOUSE_RECEIVED, ReturnCaseStatus.INSPECTION_IN_PROGRESS),
        (ReturnCaseStatus.INSPECTION_IN_PROGRESS, ReturnCaseStatus.ASSESSED),
        (ReturnCaseStatus.ASSESSED, ReturnCaseStatus.RECOVERY_IN_PROGRESS),
        (ReturnCaseStatus.ASSESSED, ReturnCaseStatus.ON_HOLD),
        (ReturnCaseStatus.RECOVERY_IN_PROGRESS, ReturnCaseStatus.COMPLETED),
        (ReturnCaseStatus.RECOVERY_IN_PROGRESS, ReturnCaseStatus.ON_HOLD),
        (ReturnCaseStatus.ON_HOLD, ReturnCaseStatus.RECOVERY_IN_PROGRESS),
        (ReturnCaseStatus.ON_HOLD, ReturnCaseStatus.COMPLETED),
        (ReturnCaseStatus.ON_HOLD, ReturnCaseStatus.CANCELLED),
    }

    # 2. Approval Status Transitions
    VALID_APPROVAL_TRANSITIONS: Set[Tuple[ApprovalStatus, ApprovalStatus]] = {
        (ApprovalStatus.PENDING_APPROVAL, ApprovalStatus.NOT_REQUIRED_POLICY_AUTHORIZED),
        (ApprovalStatus.PENDING_APPROVAL, ApprovalStatus.APPROVED),
        (ApprovalStatus.PENDING_APPROVAL, ApprovalStatus.REJECTED),
        (ApprovalStatus.PENDING_APPROVAL, ApprovalStatus.OVERDUE),
        (ApprovalStatus.OVERDUE, ApprovalStatus.ESCALATED),
        (ApprovalStatus.OVERDUE, ApprovalStatus.APPROVED),
        (ApprovalStatus.OVERDUE, ApprovalStatus.REJECTED),
        (ApprovalStatus.ESCALATED, ApprovalStatus.APPROVED),
        (ApprovalStatus.ESCALATED, ApprovalStatus.REJECTED),
        (ApprovalStatus.REJECTED, ApprovalStatus.PENDING_APPROVAL), # If re-assessed
    }

    # 3. Sanitization Status Transitions
    VALID_SANITIZATION_TRANSITIONS: Set[Tuple[SanitizationStatus, SanitizationStatus]] = {
        (SanitizationStatus.NOT_STARTED, SanitizationStatus.IN_PROGRESS),
        (SanitizationStatus.IN_PROGRESS, SanitizationStatus.PASSED),
        (SanitizationStatus.IN_PROGRESS, SanitizationStatus.FAILED),
        (SanitizationStatus.IN_PROGRESS, SanitizationStatus.EXCEPTION_REVIEW),
        (SanitizationStatus.FAILED, SanitizationStatus.EXCEPTION_REVIEW),
        (SanitizationStatus.FAILED, SanitizationStatus.IN_PROGRESS), # Retry wipe
        (SanitizationStatus.EXCEPTION_REVIEW, SanitizationStatus.PASSED), # Physical destruction / cert
        (SanitizationStatus.EXCEPTION_REVIEW, SanitizationStatus.FAILED),
    }

    # 4. Custody Location Transitions
    VALID_CUSTODY_TRANSITIONS: Set[Tuple[CustodyLocation, CustodyLocation]] = {
        (CustodyLocation.WITH_RETURN_AGENT, CustodyLocation.IN_TRANSIT),
        (CustodyLocation.IN_TRANSIT, CustodyLocation.WAREHOUSE),
        (CustodyLocation.WAREHOUSE, CustodyLocation.INSPECTION_FACILITY),
        (CustodyLocation.INSPECTION_FACILITY, CustodyLocation.WAREHOUSE),
        (CustodyLocation.WAREHOUSE, CustodyLocation.REPAIR_FACILITY),
        (CustodyLocation.REPAIR_FACILITY, CustodyLocation.WAREHOUSE),
        (CustodyLocation.WAREHOUSE, CustodyLocation.WITH_CARRIER),
        (CustodyLocation.WITH_CARRIER, CustodyLocation.DELIVERED_TO_MANUFACTURER),
    }

    # 5. Work Order Transitions
    VALID_WORK_ORDER_TRANSITIONS: Set[Tuple[WorkOrderStatus, WorkOrderStatus]] = {
        (WorkOrderStatus.PENDING, WorkOrderStatus.IN_PROGRESS),
        (WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.QUALITY_CHECK),
        (WorkOrderStatus.QUALITY_CHECK, WorkOrderStatus.COMPLETED),
        (WorkOrderStatus.QUALITY_CHECK, WorkOrderStatus.IN_PROGRESS), # Rework
        (WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.FAILED),
        (WorkOrderStatus.QUALITY_CHECK, WorkOrderStatus.FAILED),
    }

    # 6. Refund Status Transitions
    VALID_REFUND_TRANSITIONS: Set[Tuple[RefundStatus, RefundStatus]] = {
        (RefundStatus.NOT_APPLICABLE, RefundStatus.PENDING),
        (RefundStatus.PENDING, RefundStatus.INITIATED),
        (RefundStatus.PENDING, RefundStatus.NOT_APPLICABLE),
        (RefundStatus.INITIATED, RefundStatus.PROCESSING),
        (RefundStatus.PROCESSING, RefundStatus.COMPLETED),
        (RefundStatus.PROCESSING, RefundStatus.FAILED),
        (RefundStatus.FAILED, RefundStatus.INITIATED), # Retry payout
    }

    @classmethod
    def validate_return_case_transition(cls, current: ReturnCaseStatus, attempted: ReturnCaseStatus, item_id: str):
        if (current, attempted) not in cls.VALID_RETURN_CASE_TRANSITIONS and current != attempted:
            raise InvalidStateTransitionError(
                current_state=current.value,
                attempted_state=attempted.value,
                entity_name=f"ReturnCase (Item {item_id})"
            )

    @classmethod
    def validate_approval_transition(cls, current: ApprovalStatus, attempted: ApprovalStatus, item_id: str):
        if (current, attempted) not in cls.VALID_APPROVAL_TRANSITIONS and current != attempted:
            raise InvalidStateTransitionError(
                current_state=current.value,
                attempted_state=attempted.value,
                entity_name=f"ApprovalStatus (Item {item_id})"
            )

    @classmethod
    def validate_sanitization_transition(cls, current: SanitizationStatus, attempted: SanitizationStatus, item_id: str):
        if (current, attempted) not in cls.VALID_SANITIZATION_TRANSITIONS and current != attempted:
            raise InvalidStateTransitionError(
                current_state=current.value,
                attempted_state=attempted.value,
                entity_name=f"SanitizationRecord (Item {item_id})"
            )

    @classmethod
    def validate_custody_transition(cls, current: CustodyLocation, attempted: CustodyLocation, item_id: str):
        if (current, attempted) not in cls.VALID_CUSTODY_TRANSITIONS and current != attempted:
            raise InvalidStateTransitionError(
                current_state=current.value,
                attempted_state=attempted.value,
                entity_name=f"CustodyLocation (Item {item_id})"
            )

    @classmethod
    def validate_refund_transition(cls, current: RefundStatus, attempted: RefundStatus, item_id: str):
        if (current, attempted) not in cls.VALID_REFUND_TRANSITIONS and current != attempted:
            raise InvalidStateTransitionError(
                current_state=current.value,
                attempted_state=attempted.value,
                entity_name=f"RefundRecord (ReturnRequest {item_id})"
            )
