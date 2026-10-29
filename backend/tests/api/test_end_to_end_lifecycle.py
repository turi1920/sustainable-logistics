import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_reverse_logistics_lifecycle(client: AsyncClient, seed_data: dict):
    admin_token = seed_data["admin_token"]
    agent_token = seed_data["agent_token"]
    ops_token = seed_data["ops_token"]
    mfg_token = seed_data["mfg1_token"]
    analyst_token = seed_data["analyst_token"]
    apex_org_id = str(seed_data["org_apex"].id)
    facility_id = str(seed_data["facility"].id)
    agent_id = str(seed_data["agent"].id)

    # 1. Manual Return Registration (Admin)
    ret_payload = {
        "external_order_ref": "ORD-E2E-100",
        "customer_name": "Eleanor Shellstrop",
        "customer_email": "eleanor@goodplace.com",
        "customer_phone": "555-1234",
        "pickup_address": "888 Arizona St",
        "pickup_city": "Phoenix",
        "pickup_postal_code": "85001",
        "items": [
            {
                "manufacturer_org_id": apex_org_id,
                "product_name": "Apex Pro Ultra Laptop",
                "product_category": "LAPTOP",
                "model_number": "AP-2026",
                "declared_serial_number": "SN-E2E-9999",
                "return_reason": "Screen cracked during transit",
                "requires_data_sanitization": True
            }
        ]
    }
    res_ret = await client.post("/api/v1/returns", json=ret_payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res_ret.status_code == 201
    ret_data = res_ret.json()
    item_id = ret_data["items"][0]["id"]
    req_id = ret_data["id"]

    # 2. Pickup Assignment (Admin)
    assign_payload = {
        "return_item_id": item_id,
        "agent_user_id": agent_id,
        "scheduled_date": "2026-11-01"
    }
    res_assign = await client.post("/api/v1/pickups/assign", json=assign_payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res_assign.status_code == 201
    assign_id = res_assign.json()["id"]

    # 3. Agent Task List & Field Verification (Agent)
    res_agent_tasks = await client.get("/api/v1/pickups/my-tasks", headers={"Authorization": f"Bearer {agent_token}"})
    assert res_agent_tasks.status_code == 200
    assert len(res_agent_tasks.json()) >= 1

    verify_payload = {
        "observed_product_code": "AP-2026",
        "verified_serial_number": "SN-E2E-9999",
        "initial_damage": "MEDIUM",
        "verification_outcome": "VERIFIED",
        "verification_notes": "Serial number matches box label. Minor screen crack observed.",
        "agent_signature_ref": "SIG-AGENT-101"
    }
    res_verify = await client.post(f"/api/v1/pickups/{assign_id}/verify", json=verify_payload, headers={"Authorization": f"Bearer {agent_token}"})
    assert res_verify.status_code == 200

    # 4. Custody Transfer to Transit, then Warehouse Receipt (Ops Specialist)
    custody_payload = {
        "return_item_id": item_id,
        "event_type": "TRANSIT_DEPARTURE",
        "from_location": "Customer Residence (Phoenix)",
        "to_location": "Central Logistics Hub",
        "new_custody_location": "IN_TRANSIT",
        "carrier_tracking_ref": "TRK-E2E-4455"
    }
    res_cust = await client.post("/api/v1/custody/events", json=custody_payload, headers={"Authorization": f"Bearer {agent_token}"})
    assert res_cust.status_code == 201

    receipt_payload = {
        "return_item_id": item_id,
        "facility_id": facility_id,
        "intake_barcode": "BC-E2E-001",
        "storage_bin": "BIN-A-12",
        "packaging_intact": True,
        "intake_notes": "Received safely in good transit packaging."
    }
    res_receipt = await client.post("/api/v1/custody/warehouse-receipt", json=receipt_payload, headers={"Authorization": f"Bearer {ops_token}"})
    assert res_receipt.status_code == 201

    # Check tracking timeline
    res_timeline = await client.get(f"/api/v1/custody/items/{item_id}/timeline", headers={"Authorization": f"Bearer {ops_token}"})
    assert res_timeline.status_code == 200
    assert len(res_timeline.json()) >= 2

    # 5. Technical Inspection & Assessment Report (Ops Specialist)
    insp_payload = {
        "return_item_id": item_id,
        "is_functional": True,
        "powers_on": True,
        "screen_condition": "CRACKED",
        "enclosure_condition": "GRADE_A_MINT",
        "battery_health_pct": 98,
        "has_safety_hazard": False,
        "technician_notes": "Screen replacement required. Motherboard and battery pristine."
    }
    res_insp = await client.post("/api/v1/inspections", json=insp_payload, headers={"Authorization": f"Bearer {ops_token}"})
    assert res_insp.status_code == 201
    insp_id = res_insp.json()["id"]

    est_payload = {
        "expected_resale_value": "750.00",
        "parts_cost": "90.00",
        "labour_cost": "45.00",
        "packaging_cost": "5.00",
        "transportation_cost": "15.00",
        "sanitization_cost": "12.00",
        "applicable_return_credit": "100.00"
    }
    res_pub = await client.post(f"/api/v1/assessments/publish/{insp_id}", json=est_payload, headers={"Authorization": f"Bearer {ops_token}"})
    assert res_pub.status_code == 201
    pub_data = res_pub.json()
    assert pub_data["recommended_option"] == "REPAIR"

    # 6. Manufacturer Authorization Decision (Individual or Batch)
    res_pending = await client.get("/api/v1/authorizations/pending", headers={"Authorization": f"Bearer {mfg_token}"})
    assert res_pending.status_code == 200
    pending_items = res_pending.json()
    target_pending = next(p for p in pending_items if p["return_item_id"] == item_id)

    decide_payload = {
        "approval_request_item_id": target_pending["id"],
        "action": "APPROVE",
        "approved_recovery_option": "REPAIR",
        "decision_reason": "High NRV repair approved for secondary outlet resale."
    }
    res_decide = await client.post("/api/v1/authorizations/decide-item", json=decide_payload, headers={"Authorization": f"Bearer {mfg_token}"})
    assert res_decide.status_code == 200
    assert res_decide.json()["status"] == "SUCCESS"

    # 7. Recovery Work Order Execution & QA (Ops Specialist)
    wo_payload = {
        "return_item_id": item_id,
        "facility_id": facility_id,
        "work_order_type": "REPAIR",
        "work_summary": "Replaced cracked LCD with OEM panel."
    }
    res_wo = await client.post("/api/v1/executions/work-orders", json=wo_payload, headers={"Authorization": f"Bearer {ops_token}"})
    assert res_wo.status_code == 201
    wo_id = res_wo.json()["work_order_id"]

    qc_payload = {
        "work_order_id": wo_id,
        "functional_test_passed": True,
        "cosmetic_standard_passed": True,
        "packaging_verified": True,
        "defects_observed": "None. Display output verified at 144Hz."
    }
    res_qc = await client.post("/api/v1/executions/work-orders/quality-check", json=qc_payload, headers={"Authorization": f"Bearer {ops_token}"})
    assert res_qc.status_code == 201
    assert res_qc.json()["passed"] is True

    # 8. Data Sanitization Gate Passed
    san_start = {
        "return_item_id": item_id,
        "method": "NIST_800_88_PURGE",
        "verification_tool": "Blancco Drive Eraser v6.12"
    }
    res_san_start = await client.post("/api/v1/executions/sanitization/start", json=san_start, headers={"Authorization": f"Bearer {ops_token}"})
    assert res_san_start.status_code == 201
    san_id = res_san_start.json()["id"]

    san_comp = {
        "sanitization_record_id": san_id,
        "status": "PASSED",
        "certificate_ref": "CERT-BLANCCO-2026-8877"
    }
    res_san_comp = await client.post("/api/v1/executions/sanitization/complete", json=san_comp, headers={"Authorization": f"Bearer {ops_token}"})
    assert res_san_comp.status_code == 200

    # 9. Release for Resale
    release_payload = {
        "return_item_id": item_id,
        "authorized_disposition": "RESALE_OUTLET",
        "resale_proceeds_actual": "720.00"
    }
    res_release = await client.post("/api/v1/executions/items/release", json=release_payload, headers={"Authorization": f"Bearer {ops_token}"})
    assert res_release.status_code == 201, f"Release failed: {res_release.json()}"
    assert res_release.json()["status"] == "RELEASE_AUTHORIZED"

    # 10. Financial Reconciliation & Refund Recording
    res_refund_get = await client.get(f"/api/v1/refunds/by-request/{req_id}", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res_refund_get.status_code == 200
    refund_id = res_refund_get.json()["id"]

    # Valid State Transition: PENDING -> INITIATED -> PROCESSING -> COMPLETED
    res_init = await client.patch(
        f"/api/v1/refunds/{refund_id}",
        json={"status": "INITIATED", "manual_processing_notes": "Initiated refund via Stripe dashboard."},
        headers={"Authorization": f"Bearer {analyst_token}"}
    )
    assert res_init.status_code == 200

    res_proc = await client.patch(
        f"/api/v1/refunds/{refund_id}",
        json={"status": "PROCESSING", "external_payout_ref": "PAYOUT-STRIPE-998811"},
        headers={"Authorization": f"Bearer {analyst_token}"}
    )
    assert res_proc.status_code == 200

    res_comp = await client.patch(
        f"/api/v1/refunds/{refund_id}",
        json={"status": "COMPLETED", "external_payout_ref": "PAYOUT-STRIPE-998811", "manual_processing_notes": "Payout reconciled and verified."},
        headers={"Authorization": f"Bearer {analyst_token}"}
    )
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == "COMPLETED"

    # 11. Recovery Summary & Audit Analytics
    res_summary = await client.get("/api/v1/reports/recovery-summary", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res_summary.status_code == 200
    summary_data = res_summary.json()
    assert summary_data["total_returned_items"] >= 1
    assert summary_data["total_actual_resale_proceeds"] >= 720.0

    res_audit = await client.get("/api/v1/reports/audit-events", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_audit.status_code == 200
    assert len(res_audit.json()) >= 5
