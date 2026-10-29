from datetime import date
from decimal import Decimal
from typing import List, Optional
from backend.app.models.authorization import AuthorizationPolicy
from backend.app.models.returns import ProductCategory, RecoveryClassification


class PolicyEvaluationResult:
    def __init__(
        self,
        is_authorized: bool,
        matching_policy: Optional[AuthorizationPolicy] = None,
        reason: str = ""
    ):
        self.is_authorized = is_authorized
        self.matching_policy = matching_policy
        self.reason = reason


class PolicyEngine:
    """Evaluates active manufacturer authorization policies for automated Path A pre-authorization."""

    @staticmethod
    def evaluate(
        policies: List[AuthorizationPolicy],
        recommended_action: RecoveryClassification,
        product_category: ProductCategory,
        estimated_repair_cost: Decimal,
        estimated_nrv: Decimal,
        has_safety_hazard: bool,
        evaluation_date: Optional[date] = None
    ) -> PolicyEvaluationResult:
        current_date = evaluation_date or date.today()

        if has_safety_hazard:
            return PolicyEvaluationResult(
                is_authorized=False,
                reason="Pre-authorization is strictly denied for items with active safety hazards."
            )

        for policy in policies:
            if not policy.is_active:
                continue

            # Check validity dates
            if current_date < policy.valid_from or current_date > policy.valid_to:
                continue

            # Check action match
            if policy.permitted_action != recommended_action:
                continue

            # Check category match (None implies all categories)
            if policy.product_category is not None and policy.product_category != product_category:
                continue

            # Check repair cost threshold if defined
            if policy.max_repair_cost_threshold is not None:
                if estimated_repair_cost > policy.max_repair_cost_threshold:
                    continue

            # Check minimum NRV threshold if defined
            if policy.min_expected_nrv_threshold is not None:
                if estimated_nrv < policy.min_expected_nrv_threshold:
                    continue

            # Policy matched!
            return PolicyEvaluationResult(
                is_authorized=True,
                matching_policy=policy,
                reason=f"Pre-authorized under active Policy '{policy.policy_code}' (Version {policy.version})."
            )

        return PolicyEvaluationResult(
            is_authorized=False,
            reason="No active pre-authorization policy covers this action and cost threshold. Human approval required."
        )
