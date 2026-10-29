from decimal import Decimal
import plotly.graph_objects as go
import streamlit as st
from frontend.client import api

st.set_page_config(page_title="Technical Inspection", page_icon="🔬", layout="wide")
st.title("🔬 Technical Inspection & NRV Economics")
st.caption("Operations Specialist condition testing, component-level defects, and Net Recovery Value calculations.")

current_user = st.session_state.get("current_user")
if not current_user:
    st.warning("⚠️ Please log in as an Operations Specialist to record inspections.")
    st.stop()

if current_user["role"] not in ["OPERATIONS_SPECIALIST", "PLATFORM_ADMIN"]:
    st.error(f"⛔ Access Denied. Your current role is `{current_user['role']}`.")
    st.stop()

tab_insp, tab_nrv = st.tabs(["🛠️ 1. Technical Test & Defect Findings", "📊 2. NRV Economics & Assessment Report"])

with tab_insp:
    st.markdown("### Record Comprehensive Device Inspection")
    with st.form("insp_form"):
        item_id = st.text_input("Return Item ID (UUID) *", placeholder="e.g. b32522eb-e303-4eb4-b4f0-4f01787b4577")
        
        col1, col2 = st.columns(2)
        with col1:
            is_functional = st.checkbox("Device Functional (Core Logic OK)", value=True)
            powers_on = st.checkbox("Powers On Successfully", value=True)
            battery_health = st.slider("Battery Health Percentage (%)", min_value=0, max_value=100, value=92)
        with col2:
            screen_cond = st.selectbox("Display / Screen Condition", ["PRISTINE", "MINOR_SCRATCHES", "CRACKED", "DEAD_PIXELS", "NOT_APPLICABLE"])
            enclosure_cond = st.selectbox("Cosmetic Enclosure Condition", ["GRADE_A_MINT", "GRADE_B_LIGHT_WEAR", "GRADE_C_HEAVY_WEAR", "STRUCTURAL_DAMAGE"])
            has_safety_hazard = st.checkbox("⚠️ High-Risk Safety Hazard (Swollen Battery / Short Circuit / Liquid Leak)", value=False)
            
        safety_details = st.text_input("Safety Hazard Details (if applicable)", placeholder="e.g. Battery swelling detected, chassis expanding")
        tech_notes = st.text_area("Technician Findings & Notes *", placeholder="e.g. Backlight inverter failure, display panel needs OEM replacement.")

        submitted_insp = st.form_submit_button("Submit Technical Inspection", type="primary")

        if submitted_insp:
            if not item_id or not tech_notes:
                st.error("Please provide the Item ID and Technician Notes.")
            else:
                payload = {
                    "return_item_id": item_id,
                    "is_functional": is_functional,
                    "powers_on": powers_on,
                    "screen_condition": screen_cond,
                    "enclosure_condition": enclosure_cond,
                    "battery_health_pct": battery_health,
                    "has_safety_hazard": has_safety_hazard,
                    "safety_hazard_details": safety_details if has_safety_hazard else None,
                    "technician_notes": tech_notes
                }
                res = api.post("/inspections", payload)
                if res["success"]:
                    st.success(f"✅ Inspection Recorded! Inspection ID: `{res['data']['id']}` (Version {res['data']['inspection_version']})")
                    st.session_state["last_inspection_id"] = res["data"]["id"]
                else:
                    st.error(f"Failed to record inspection: {res.get('error')}")

with tab_nrv:
    st.markdown("### Calculate Comparative Net Recovery Value (NRV)")
    insp_id_input = st.text_input("Inspection ID (UUID) *", value=st.session_state.get("last_inspection_id", ""))

    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        resale_val = st.number_input("Expected Resale Value ($)", min_value=0.0, value=650.0, step=10.0)
        parts_cost = st.number_input("Estimated Parts Cost ($)", min_value=0.0, value=85.0, step=5.0)
    with col_e2:
        labour_cost = st.number_input("Estimated Labour Cost ($)", min_value=0.0, value=40.0, step=5.0)
        packaging_cost = st.number_input("Packaging Cost ($)", min_value=0.0, value=5.0, step=1.0)
    with col_e3:
        transport_cost = st.number_input("Transportation Estimate ($ - fuel/power included)", min_value=0.0, value=15.0, step=1.0)
        sanitization_cost = st.number_input("Data Sanitization Cost ($)", min_value=0.0, value=12.0, step=1.0)

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        return_credit = st.number_input("Contractual Manufacturer Return Credit ($)", min_value=0.0, value=150.0, step=10.0)
    with col_m2:
        mfg_shipping = st.number_input("Remaining Return Shipping to Manufacturer ($)", min_value=0.0, value=20.0, step=5.0)

    open_box_eligible = st.checkbox("Product Meets Manufacturer Open-Box Policy Criteria (Zero cosmetic/functional defects)", value=False)

    # Interactive Comparison Chart Preview
    nrv_repair = resale_val - (parts_cost + labour_cost + packaging_cost + transport_cost + sanitization_cost)
    nrv_refurb = resale_val - (parts_cost + labour_cost + packaging_cost + transport_cost + sanitization_cost)
    nrv_as_new = (resale_val - (packaging_cost + transport_cost + sanitization_cost)) if open_box_eligible else 0.0
    nrv_mfg = return_credit - mfg_shipping
    nrv_recycle = 0.0 - (5.0 + transport_cost)

    fig = go.Figure(data=[
        go.Bar(
            name="Net Recovery Value ($)",
            x=["Repair & Resale", "Refurbishment", "Resale As New", "Manufacturer Return", "Recycling"],
            y=[nrv_repair, nrv_refurb, nrv_as_new, nrv_mfg, nrv_recycle],
            marker_color=["#2ecc71" if nrv_repair > 0 else "#e74c3c", "#3498db", "#9b59b6", "#f39c12", "#95a5a6"]
        )
    ])
    fig.update_layout(title="Comparative Net Recovery Economics (USD)", yaxis_title="Net Value (USD)", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    if st.button("🚀 Publish Finalized Assessment Report (Triggers 5-Day SLA Clock)", type="primary"):
        if not insp_id_input:
            st.error("Please enter a valid Inspection ID.")
        else:
            payload = {
                "expected_resale_value": str(resale_val),
                "parts_cost": str(parts_cost),
                "labour_cost": str(labour_cost),
                "packaging_cost": str(packaging_cost),
                "transportation_cost": str(transport_cost),
                "sanitization_cost": str(sanitization_cost),
                "applicable_return_credit": str(return_credit),
                "remaining_return_shipping_cost": str(mfg_shipping),
                "is_open_box_resale_eligible": open_box_eligible
            }
            res_pub = api.post(f"/assessments/publish/{insp_id_input}", payload)
            if res_pub["success"]:
                report = res_pub["data"]
                st.success(f"✅ Assessment Report Published! Recommended Route: `{report['recommended_option']}`")
                st.info(f"**Rationale:** {report['recommendation_rationale']}")
                st.warning(f"⏰ Manufacturer Approval Deadline: `{report['approval_deadline']}` (5-Day SLA Clock Active)")
            else:
                st.error(f"Failed to publish report: {res_pub.get('error')}")
