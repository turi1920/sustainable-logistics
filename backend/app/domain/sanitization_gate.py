from typing import Optional
from backend.app.core.exceptions import SanitizationGateError
from backend.app.models.execution import AuthorizedDisposition, SanitizationRecord, SanitizationStatus
from backend.app.models.returns import ReturnItem


class SanitizationGate:
    """Enforces the device data sanitization security gate before resale release.
    A device can NEVER be released for secondary market or outlet resale without a verified PASSED record.
    """

    RESALE_DISPOSITIONS = {
        AuthorizedDisposition.RESALE_SECONDARY_MARKET,
        AuthorizedDisposition.RESALE_OUTLET,
    }

    @classmethod
    def verify_release_eligibility(
        cls,
        item: ReturnItem,
        target_disposition: AuthorizedDisposition,
        latest_sanitization: Optional[SanitizationRecord]
    ) -> None:
        # If the item does not store data, sanitization is bypassed
        if not item.requires_data_sanitization:
            return

        # If releasing for resale, sanitization MUST be PASSED and verified
        if target_disposition in cls.RESALE_DISPOSITIONS:
            if not latest_sanitization:
                raise SanitizationGateError(
                    item_id=str(item.id),
                    reason="No data sanitization record exists for this electronic device. Resale is strictly prohibited."
                )

            if latest_sanitization.sanitization_status != SanitizationStatus.PASSED:
                raise SanitizationGateError(
                    item_id=str(item.id),
                    reason=(
                        f"Device data sanitization status is '{latest_sanitization.sanitization_status.value}'. "
                        "Only devices with verified 'PASSED' sanitization can be released for resale."
                    )
                )

            if not latest_sanitization.verified_at:
                raise SanitizationGateError(
                    item_id=str(item.id),
                    reason="Sanitization completion has not been verified by a qualified technician."
                )
