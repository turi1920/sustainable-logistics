from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.jobs.timeout_worker import TimeoutWorker
from backend.app.models.authorization import ApprovalRequest
from backend.app.models.returns import ApprovalStatus, RecoveryClassification, ReturnItem


@pytest.mark.asyncio
async def test_5_day_sla_auto_return_when_contract_authorizes(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict
):
    admin_token = seed_data["admin_token"]
    ops_token = seed_data["ops_token"]
    apex_org_id = str(seed_data["org_apex"].id)

    # Create item for Apex (which has auto_return_on_timeout_authorized = True)
    ret_payload = {
        "external_order_ref": "ORD-SLA-APEX",
        "customer_name": "SLA Customer",
        "customer_email": "sla@test.com",
        "customer_phone": "555-0105",
        "pickup_address": "SLA Blvd",
        "pickup_city": "City",
        "pickup_postal_code": "12345",
        "items": [
            {
                "manufacturer_org_id": apex_org_id,
                "product_name": "SLA Test Laptop",
                "product_category": "LAPTOP",
                "model_number": "SLA-1",
                "return_reason": "No response test",
                "requires_data_sanitization": True
            }
        ]
    }
    res_ret = await client.post("/api/v1/returns", json=ret_payload, headers={"Authorization": f"Bearer {admin_token}"})
    item_id = res_ret.json()["items"][0]["id"]

    # Inspect & Publish report
    insp_payload = {
        "return_item_id": item_id,
        "is_functional": True,
        "powers_on": True,
        "screen_condition": "PRISTINE",
        "enclosure_condition": "GRADE_A_MINT",
        "technician_notes": "SLA test inspection"
    }
    res_insp = await client.post("/api/v1/inspections", json=insp_payload, headers={"Authorization": f"Bearer {ops_token}"})
    insp_id = res_insp.json()["id"]

    est_payload = {"expected_resale_value": "400.00"}
    res_pub = await client.post(f"/api/v1/assessments/publish/{insp_id}", json=est_payload, headers={"Authorization": f"Bearer {ops_token}"})
    assert res_pub.status_code == 201

    # Simulate passage of 5 days: set deadline_at into the past
    stmt_req = select(ApprovalRequest).where(ApprovalRequest.manufacturer_org_id == seed_data["org_apex"].id)
    approval_req = (await db_session.execute(stmt_req)).scalars().first()
    approval_req.deadline_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()

    # Run SLA Worker
    processed_first_run = await TimeoutWorker.process_sla_checks(db_session)
    await db_session.commit()
    assert processed_first_run >= 1

    # Verify item status transitioned to RETURN_TO_MANUFACTURER & OVERDUE
    stmt_item = select(ReturnItem).where(ReturnItem.id == item_id)
    item = (await db_session.execute(stmt_item)).scalar_one()
    assert item.approval_status == ApprovalStatus.OVERDUE
    assert item.recovery_classification == RecoveryClassification.RETURN_TO_MANUFACTURER

    # Idempotency test: Run SLA worker again -> 0 requests should be processed, no duplicate changes
    processed_second_run = await TimeoutWorker.process_sla_checks(db_session)
    assert processed_second_run == 0
