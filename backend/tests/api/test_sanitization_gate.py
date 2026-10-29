import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_resale_gate_blocks_unsanitized_device(client: AsyncClient, seed_data: dict):
    admin_token = seed_data["admin_token"]
    ops_token = seed_data["ops_token"]
    apex_org_id = str(seed_data["org_apex"].id)

    # 1. Create return with a laptop that requires sanitization
    ret_payload = {
        "external_order_ref": "ORD-GATE-001",
        "customer_name": "Gate Tester",
        "customer_email": "gate@test.com",
        "customer_phone": "555-0199",
        "pickup_address": "Gate Street",
        "pickup_city": "City",
        "pickup_postal_code": "12345",
        "items": [
            {
                "manufacturer_org_id": apex_org_id,
                "product_name": "Sanitization Test Laptop",
                "product_category": "LAPTOP",
                "model_number": "STL-1",
                "return_reason": "Customer changed mind",
                "requires_data_sanitization": True
            }
        ]
    }
    res_ret = await client.post("/api/v1/returns", json=ret_payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res_ret.status_code == 201
    item_id = res_ret.json()["items"][0]["id"]

    # 2. Attempt to directly release device for resale without sanitization -> MUST fail with 422
    release_payload = {
        "return_item_id": item_id,
        "authorized_disposition": "RESALE_SECONDARY_MARKET",
        "resale_proceeds_actual": "450.00"
    }
    res_release_fail = await client.post(
        "/api/v1/executions/items/release",
        json=release_payload,
        headers={"Authorization": f"Bearer {ops_token}"}
    )
    assert res_release_fail.status_code == 422
    assert res_release_fail.json()["error"] == "SANITIZATION_GATE_VIOLATION"
    assert "No data sanitization record exists" in res_release_fail.json()["message"]

    # 3. Start sanitization
    start_payload = {
        "return_item_id": item_id,
        "method": "NIST_800_88_CLEAR",
        "verification_tool": "Nwipe Enterprise v2.4"
    }
    res_start = await client.post(
        "/api/v1/executions/sanitization/start",
        json=start_payload,
        headers={"Authorization": f"Bearer {ops_token}"}
    )
    assert res_start.status_code == 201
    san_record_id = res_start.json()["id"]

    # 4. Complete sanitization as PASSED with certificate
    comp_payload = {
        "sanitization_record_id": san_record_id,
        "status": "PASSED",
        "certificate_ref": "CERT-NIST-2026-98124"
    }
    res_comp = await client.post(
        "/api/v1/executions/sanitization/complete",
        json=comp_payload,
        headers={"Authorization": f"Bearer {ops_token}"}
    )
    assert res_comp.status_code == 200
    assert res_comp.json()["sanitization_status"] == "PASSED"

    # 5. Now release item for resale -> MUST succeed!
    res_release_success = await client.post(
        "/api/v1/executions/items/release",
        json=release_payload,
        headers={"Authorization": f"Bearer {ops_token}"}
    )
    assert res_release_success.status_code == 201
    assert res_release_success.json()["status"] == "RELEASE_AUTHORIZED"
