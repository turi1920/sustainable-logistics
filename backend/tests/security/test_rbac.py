import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_return_agent_cannot_create_return_request(client: AsyncClient, seed_data: dict):
    # Only PLATFORM_ADMIN can register returns manually
    agent_token = seed_data["agent_token"]
    payload = {
        "external_order_ref": "ORD-UNAUTH-01",
        "customer_name": "Test Cust",
        "customer_email": "cust@test.com",
        "customer_phone": "555-0100",
        "pickup_address": "123 Street",
        "pickup_city": "City",
        "pickup_postal_code": "12345",
        "items": []
    }
    response = await client.post(
        "/api/v1/returns",
        json=payload,
        headers={"Authorization": f"Bearer {agent_token}"}
    )
    assert response.status_code == 403
    assert "Operation not permitted" in response.json()["detail"]


@pytest.mark.asyncio
async def test_platform_admin_can_create_return_request(client: AsyncClient, seed_data: dict):
    admin_token = seed_data["admin_token"]
    mfg_id = str(seed_data["org_apex"].id)
    payload = {
        "external_order_ref": "ORD-ADMIN-01",
        "customer_name": "Admin Customer",
        "customer_email": "admincust@test.com",
        "customer_phone": "555-0101",
        "pickup_address": "456 Admin Way",
        "pickup_city": "Metropolis",
        "pickup_postal_code": "98765",
        "items": [
            {
                "manufacturer_org_id": mfg_id,
                "product_name": "Test Laptop",
                "product_category": "LAPTOP",
                "model_number": "TL-2026",
                "declared_serial_number": "SN-TEST-001",
                "return_reason": "Screen cracked",
                "requires_data_sanitization": True
            }
        ]
    }
    response = await client.post(
        "/api/v1/returns",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["case_number"].startswith("RET-")
    assert len(data["items"]) == 1
