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
    st.set_page_config(page_title="Manufacturer Approvals", page_icon="🛡️", layout="wide")
except Exception:
    pass
st.title("🛡️ Manufacturer Authorization Portal")
st.caption("Governance, policy evaluation, batch approvals, and individual exception decisions.")

current_user = st.session_state.get("current_user")
if not current_user:
    st.warning("⚠️ Please log in as a Manufacturer Approver to access pending authorization requests.")
    st.stop()

if current_user["role"] not in ["MANUFACTURER_APPROVER", "PLATFORM_ADMIN"]:
    st.error(f"⛔ Access Denied. Your current role is `{current_user['role']}`.")
    st.stop()

tab_pending, tab_batch, tab_policy = st.tabs(["📥 Pending Approvals", "⚡ Batch Approvals", "📜 Pre-Authorization Policies"])

with tab_pending:
    st.markdown("### ⏳ Items Awaiting Manufacturer Authorization")
    res_pending = api.get("/authorizations/pending")

    if res_pending["success"] and res_pending["data"]:
        items = res_pending["data"]
        st.write(f"Found **{len(items)}** items awaiting decision.")

        for item_req in items:
            with st.container():
                st.markdown(f"**Item Tag:** `{item_req.get('item_tag')}` | **Product:** {item_req.get('product_name')}")
                st.markdown(f"**Recommended Recovery Option:** `{item_req.get('recommended_option')}`")

                with st.expander(f"Review & Decide: Request Item {item_req['id']}"):
                    with st.form(f"decision_form_{item_req['id']}"):
                        action = st.selectbox("Decision Action *", ["APPROVE", "REJECT", "REQUEST_MORE_INFORMATION"])
                        approved_option = st.selectbox("Approved Disposition Route", [
                            "REPAIR", "REFURBISHMENT", "RESALE_AS_NEW_ELIGIBLE", "RETURN_TO_MANUFACTURER", "RECYCLING"
                        ])
                        reason = st.text_area("Decision Rationale / Feedback *", placeholder="e.g. Approved for repair and resale in secondary outlet channel.")

                        submitted = st.form_submit_button("Submit Authorization Decision", type="primary")

                        if submitted:
                            if not reason:
                                st.error("Please provide a reason for your decision.")
                            else:
                                payload = {
                                    "approval_request_item_id": item_req["id"],
                                    "action": action,
                                    "approved_recovery_option": approved_option if action == "APPROVE" else None,
                                    "decision_reason": reason
                                }
                                res_dec = api.post("/authorizations/decide-item", payload)
                                if res_dec["success"]:
                                    st.success(f"Decision `{action}` recorded successfully!")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to submit decision: {res_dec.get('error')}")
                st.divider()
    else:
        st.info("No items currently pending manufacturer authorization.")

with tab_batch:
    st.markdown("### ⚡ Batch Decision Processing")
    st.caption("Apply bulk actions across multiple items while preserving granular item-level audit decisions.")

    res_batch_list = api.get("/authorizations/pending")
    if res_batch_list["success"] and res_batch_list["data"]:
        batch_items = res_batch_list["data"]
        
        selected_item_ids = []
        st.markdown("#### Select Items for Batch Review:")
        for bi in batch_items:
            chk = st.checkbox(f"Item `{bi.get('item_tag', bi['return_item_id'])}` - {bi.get('product_name')} (Recommended: {bi.get('recommended_option')})", key=f"chk_{bi['id']}")
            if chk:
                selected_item_ids.append(bi["id"])

        if selected_item_ids:
            st.info(f"Selected **{len(selected_item_ids)}** items for batch authorization.")
            with st.form("batch_decision_form"):
                batch_action = st.selectbox("Batch Action", ["APPROVE", "REJECT"])
                batch_route = st.selectbox("Batch Disposition Route", ["REPAIR", "REFURBISHMENT", "RETURN_TO_MANUFACTURER", "RECYCLING"])
                batch_reason = st.text_input("Batch Rationale", placeholder="e.g. Standard batch authorization for inspected laptops meeting QA thresholds.")

                submit_batch = st.form_submit_button(f"Execute Batch {batch_action} on {len(selected_item_ids)} Items", type="primary")

                if submit_batch:
                    items_payload = [
                        {
                            "approval_request_item_id": req_id,
                            "action": batch_action,
                            "approved_recovery_option": batch_route if batch_action == "APPROVE" else None,
                            "decision_reason": batch_reason or "Batch decision executed by authorized approver."
                        }
                        for req_id in selected_item_ids
                    ]
                    res_batch = api.post("/authorizations/decide-batch", {"items": items_payload})
                    if res_batch["success"]:
                        st.success(f"Successfully processed batch! {res_batch['data']['processed_count']} item-level decisions committed.")
                        st.rerun()
                    else:
                        st.error(f"Batch failed: {res_batch.get('error')}")
    else:
        st.info("No pending items available for batch review.")

with tab_policy:
    st.markdown("### ⚙️ Pre-Authorization Policy Engine (Path A)")
    st.markdown("Automate routine approvals (e.g. repairs under \$150 with positive NRV) under active manufacturer contracts.")

    with st.expander("➕ Define New Pre-Authorization Policy Rule"):
        with st.form("new_policy_form"):
            code = st.text_input("Policy Code *", placeholder="e.g. APEX-PHONE-REFURB-AUTO")
            desc = st.text_area("Description *", placeholder="Auto-approves refurbishments for smartphones under $80 repair cost.")
            cat = st.selectbox("Applicable Category", ["LAPTOP", "SMARTPHONE", "TABLET", "AUDIO", "MONITOR"])
            action = st.selectbox("Permitted Action", ["REPAIR", "REFURBISHMENT", "RESALE_AS_NEW_ELIGIBLE", "RECYCLING"])
            max_cost = st.number_input("Max Repair Cost Threshold ($)", min_value=0.0, value=100.0, step=10.0)
            min_nrv = st.number_input("Min Expected NRV Threshold ($)", min_value=0.0, value=150.0, step=10.0)
            
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                start_d = st.date_input("Valid From")
            with col_v2:
                end_d = st.date_input("Valid To")

            submit_pol = st.form_submit_button("Save Policy Rule", type="primary")

            if submit_pol:
                payload = {
                    "policy_code": code,
                    "description": desc,
                    "product_category": cat,
                    "permitted_action": action,
                    "max_repair_cost_threshold": str(max_cost),
                    "min_expected_nrv_threshold": str(min_nrv),
                    "requires_safety_pass": True,
                    "valid_from": start_d.isoformat(),
                    "valid_to": end_d.isoformat()
                }
                res_pol = api.post("/authorizations/policies", payload)
                if res_pol["success"]:
                    st.success(f"✅ Policy `{code}` created successfully!")
                else:
                    st.error(f"Failed to create policy: {res_pol.get('error')}")
