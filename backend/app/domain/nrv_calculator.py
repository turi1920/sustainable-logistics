from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.core.config import settings
from backend.app.models.returns import ProductCategory, RecoveryClassification


class OptionEconomics(BaseModel):
    option_type: RecoveryClassification
    is_eligible: bool
    ineligibility_reason: Optional[str] = None
    expected_resale_value: Decimal = Field(default=Decimal("0.00"))
    parts_cost: Decimal = Field(default=Decimal("0.00"))
    labour_cost: Decimal = Field(default=Decimal("0.00"))
    packaging_cost: Decimal = Field(default=Decimal("0.00"))
    transportation_cost: Decimal = Field(default=Decimal("0.00"))
    sanitization_cost: Decimal = Field(default=Decimal("0.00"))
    applicable_return_credit: Decimal = Field(default=Decimal("0.00"))
    remaining_return_shipping_cost: Decimal = Field(default=Decimal("0.00"))
    net_recovery_value: Decimal = Field(default=Decimal("0.00"))


class NRVCalculationResult(BaseModel):
    recommended_option: RecoveryClassification
    recommendation_rationale: str
    options: List[OptionEconomics]
    calculation_version: str = "v1.0"
    currency: str = "USD"


class NRVCalculator:
    """Deterministic, transparent Net Recovery Value calculation engine.
    Uses pure Decimal arithmetic with 2 decimal places to prevent float rounding errors.
    """

    @staticmethod
    def quantize(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_repair_nrv(
        cls,
        expected_resale_value: Decimal,
        parts_cost: Decimal,
        labour_cost: Decimal,
        packaging_cost: Optional[Decimal] = None,
        transportation_cost: Optional[Decimal] = None,
        sanitization_cost: Optional[Decimal] = None,
        requires_sanitization: bool = True
    ) -> OptionEconomics:
        pkg = packaging_cost if packaging_cost is not None else settings.DEFAULT_PACKAGING_COST
        trans = transportation_cost if transportation_cost is not None else settings.AVERAGE_TRANSPORTATION_COST
        san = sanitization_cost if sanitization_cost is not None else (settings.DEFAULT_SANITIZATION_COST if requires_sanitization else Decimal("0.00"))
        
        # NRV = Expected Resale Value - (Repair Cost + Packaging + Transportation + Sanitization)
        total_costs = parts_cost + labour_cost + pkg + trans + san
        nrv = expected_resale_value - total_costs

        return OptionEconomics(
            option_type=RecoveryClassification.REPAIR,
            is_eligible=True,
            expected_resale_value=cls.quantize(expected_resale_value),
            parts_cost=cls.quantize(parts_cost),
            labour_cost=cls.quantize(labour_cost),
            packaging_cost=cls.quantize(pkg),
            transportation_cost=cls.quantize(trans),
            sanitization_cost=cls.quantize(san),
            net_recovery_value=cls.quantize(nrv)
        )

    @classmethod
    def calculate_refurbishment_nrv(
        cls,
        expected_resale_value: Decimal,
        parts_cost: Decimal,
        labour_cost: Decimal,
        packaging_cost: Optional[Decimal] = None,
        transportation_cost: Optional[Decimal] = None,
        sanitization_cost: Optional[Decimal] = None,
        requires_sanitization: bool = True
    ) -> OptionEconomics:
        pkg = packaging_cost if packaging_cost is not None else settings.DEFAULT_PACKAGING_COST
        trans = transportation_cost if transportation_cost is not None else settings.AVERAGE_TRANSPORTATION_COST
        san = sanitization_cost if sanitization_cost is not None else (settings.DEFAULT_SANITIZATION_COST if requires_sanitization else Decimal("0.00"))
        
        total_costs = parts_cost + labour_cost + pkg + trans + san
        nrv = expected_resale_value - total_costs

        return OptionEconomics(
            option_type=RecoveryClassification.REFURBISHMENT,
            is_eligible=True,
            expected_resale_value=cls.quantize(expected_resale_value),
            parts_cost=cls.quantize(parts_cost),
            labour_cost=cls.quantize(labour_cost),
            packaging_cost=cls.quantize(pkg),
            transportation_cost=cls.quantize(trans),
            sanitization_cost=cls.quantize(san),
            net_recovery_value=cls.quantize(nrv)
        )

    @classmethod
    def calculate_resale_as_new_nrv(
        cls,
        expected_resale_value: Decimal,
        packaging_cost: Optional[Decimal] = None,
        transportation_cost: Optional[Decimal] = None,
        sanitization_cost: Optional[Decimal] = None,
        is_contractually_eligible: bool = False,
        requires_sanitization: bool = True
    ) -> OptionEconomics:
        pkg = packaging_cost if packaging_cost is not None else settings.DEFAULT_PACKAGING_COST
        trans = transportation_cost if transportation_cost is not None else settings.AVERAGE_TRANSPORTATION_COST
        san = sanitization_cost if sanitization_cost is not None else (settings.DEFAULT_SANITIZATION_COST if requires_sanitization else Decimal("0.00"))
        
        if not is_contractually_eligible:
            return OptionEconomics(
                option_type=RecoveryClassification.RESALE_AS_NEW_ELIGIBLE,
                is_eligible=False,
                ineligibility_reason="Product does not meet manufacturer open-box resale policy criteria or package is opened.",
                net_recovery_value=Decimal("0.00")
            )

        total_costs = pkg + trans + san
        nrv = expected_resale_value - total_costs

        return OptionEconomics(
            option_type=RecoveryClassification.RESALE_AS_NEW_ELIGIBLE,
            is_eligible=True,
            expected_resale_value=cls.quantize(expected_resale_value),
            packaging_cost=cls.quantize(pkg),
            transportation_cost=cls.quantize(trans),
            sanitization_cost=cls.quantize(san),
            net_recovery_value=cls.quantize(nrv)
        )

    @classmethod
    def calculate_manufacturer_return_value(
        cls,
        applicable_return_credit: Decimal,
        remaining_return_shipping_cost: Optional[Decimal] = None
    ) -> OptionEconomics:
        shipping = remaining_return_shipping_cost if remaining_return_shipping_cost is not None else settings.AVERAGE_TRANSPORTATION_COST
        net_value = applicable_return_credit - shipping

        return OptionEconomics(
            option_type=RecoveryClassification.RETURN_TO_MANUFACTURER,
            is_eligible=True,
            applicable_return_credit=cls.quantize(applicable_return_credit),
            remaining_return_shipping_cost=cls.quantize(shipping),
            transportation_cost=cls.quantize(shipping),
            net_recovery_value=cls.quantize(net_value)
        )

    @classmethod
    def calculate_recycling_value(
        cls,
        materials_scrap_value: Decimal = Decimal("0.00"),
        processing_fee: Decimal = Decimal("5.00"),
        transportation_cost: Optional[Decimal] = None
    ) -> OptionEconomics:
        trans = transportation_cost if transportation_cost is not None else settings.AVERAGE_TRANSPORTATION_COST
        net_value = materials_scrap_value - (processing_fee + trans)

        return OptionEconomics(
            option_type=RecoveryClassification.RECYCLING,
            is_eligible=True,
            expected_resale_value=cls.quantize(materials_scrap_value),
            labour_cost=cls.quantize(processing_fee),
            transportation_cost=cls.quantize(trans),
            net_recovery_value=cls.quantize(net_value)
        )

    @classmethod
    def evaluate_all(
        cls,
        has_safety_hazard: bool,
        options: List[OptionEconomics]
    ) -> NRVCalculationResult:
        """Evaluates all options and selects the optimal eligible route with an explanation."""
        if has_safety_hazard:
            # High-risk safety hazard blocks standard resale/repair routes
            for opt in options:
                if opt.option_type in [RecoveryClassification.REPAIR, RecoveryClassification.REFURBISHMENT, RecoveryClassification.RESALE_AS_NEW_ELIGIBLE]:
                    opt.is_eligible = False
                    opt.ineligibility_reason = "Safety hazard detected (e.g. swollen battery or short circuit); repair/resale prohibited."

        eligible_options = [opt for opt in options if opt.is_eligible]

        if not eligible_options:
            return NRVCalculationResult(
                recommended_option=RecoveryClassification.ON_HOLD,
                recommendation_rationale="No recovery option is eligible due to safety hazards or operational restrictions. Product placed ON_HOLD for specialist triage.",
                options=options
            )

        # Sort eligible options by Net Recovery Value descending
        eligible_options.sort(key=lambda x: x.net_recovery_value, reverse=True)
        best_option = eligible_options[0]

        # Formulate rationale
        if best_option.net_recovery_value > Decimal("0.00"):
            rationale = (
                f"Recommended '{best_option.option_type.value}' providing the highest Net Recovery Value "
                f"of {best_option.net_recovery_value} USD among {len(eligible_options)} eligible options."
            )
        else:
            # If all options are negative, prioritize minimizing loss
            rationale = (
                f"All eligible recovery options yield negative net recovery. "
                f"Recommended '{best_option.option_type.value}' as the least loss-incurring disposition route "
                f"({best_option.net_recovery_value} USD)."
            )

        return NRVCalculationResult(
            recommended_option=best_option.option_type,
            recommendation_rationale=rationale,
            options=options
        )
