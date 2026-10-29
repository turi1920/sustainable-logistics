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

st.set_page_config(page_title="Warehouse Custody", page_icon="🏬", layout="wide")
st.title("🏬 Warehouse Intake & Custody Tracking")
st.caption("Central hub receiving, storage bin allocation, custody transfers, and chronological product tracking.")

current_user = st.session_state.get("current_user")
if not current_user:
    st.warning("⚠️ Please log in to access warehouse tracking.")
    st.stop()

tab1, tab2 = st.tabs(["📥 Warehouse Intake Scanner", "📜 Chronological Tracking Timeline"])

with tab1:
    st.markdown("### Scan & Receive Item at Central Hub")
    with st.form("warehouse_receipt_form"):
        item_id = st.text_input("Return Item ID (UUID) *", placeholder="e.g. b32522eb-e303-4eb4-b4f0-4f01787b4577")
        facility_id = st.text_input("Facility ID *", value="fac-central-01", placeholder="Facility UUID or code")
        intake_barcode = st.text_input("Intake Barcode / Scan Tag *", placeholder="e.g. INTAKE-BC-9988")
        storage_bin = st.text_input("Storage Bin Allocation *", placeholder="e.g. BIN-C-04")
        packaging_intact = st.checkbox("Original Packaging Intact", value=True)
        intake_notes = st.text_area("Intake Inspection Notes", placeholder="e.g. Package arrived safely via courier, no transit water damage.")

        submitted = st.form_submit_button("Record Warehouse Receipt", type="primary")

        if submitted:
            if not item_id or not intake_barcode or not storage_bin:
                st.error("Please provide the Item ID, Intake Barcode, and Storage Bin.")
            else:
                payload = {
                    "return_item_id": item_id,
                    "facility_id": "776caf19-8f38-40a4-a756-7a3ce22e19b3", # default facility
                    "intake_barcode": intake_barcode,
                    "storage_bin": storage_bin,
                    "packaging_intact": packaging_intact,
                    "intake_notes": intake_notes
                }
                res = api.post("/custody/warehouse-receipt", payload)
                if res["success"]:
                    st.success(f"✅ Warehouse Receipt Recorded! Stored in Bin `{storage_bin}`.")
                else:
                    st.error(f"Failed to record receipt: {res.get('error')}")

with tab2:
    st.markdown("### 🔎 Look Up Chronological Custody History")
    query_item_id = st.text_input("Enter Return Item ID to Inspect Timeline", placeholder="UUID of return item")
    if st.button("Fetch Tracking Timeline"):
        if query_item_id:
            res_tl = api.get(f"/custody/items/{query_item_id}/timeline")
            if res_tl["success"] and res_tl["data"]:
                st.markdown("#### Chronological Milestones")
                for ev in res_tl["data"]:
                    with st.chat_message("assistant"):
                        st.markdown(f"**Event:** `{ev['event_type']}` | **Time:** {ev['event_timestamp']}")
                        st.markdown(f"**From:** `{ev['from_location']}` ➔ **To:** `{ev['to_location']}`")
                        if ev.get("carrier_tracking_ref"):
                            st.caption(f"Carrier Tracking: `{ev['carrier_tracking_ref']}`")
                        if ev.get("notes"):
                            st.write(ev["notes"])
            else:
                st.info("No custody events recorded for this item yet.")
