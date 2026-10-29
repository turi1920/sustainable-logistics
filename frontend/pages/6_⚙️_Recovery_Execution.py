from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

try:
    from frontend.client import api
except ImportError:
    from client import api

try:
    st.set_page_config(page_title="Recovery Execution", page_icon="⚙️", layout="wide")
except Exception:
    pass
st.title("⚙️ Recovery Execution & Resale Gate")
st.caption("Work order tracking, quality checks, NIST 800-88 data sanitization, and resale release verification.")

current_user = st.session_state.get("current_user")
if not current_user:
    st.warning("⚠️ Please log in to access recovery operations.")
    st.stop()

tab_wo, tab_san, tab_release = st.tabs([
    "🛠️ 1. Recovery Work Orders & QA",
    "🔒 2. Data Sanitization Workflow",
    "🚪 3. Resale Release Security Gate"
])

with tab_wo:
    st.markdown("### Create & Track Recovery Work Orders")
    col1, col2 = st.columns(2)
    with col1:
        with st.form("create_wo_form"):
            st.markdown("#### Issue New Work Order")
            wo_item_id = st.text_input("Return Item ID (UUID) *", placeholder="UUID of authorized item")
            wo_type = st.selectbox("Work Order Type *", ["REPAIR", "REFURBISHMENT", "RECYCLING", "RETURN_TO_MANUFACTURER"])
            wo_summary = st.text_area("Work Instructions / Summary", placeholder="e.g. Replace damaged display panel with OEM parts; clean cooling fan.")

            submit_wo = st.form_submit_button("Create Work Order", type="primary")

            if submit_wo:
                if not wo_item_id:
                    st.error("Please enter the Return Item ID.")
                else:
                    payload = {
                        "return_item_id": wo_item_id,
                        "facility_id": "776caf19-8f38-40a4-a756-7a3ce22e19b3",
                        "work_order_type": wo_type,
                        "work_summary": wo_summary
                    }
                    res_wo = api.post("/executions/work-orders", payload)
                    if res_wo["success"]:
                        st.success(f"✅ Work Order Issued! ID: `{res_wo['data']['work_order_id']}`")
                        st.session_state["last_wo_id"] = res_wo["data"]["work_order_id"]
                    else:
                        st.error(f"Cannot create work order: {res_wo.get('error')}")

    with col2:
        with st.form("record_qc_form"):
            st.markdown("#### Quality Assurance Verification")
            qc_wo_id = st.text_input("Work Order ID (UUID) *", value=st.session_state.get("last_wo_id", ""))
            q_func = st.checkbox("Functional Diagnostic Test Passed", value=True)
            q_cos = st.checkbox("Cosmetic Standard Passed (Grade Met)", value=True)
            q_pkg = st.checkbox("Secure Packaging Verified", value=True)
            q_defects = st.text_input("Defects Observed (if any)", placeholder="None observed. Test passed.")

            submit_qc = st.form_submit_button("Submit QA Check", type="primary")

            if submit_qc:
                if not qc_wo_id:
                    st.error("Please provide the Work Order ID.")
                else:
                    payload = {
                        "work_order_id": qc_wo_id,
                        "functional_test_passed": q_func,
                        "cosmetic_standard_passed": q_cos,
                        "packaging_verified": q_pkg,
                        "defects_observed": q_defects
                    }
                    res_qc = api.post("/executions/work-orders/quality-check", payload)
                    if res_qc["success"]:
                        if res_qc["data"]["passed"]:
                            st.success("✅ Quality Check PASSED! Work order marked COMPLETED.")
                        else:
                            st.warning("⚠️ Quality Check FAILED. Rework required.")
                    else:
                        st.error(f"QA submission failed: {res_qc.get('error')}")

