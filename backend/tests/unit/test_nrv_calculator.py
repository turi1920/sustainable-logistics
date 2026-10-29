from decimal import Decimal
import pytest
from backend.app.domain.nrv_calculator import NRVCalculator
from backend.app.models.returns import RecoveryClassification


def test_repair_nrv_calculation_decimal_precision():
    # Expected Resale: 450.00
    # Parts: 85.50, Labour: 40.00, Pkg: 5.00, Trans: 15.00, San: 12.00
    # Costs: 85.50 + 40.00 + 5.00 + 15.00 + 12.00 = 157.50
    # NRV = 450.00 - 157.50 = 292.50
    res = NRVCalculator.calculate_repair_nrv(
        expected_resale_value=Decimal("450.00"),
        parts_cost=Decimal("85.50"),
        labour_cost=Decimal("40.00"),
        packaging_cost=Decimal("5.00"),
        transportation_cost=Decimal("15.00"),
        sanitization_cost=Decimal("12.00")
    )
    assert res.option_type == RecoveryClassification.REPAIR
    assert res.is_eligible is True
    assert res.net_recovery_value == Decimal("292.50")
    assert isinstance(res.net_recovery_value, Decimal)


def test_resale_as_new_contract_ineligible():
    # If not contractually eligible, should return is_eligible=False
    res = NRVCalculator.calculate_resale_as_new_nrv(
        expected_resale_value=Decimal("800.00"),
        is_contractually_eligible=False
    )
    assert res.is_eligible is False
    assert "policy criteria" in res.ineligibility_reason


def test_safety_hazard_blocks_resale_options():
    opt_repair = NRVCalculator.calculate_repair_nrv(
        expected_resale_value=Decimal("300.00"),
        parts_cost=Decimal("50.00"),
        labour_cost=Decimal("30.00")
    )
    opt_recycle = NRVCalculator.calculate_recycling_value()

    # When safety hazard is true, repair is blocked
    result = NRVCalculator.evaluate_all(
        has_safety_hazard=True,
        options=[opt_repair, opt_recycle]
    )

    assert opt_repair.is_eligible is False
    assert "Safety hazard detected" in opt_repair.ineligibility_reason
    assert result.recommended_option == RecoveryClassification.RECYCLING


def test_manufacturer_return_economics():
    # Applicable Return Credit: 150.00, remaining shipping: 20.00 -> Net: 130.00
    res = NRVCalculator.calculate_manufacturer_return_value(
        applicable_return_credit=Decimal("150.00"),
        remaining_return_shipping_cost=Decimal("20.00")
    )
    assert res.option_type == RecoveryClassification.RETURN_TO_MANUFACTURER
    assert res.net_recovery_value == Decimal("130.00")
