from datetime import date
from decimal import Decimal
import uuid
import pytest
from backend.app.domain.policy_engine import PolicyEngine
from backend.app.models.authorization import AuthorizationPolicy
from backend.app.models.returns import ProductCategory, RecoveryClassification


def test_policy_engine_matching_pre_authorization():
    policy = AuthorizationPolicy(
        id=uuid.uuid4(),
        manufacturer_org_id=uuid.uuid4(),
        policy_code="LAPTOP-REPAIR-RULE",
        description="Auto repair under $100",
        product_category=ProductCategory.LAPTOP,
        permitted_action=RecoveryClassification.REPAIR,
        max_repair_cost_threshold=Decimal("100.00"),
        min_expected_nrv_threshold=Decimal("150.00"),
        requires_safety_pass=True,
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
        is_active=True
    )

    # Cost 80 <= 100, NRV 200 >= 150 -> Matches!
    result = PolicyEngine.evaluate(
        policies=[policy],
        recommended_action=RecoveryClassification.REPAIR,
        product_category=ProductCategory.LAPTOP,
        estimated_repair_cost=Decimal("80.00"),
        estimated_nrv=Decimal("200.00"),
        has_safety_hazard=False,
        evaluation_date=date(2026, 6, 1)
    )
    assert result.is_authorized is True
    assert result.matching_policy.policy_code == "LAPTOP-REPAIR-RULE"


def test_policy_engine_cost_exceeded_denies_pre_auth():
    policy = AuthorizationPolicy(
        id=uuid.uuid4(),
        manufacturer_org_id=uuid.uuid4(),
        policy_code="LAPTOP-REPAIR-RULE",
        description="Auto repair under $100",
        product_category=ProductCategory.LAPTOP,
        permitted_action=RecoveryClassification.REPAIR,
        max_repair_cost_threshold=Decimal("100.00"),
        min_expected_nrv_threshold=Decimal("150.00"),
        requires_safety_pass=True,
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
        is_active=True
    )

    # Repair cost 120 > 100 -> Denied
    result = PolicyEngine.evaluate(
        policies=[policy],
        recommended_action=RecoveryClassification.REPAIR,
        product_category=ProductCategory.LAPTOP,
        estimated_repair_cost=Decimal("120.00"),
        estimated_nrv=Decimal("200.00"),
        has_safety_hazard=False,
        evaluation_date=date(2026, 6, 1)
    )
    assert result.is_authorized is False
    assert "No active pre-authorization policy" in result.reason
