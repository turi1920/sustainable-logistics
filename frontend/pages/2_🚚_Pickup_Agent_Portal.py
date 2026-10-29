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

st.set_page_config(page_title="Pickup Agent Portal", page_icon="🚚", layout="wide")
st.title("🚚 Pickup Agent Portal")
st.caption("Field operations for assigned collections, product code verification, and preliminary damage assessment.")

current_user = st.session_state.get("current_user")
if not current_user:
    st.warning("⚠️ Please log in as a Return Agent to access your pickup assignments.")
    st.stop()

if current_user["role"] != "RETURN_AGENT":
    st.error(f"⛔ Access Denied. Your current role is `{current_user['role']}`. Only `RETURN_AGENT` can access this portal.")
    st.stop()

st.markdown("### 📋 Your Assigned Pickups")
res_tasks = api.get("/pickups/my-tasks")

if res_tasks["success"] and res_tasks["data"]:
    for task in res_tasks["data"]:
        with st.container():
            st.markdown(f"**Task ID:** `{task['id']}` | **Scheduled Date:** `{task['scheduled_date']}`")
            if task.get("completed_at"):
                st.success(f"✅ Verified & Collected on {task['completed_at']} (Outcome: `{task['verification_outcome']}`, Damage: `{task['initial_damage']}`)")
            else:
                st.warning("⏳ Pending Verification & Collection")
                with st.expander(f"Verify & Collect Item: {task['return_item_id']}"):
                    with st.form(f"verify_form_{task['id']}"):
                        observed_code = st.text_input("Observed Product Code/Tag on Device *", placeholder="e.g. UB-15-2025")
                        verified_serial = st.text_input("Observed Serial Number", placeholder="e.g. SN-APX-882199")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            damage = st.selectbox("Initial Damage Classification *", ["LOW", "MEDIUM", "HIGH"])
                        with col2:
                            outcome = st.selectbox("Verification Outcome *", ["VERIFIED", "MISMATCH", "UNABLE_TO_VERIFY"])
                        
                        notes = st.text_area("Verification Notes / Reason for Mismatch", placeholder="e.g. Tag matches, packaging intact, minor scratches on lid.")
                        signature = st.text_input("Customer/Agent Handover Signature Ref", placeholder="SIG-4491-COLLECT")

                        submitted = st.form_submit_button("Confirm Verification & Collection", type="primary")

                        if submitted:
                            if not observed_code:
                                st.error("Please enter the observed product code or tag.")
                            else:
                                payload = {
                                    "observed_product_code": observed_code,
                                    "verified_serial_number": verified_serial if verified_serial else None,
                                    "initial_damage": damage,
                                    "verification_outcome": outcome,
                                    "verification_notes": notes,
                                    "agent_signature_ref": signature if signature else None
                                }
                                res_v = api.post(f"/pickups/{task['id']}/verify", payload)
                                if res_v["success"]:
                                    st.success(f"Verification recorded with outcome `{outcome}`!")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to record verification: {res_v.get('error')}")
            st.divider()
else:
    st.info("No pickup tasks currently assigned to your account.")
