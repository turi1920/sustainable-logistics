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

st.set_page_config(page_title="Refunds Management", page_icon="💰", layout="wide")
st.title("💰 Customer Refunds Reconciliation")
st.caption("Accounting ledger for refund eligibility, status tracking, and manual payout reference recording.")

current_user = st.session_state.get("current_user")
if not current_user:
    st.warning("⚠️ Please log in to manage refunds.")
    st.stop()

if current_user["role"] not in ["FINANCE_SUSTAINABILITY_ANALYST", "PLATFORM_ADMIN"]:
    st.error(f"⛔ Access Denied. Your current role is `{current_user['role']}`.")
    st.stop()

st.markdown("### 🔎 Look Up Refund Record by Return Request")
req_id_input = st.text_input("Return Request ID (UUID) *", placeholder="UUID of return request")

if st.button("Fetch Refund Details"):
    if req_id_input:
        res = api.get(f"/refunds/by-request/{req_id_input}")
        if res["success"] and res["data"]:
            ref = res["data"]
            st.session_state["active_refund"] = ref
        else:
            st.error(f"Could not find refund record: {res.get('error')}")

active_refund = st.session_state.get("active_refund")
if active_refund:
    st.markdown("---")
    st.markdown(f"#### Refund ID: `{active_refund['id']}`")
    col1, col2, col3 = st.columns(3)
    col1.metric("Refund Amount", f"${active_refund['refund_amount']}", "USD")
    col2.metric("Current Status", active_refund["status"])
    col3.metric("External Reference", active_refund.get("external_payout_ref") or "None")

    st.markdown("#### Update Refund Reconciliation Milestone")
    with st.form("update_refund_form"):
        new_status = st.selectbox("Target Status", ["INITIATED", "PROCESSING", "COMPLETED", "FAILED", "NOT_APPLICABLE"])
        payout_ref = st.text_input("External Payout Reference (Stripe / Bank Wire ID)", value=active_refund.get("external_payout_ref") or "")
        notes = st.text_area("Reconciliation Notes", value=active_refund.get("manual_processing_notes") or "")

        submit_ref = st.form_submit_button("Update Refund Status", type="primary")

        if submit_ref:
            payload = {
                "status": new_status,
                "external_payout_ref": payout_ref if payout_ref else None,
                "manual_processing_notes": notes
            }
            res_up = api.patch(f"/refunds/{active_refund['id']}", payload)
            if res_up["success"]:
                st.success(f"✅ Refund status updated to `{new_status}`!")
                st.session_state["active_refund"] = res_up["data"]
                st.rerun()
            else:
                st.error(f"Failed to update refund: {res_up.get('error')}")
