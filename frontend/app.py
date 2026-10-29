import streamlit as st
from frontend.client import api

st.set_page_state = "wide"
st.set_page_config(
    page_title="Sustainable Reverse Logistics",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("♻️ Sustainable Reverse Logistics Platform")
st.subheader("Enterprise Post-Consumer Electronics Recovery & Decision System")

# Sidebar Authentication & Session
st.sidebar.header("🔐 User Authentication")

DEMO_USERS = {
    "Alex Vance (Platform Admin)": ("admin@reverse-logistics.com", "password123"),
    "Sam Fisher (Return Agent)": ("agent@reverse-logistics.com", "password123"),
    "Elena Rostova (Operations Specialist)": ("ops@reverse-logistics.com", "password123"),
    "Marcus Brody (Apex Approver)": ("approver@apex.com", "password123"),
    "Sarah Connor (Finance & Sustainability)": ("analyst@reverse-logistics.com", "password123"),
}

current_user = st.session_state.get("current_user")

if current_user:
    st.sidebar.success(f"**Logged in as:** {current_user['full_name']}")
    st.sidebar.info(f"**Role:** `{current_user['role']}`")
    if st.sidebar.button("Logout"):
        st.session_state.pop("access_token", None)
        st.session_state.pop("current_user", None)
        st.rerun()
else:
    st.sidebar.markdown("### Quick Demo Login")
    selected_demo = st.sidebar.selectbox("Choose Persona", list(DEMO_USERS.keys()))
    if st.sidebar.button("Login as Selected Role"):
        email, pw = DEMO_USERS[selected_demo]
        res = api.login(email, pw)
        if res["success"]:
            st.sidebar.success("Logged in successfully!")
            st.rerun()
        else:
            st.sidebar.error(f"Login failed: {res.get('error')}")

# Architecture & Workflow Overview Cards
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Architecture", "Modular Monolith", "FastAPI + Streamlit")
col2.metric("Database", "PostgreSQL / SQLAlchemy", "Decimal Money")
col3.metric("SLA Timeout", "5-Day Non-Response", "Contract Governed")
col4.metric("Privacy Gate", "NIST 800-88 Purge", "Resale Blocker")

st.markdown("### 🧭 Role-Based Operational Portals")
st.markdown(
    """
    Select an operational portal from the sidebar navigation to perform workflow actions:
    1. **📋 Return Registration:** Intake manual return requests and generate tracking tags.
    2. **🚚 Pickup Agent Portal:** View assigned field collections, verify product identifiers, and log preliminary damage.
    3. **🏬 Warehouse Custody:** Log custody handovers, warehouse receipt, storage bin allocation, and inspect chronological timeline.
    4. **🔬 Technical Inspection:** Record detailed test findings, screen/battery condition, and run the Net Recovery Value (NRV) calculation engine.
    5. **🛡️ Manufacturer Approvals:** Review assessment reports, configure pre-authorization policy rules, and submit individual or batch approval decisions.
    6. **⚙️ Recovery Execution:** Issue repair/refurbishment work orders, perform QA testing, execute NIST 800-88 data sanitization, and release for resale.
    7. **💰 Refunds Management:** Monitor refund eligibility, record manual disbursement milestones, and link external payout references.
    8. **📊 Audit & Analytics:** Real-time financial recovery summary, actual proceeds vs. costs, and immutable audit trail.
    """
)

# Backend Health Status Check
st.markdown("---")
health_check = api.get("/health")
if health_check["success"]:
    st.success(f"🟢 Backend API Connected: {health_check['data']['status'].upper()} (Environment: `{health_check['data']['environment']}`)")
else:
    st.warning("🟡 Backend API connecting... Please ensure the FastAPI server is running on port 8000.")
