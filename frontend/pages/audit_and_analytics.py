from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    from frontend.client import api
except ImportError:
    from client import api

try:
    st.set_page_config(page_title="Audit & Analytics", page_icon="📊", layout="wide")
except Exception:
    pass
st.title("📊 Recovery Analytics & Immutable Audit Trail")
st.caption("Financial performance, circular economy metrics, and append-only governance trail.")

current_user = st.session_state.get("current_user")
if not current_user:
    st.warning("⚠️ Please log in to access analytics and audit reports.")
    st.stop()

tab_analytics, tab_audit, tab_sla = st.tabs([
    "📈 1. Financial & Recovery Metrics",
    "🛡️ 2. Immutable Audit Trail",
    "⏰ 3. SLA Timeout Operations"
])

with tab_analytics:
    st.markdown("### 💰 Financial Recovery vs. Expenses Summary")
    res_summary = api.get("/reports/recovery-summary")

    if res_summary["success"] and res_summary["data"]:
        data = res_summary["data"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Returned Products", f"{data['total_returned_items']} units")
        m2.metric("Executed Recovery Orders", f"{data['completed_recovery_orders']} orders")
        m3.metric("Total Recovery Costs", f"${data['total_recovery_expenses']:,.2f}", "Parts + Labour")
        net_val = data['net_financial_recovery']
        m4.metric("Net Financial Recovery", f"${net_val:,.2f}", delta=f"${data['total_actual_resale_proceeds']:,.2f} Proceeds")

        st.markdown("---")
        # Visual Waterfall Chart of Recovery Value Flow
        fig_waterfall = go.Figure(go.Waterfall(
            name="Recovery Cash Flow",
            orientation="v",
            measure=["relative", "relative", "total"],
            x=["Actual Resale Proceeds", "Parts & Labour Expenses", "Net Cash Realized"],
            textposition="outside",
            text=[f"+${data['total_actual_resale_proceeds']:.2f}", f"-${data['total_recovery_expenses']:.2f}", f"${net_val:.2f}"],
            y=[data['total_actual_resale_proceeds'], -data['total_recovery_expenses'], net_val],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
        ))
        fig_waterfall.update_layout(title="Net Financial Recovery Waterfall (USD)", template="plotly_white")
        st.plotly_chart(fig_waterfall, use_container_width=True)
    else:
        st.info("No recovery financial data recorded yet.")

with tab_audit:
    st.markdown("### 📜 Append-Only Audit History")
    st.caption("Full traceability: Every state change, custody handover, assessment report, and authorization decision is permanently recorded.")

    res_audit = api.get("/reports/audit-events", params={"limit": 100})
    if res_audit["success"] and res_audit["data"]:
        events = res_audit["data"]
        df_audit = pd.DataFrame(events)
        df_display = df_audit[["timestamp", "action", "entity_name", "entity_id", "actor_user_id", "reason"]]
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("No audit events recorded yet.")

with tab_sla:
    st.markdown("### ⏰ Five-Day SLA Timeout Worker Management")
    st.info(
        """
        **SLA Policy Rule:**
        When an assessment report is finalized, a 120-hour (5-day) clock begins.
        - T + 48h: 1st Friendly Reminder dispatched to manufacturer contacts.
        - T + 96h: 2nd Urgent Reminder dispatched.
        - T + 120h: Deadline reached. If partner contract authorizes return on timeout, return procedure is automatically initiated. Otherwise, item is placed on secure hold and escalated. Silence is never interpreted as permission to repair or resell.
        """
    )
    if st.button("⚡ Trigger Manual SLA Non-Response Scan", type="primary"):
        res_sla = api.post("/reports/trigger-sla-check", {})
        if res_sla["success"]:
            st.success(f"SLA worker executed successfully! Processed {res_sla['data']['processed_sla_requests']} pending approval requests.")
        else:
            st.error(f"SLA execution failed: {res_sla.get('error')}")
