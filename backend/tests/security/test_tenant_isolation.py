import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_manufacturer_tenant_isolation_in_pending_approvals(client: AsyncClient, seed_data: dict):
    # 1. Admin creates a return for Manufacturer Apex
    admin_token = seed_data["admin_token"]
    apex_org_id = str(seed_data["org_apex"].id)
    payload = {
        "external_order_ref": "ORD-APEX-ISOLATION",
        "customer_name": "Apex Customer",
        "customer_email": "apexcust@test.com",
        "customer_phone": "555-0102",
        "pickup_address": "789 Apex Blvd",
        "pickup_city": "Tech City",
        "pickup_postal_code": "54321",
        "items": [
            {
                "manufacturer_org_id": apex_org_id,
                "product_name": "Apex Device",
                "product_category": "SMARTPHONE",
                "model_number": "AD-1",
                "return_reason": "Broken speaker",
                "requires_data_sanitization": True
            }
        ]
    }
    res_create = await client.post("/api/v1/returns", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res_create.status_code == 201
    item_id = res_create.json()["items"][0]["id"]

    # 2. Ops inspects and publishes assessment
    ops_token = seed_data["ops_token"]
    insp_payload = {
        "return_item_id": item_id,
        "is_functional": True,
        "powers_on": True,
        "screen_condition": "PRISTINE",
        "enclosure_condition": "GRADE_A_MINT",
        "has_safety_hazard": False,
        "technician_notes": "All hardware verified"
    }
    res_insp = await client.post("/api/v1/inspections", json=insp_payload, headers={"Authorization": f"Bearer {ops_token}"})
    assert res_insp.status_code == 201
    insp_id = res_insp.json()["id"]

    est_payload = {
        "expected_resale_value": "300.00",
        "parts_cost": "20.00",
        "labour_cost": "15.00"
    }
    res_pub = await client.post(f"/api/v1/assessments/publish/{insp_id}", json=est_payload, headers={"Authorization": f"Bearer {ops_token}"})
    assert res_pub.status_code == 201

    # 3. Nova Approver queries pending approvals -> should see 0 items (since item belongs to Apex)
    nova_token = seed_data["mfg2_token"]
    res_nova = await client.get("/api/v1/authorizations/pending", headers={"Authorization": f"Bearer {nova_token}"})
    assert res_nova.status_code == 200
    assert len(res_nova.json()) == 0

    # 4. Apex Approver queries pending approvals -> should see the 1 item
    apex_token = seed_data["mfg1_token"]
    res_apex = await client.get("/api/v1/authorizations/pending", headers={"Authorization": f"Bearer {apex_token}"})
    assert res_apex.status_code == 200
    assert len(res_apex.json()) == 1
    assert res_apex.json()[0]["return_item_id"] == item_id