with tab_san:
    st.markdown("### 🔒 Device Data Sanitization (NIST SP 800-88 Rev. 1)")
    st.info("⚠️ Before any electronic product with storage can be resold, an approved data erasure method must be verified. A simple factory reset is NOT recognized as proof of data sanitization.")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("#### Step 1: Start Sanitization Task")
        with st.form("start_san_form"):
            san_item_id = st.text_input("Return Item ID (UUID) *", placeholder="UUID of device to wipe")
            san_method = st.selectbox("Sanitization Standard / Method *", [
                "NIST_800_88_PURGE",
                "NIST_800_88_CLEAR",
                "CRYPTOGRAPHIC_ERASE",
                "PHYSICAL_DESTRUCTION",
                "NOT_APPLICABLE_NO_STORAGE"
            ])
            san_tool = st.text_input("Erasure & Verification Utility *", value="Blancco Drive Eraser v6.12", placeholder="e.g. Blancco, nwipe, KillDisk")

            submit_start_san = st.form_submit_button("Initiate Sanitization Task", type="primary")

            if submit_start_san:
                if not san_item_id:
                    st.error("Please enter the Return Item ID.")
                else:
                    payload = {
                        "return_item_id": san_item_id,
                        "method": san_method,
                        "verification_tool": san_tool
                    }
                    res_s = api.post("/executions/sanitization/start", payload)
                    if res_s["success"]:
                        st.success(f"Sanitization task started! Record ID: `{res_s['data']['id']}`")
                        st.session_state["last_san_id"] = res_s["data"]["id"]
                    else:
                        st.error(f"Failed to start sanitization: {res_s.get('error')}")

    with col_s2:
        st.markdown("#### Step 2: Complete & Verify Certificate")
        with st.form("complete_san_form"):
            comp_san_id = st.text_input("Sanitization Record ID (UUID) *", value=st.session_state.get("last_san_id", ""))
            comp_status = st.selectbox("Sanitization Outcome *", ["PASSED", "FAILED", "EXCEPTION_REVIEW"])
            cert_ref = st.text_input("Certificate of Erasure Reference / Hash", placeholder="e.g. CERT-BLANCCO-2026-98114")
            exc_reason = st.text_input("Exception Reason (if failed)", placeholder="e.g. Drive bad sectors; unreadable sectors detected")

            submit_comp_san = st.form_submit_button("Record Sanitization Verification", type="primary")

            if submit_comp_san:
                if not comp_san_id:
                    st.error("Please provide the Sanitization Record ID.")
                else:
                    payload = {
                        "sanitization_record_id": comp_san_id,
                        "status": comp_status,
                        "certificate_ref": cert_ref if cert_ref else None,
                        "exception_reason": exc_reason if comp_status != "PASSED" else None
                    }
                    res_c = api.post("/executions/sanitization/complete", payload)
                    if res_c["success"]:
                        if comp_status == "PASSED":
                            st.success("✅ Device Certified Sanitized! Eligible for resale release.")
                        else:
                            st.error(f"Device sanitization status: `{comp_status}`. Device placed on secure hold.")
                    else:
                        st.error(f"Failed to complete sanitization: {res_c.get('error')}")

with tab_release:
    st.markdown("### 🚪 Resale Release Security Gate")
    st.warning("Backend Security Enforcement: Releasing an item for secondary market or outlet resale without a verified 'PASSED' data sanitization certificate will be blocked by the server with HTTP 422.")

    with st.form("release_gate_form"):
        rel_item_id = st.text_input("Return Item ID to Release (UUID) *", placeholder="UUID of product ready for disposition")
        rel_disposition = st.selectbox("Target Disposition Route *", [
            "RESALE_SECONDARY_MARKET",
            "RESALE_OUTLET",
            "DISPATCHED_TO_MANUFACTURER",
            "RECYCLED_CERTIFIED"
        ])
        actual_proceeds = st.number_input("Actual Realized Proceeds ($)", min_value=0.0, value=720.0, step=10.0)

        submit_release = st.form_submit_button("Authorize Release & Close Case", type="primary")

        if submit_release:
            if not rel_item_id:
                st.error("Please enter the Return Item ID.")
            else:
                payload = {
                    "return_item_id": rel_item_id,
                    "authorized_disposition": rel_disposition,
                    "resale_proceeds_actual": str(actual_proceeds)
                }
                res_rel = api.post("/executions/items/release", payload)
                if res_rel["success"]:
                    st.success(f"🎉 Release Authorized! Disposition: `{res_rel['data']['disposition']}`. Parent return case marked COMPLETED.")
                else:
                    st.error(f"❌ Release Blocked by Security Gate: {res_rel.get('error')}")
