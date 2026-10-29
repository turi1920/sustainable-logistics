from pathlib import Path
import sys
import streamlit as st

# Ensure project root is on sys.path so 'frontend' package is resolvable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from frontend.client import api
except ImportError:
    from client import api

st.set_page_config(
    page_title="Sustainable Reverse Logistics",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Demo User Personas with standard credentials
DEMO_USERS = {
    "Alex Vance (Platform Admin)": ("admin@reverse-logistics.com", "password123"),
    "Sam Fisher (Return Agent)": ("agent@reverse-logistics.com", "password123"),
    "Elena Rostova (Operations Specialist)": ("ops@reverse-logistics.com", "password123"),
    "Marcus Brody (Apex Approver)": ("approver@apex.com", "password123"),
    "Tali'Zorah (Nova Approver)": ("approver@nova.com", "password123"),
    "Sarah Connor (Finance & Sustainability)": ("analyst@reverse-logistics.com", "password123"),
    "Jax Briggs (Recovery Technician)": ("tech@reverse-logistics.com", "password123"),
}

# Sidebar Authentication Section
st.sidebar.header("🔐 User Authentication")

current_user = st.session_state.get("current_user")

if current_user:
    st.sidebar.success(f"**Logged in as:** {current_user['full_name']}")
    st.sidebar.info(f"**Role:** `{current_user['role']}`")
    if st.sidebar.button("Logout", key="logout_btn", type="secondary"):
        st.session_state.pop("access_token", None)
        st.session_state.pop("current_user", None)
        st.rerun()
else:
    st.sidebar.markdown("### Quick Demo Login")
    selected_demo = st.sidebar.selectbox("Choose Persona", list(DEMO_USERS.keys()), key="demo_persona_select")
    if st.sidebar.button("Login as Selected Role", key="login_btn", type="primary"):
        email, pw = DEMO_USERS[selected_demo]
        res = api.login(email, pw)
        if res["success"]:
            st.sidebar.success("Logged in successfully!")
            st.rerun()
        else:
            st.sidebar.error(f"Login failed: {res.get('error')}")


def render_home():
    st.title("♻️ Sustainable Reverse Logistics Platform")
    st.subheader("Enterprise Post-Consumer Electronics Recovery & Decision System")

    # Current role banner
    if current_user:
        st.info(f"👤 Active Session: **{current_user['full_name']}** — Role: `{current_user['role']}`. Use the sidebar to access your authorized portals.")
    else:
        st.warning("⚠️ You are currently browsing as a guest. Please select a demo persona in the sidebar and log in to view and access your role-specific operational tools.")

    # Architecture & Workflow Overview Cards
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Architecture", "Modular Monolith", "FastAPI + Streamlit")
    col2.metric("Financial Engine", "Decimal NRV", "Multi-Option Recovery")
    col3.metric("Contract SLA", "120h Non-Response", "Auto-Return / Hold")
    col4.metric("Privacy Gate", "NIST SP 800-88", "Cryptographic Gate")

    st.markdown("### 🧭 Role-Based Operational Portals")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            """
            - **Platform Administrator (`PLATFORM_ADMIN`):**
              Full end-to-end custody access, manual return intake, contract & SLA policy management, refund approvals.
            - **Return Agent (`RETURN_AGENT`):**
              Assigned collection tasks, customer premises inspection, serial/tag verification, preliminary damage classification (`LOW`/`MEDIUM`/`HIGH`).
            - **Operations Specialist (`OPERATIONS_SPECIALIST`):**
              Warehouse intake, storage bin allocation, 10-point technical diagnostics, Net Recovery Value (NRV) calculation.
            """
        )
    with col_b:
        st.markdown(
            """
            - **Manufacturer Approver (`MANUFACTURER_APPROVER`):**
              Tenant-isolated authorization portal, Path A pre-authorization rules, individual & batch authorization review.
            - **Recovery Technician (`RECOVERY_TECHNICIAN`):**
              Repair & refurbishment work order execution, QA test submission, NIST 800-88 data sanitization, resale release verification.
            - **Finance & Sustainability Analyst (`FINANCE_SUSTAINABILITY_ANALYST`):**
              Disbursement ledger, refund reconciliation, circular recovery metrics, immutable audit trail.
            """
        )

    # Backend Health Status Check
    st.markdown("---")
    health_check = api.get("/health")
    if health_check["success"]:
        st.success(f"🟢 Backend API Connected: {health_check['data']['status'].upper()} (Environment: `{health_check['data']['environment']}`)")
    else:
        st.warning("🟡 Backend API connecting... Please ensure the FastAPI server is running on port 8000.")


# Define Pages
page_home = st.Page(render_home, title="Dashboard & Login", icon="🏠", default=True)
page_return_reg = st.Page("pages/return_registration.py", title="Return Registration", icon="📋")
page_pickup = st.Page("pages/pickup_agent.py", title="Pickup Agent Portal", icon="🚚")
page_warehouse = st.Page("pages/warehouse_custody.py", title="Warehouse Custody", icon="🏬")
page_inspection = st.Page("pages/technical_inspection.py", title="Technical Inspection", icon="🔬")
page_approvals = st.Page("pages/manufacturer_approvals.py", title="Manufacturer Approvals", icon="🛡️")
page_execution = st.Page("pages/recovery_execution.py", title="Recovery Execution", icon="⚙️")
page_refunds = st.Page("pages/refunds_management.py", title="Refunds Management", icon="💰")
page_audit = st.Page("pages/audit_and_analytics.py", title="Audit & Analytics", icon="📊")

# Build navigation dynamically based on role
role = current_user.get("role") if current_user else None

if not current_user:
    nav_structure = {
        "Portal": [page_home]
    }
elif role == "PLATFORM_ADMIN":
    nav_structure = {
        "Portal": [page_home],
        "Intake & Field": [page_return_reg, page_pickup],
        "Depot & Diagnostics": [page_warehouse, page_inspection],
        "Governance & Execution": [page_approvals, page_execution],
        "Finance & Compliance": [page_refunds, page_audit],
    }
elif role == "RETURN_AGENT":
    nav_structure = {
        "Portal": [page_home],
        "Field Operations": [page_pickup],
    }
elif role == "OPERATIONS_SPECIALIST":
    nav_structure = {
        "Portal": [page_home],
        "Depot Operations": [page_warehouse, page_inspection],
        "Workshop & QA": [page_execution],
        "Reporting": [page_audit],
    }
elif role == "MANUFACTURER_APPROVER":
    nav_structure = {
        "Portal": [page_home],
        "Manufacturer Approvals": [page_approvals],
    }
elif role == "FINANCE_SUSTAINABILITY_ANALYST":
    nav_structure = {
        "Portal": [page_home],
        "Finance & Reconciliation": [page_refunds],
        "Governance & Metrics": [page_audit],
    }
elif role == "RECOVERY_TECHNICIAN":
    nav_structure = {
        "Portal": [page_home],
        "Workshop Operations": [page_warehouse, page_execution],
    }
else:
    nav_structure = {
        "Portal": [page_home]
    }

pg = st.navigation(nav_structure)
pg.run()
