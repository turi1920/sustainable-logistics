import streamlit as st
from frontend.client import api

st.set_page_config(page_title="Return Registration", page_icon="📋", layout="wide")
st.title("📋 Return Registration & Intake")
st.caption("Manual return registration for authorized administrators (extensible for future ecommerce integrations).")

current_user = st.session_state.get("current_user")
if not current_user:
    st.warning("⚠️ Please log in from the main page as an Administrator to register returns.")
    st.stop()

if current_user["role"] != "PLATFORM_ADMIN":
    st.error(f"⛔ Access Denied. Your current role is `{current_user['role']}`. Only `PLATFORM_ADMIN` can register returns.")
    st.stop()

# Registration Form
with st.expander("➕ Register New Return Case", expanded=True):
    with st.form("return_reg_form"):
        col1, col2 = st.columns(2)
        with col1:
            order_ref = st.text_input("External Order Reference *", placeholder="e.g. ORD-AMZ-2026-9921")
            customer_name = st.text_input("Customer Name *", placeholder="Jane Doe")
            customer_email = st.text_input("Customer Email *", placeholder="jane.doe@example.com")
            customer_phone = st.text_input("Customer Phone *", placeholder="555-0144")
        with col2:
            pickup_address = st.text_area("Pickup Address *", placeholder="123 Tech Lane, Apt 4B")
            pickup_city = st.text_input("Pickup City *", placeholder="San Jose")
            pickup_postal_code = st.text_input("Postal Code *", placeholder="95112")

        st.markdown("#### Returned Product Details")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            mfg_choice = st.selectbox("Manufacturer", [
                ("Apex Electronics Inc.", "776caf19-8f38-40a4-a756-7a3ce22e19b3"),
                ("Nova Computing Systems", "a1111111-1111-1111-1111-111111111111")
            ], format_func=lambda x: x[0])
            product_name = st.text_input("Product Name *", placeholder="e.g. Apex UltraBook Pro 15")
        with col_p2:
            category = st.selectbox("Product Category", ["LAPTOP", "SMARTPHONE", "TABLET", "AUDIO", "MONITOR", "COMPONENT"])
            model_num = st.text_input("Model Number *", placeholder="e.g. UB-15-2025")
        with col_p3:
            serial_num = st.text_input("Declared Serial Number", placeholder="e.g. SN-8899221")
            requires_san = st.checkbox("Stores Personal Data (Requires Sanitization)", value=True)

        return_reason = st.text_input("Return Reason *", placeholder="e.g. Intermittent display blackouts, wants refund")

        submitted = st.form_submit_button("Submit Return Registration", type="primary")

        if submitted:
            if not order_ref or not customer_name or not customer_email or not product_name or not model_num:
                st.error("Please fill in all mandatory fields marked with an asterisk (*).")
            else:
                payload = {
                    "external_order_ref": order_ref,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "pickup_address": pickup_address,
                    "pickup_city": pickup_city,
                    "pickup_postal_code": pickup_postal_code,
                    "items": [
                        {
                            "manufacturer_org_id": mfg_choice[1],
                            "product_name": product_name,
                            "product_category": category,
                            "model_number": model_num,
                            "declared_serial_number": serial_num if serial_num else None,
                            "return_reason": return_reason,
                            "requires_data_sanitization": requires_san
                        }
                    ]
                }
                res = api.post("/returns", payload)
                if res["success"]:
                    st.success(f"✅ Return Registered Successfully! Case Number: `{res['data']['case_number']}`")
                else:
                    st.error(f"Failed to register return: {res.get('error')}")

# Existing Returns List
st.markdown("---")
st.subheader("📦 Registered Return Requests")

res_list = api.get("/returns")
if res_list["success"] and res_list["data"]:
    for req in res_list["data"]:
        with st.container():
            st.markdown(f"**Case:** `{req['case_number']}` | **Order:** `{req['external_order_ref']}` | **Customer:** {req['customer_name']} | **Status:** `{req['status']}`")
            if req.get("items"):
                for itm in req["items"]:
                    st.caption(f"↳ **Item Tag:** `{itm['item_tag']}` | **Product:** {itm['product_name']} ({itm['product_category']}) | **Location:** `{itm['current_custody_location']}` | **Approval:** `{itm['approval_status']}`")
            st.divider()
else:
    st.info("No return requests found.")
