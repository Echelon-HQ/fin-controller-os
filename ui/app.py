import streamlit as st
import os
from pathlib import Path
from datetime import date
from orchestration.controller_adapter import (
    tool_run_daily_digest_impl,
    tool_run_weekly_summary_impl,
    tool_simulate_scenario_impl,
)

# ---------------------------------------------------------------------
# Paths (Updated for Docker)
# ---------------------------------------------------------------------
# If running in Docker (APP_HOME is set), use /app. Otherwise, use relative path.
if os.getenv("APP_HOME"):
    BASE_DIR = Path(os.getenv("APP_HOME"))
else:
    BASE_DIR = Path(__file__).resolve().parents[1]

CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "log"

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def normalize_priority(raw):
    """
    Normalize priority to an integer.
    Lower number = higher urgency.
    Handles numeric and semantic priorities.
    """
    if raw is None:
        return 99

    if isinstance(raw, (int, float)):
        return int(raw)

    if isinstance(raw, str):
        raw_lower = raw.lower()

        if raw_lower.isdigit():
            return int(raw_lower)

        mapping = {
            "critical": 1,
            "high": 1,
            "warning": 2,
            "medium": 2,
            "info": 3,
            "low": 3,
        }
        return mapping.get(raw_lower, 99)

    return 99


def status_badge(status):
    if status == "critical":
        return "🔴 CRITICAL"
    if status == "tight":
        return "🟠 TIGHT"
    return "🟢 STABLE"


# ---------------------------------------------------------------------
# Streamlit Page Config
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Financial Controller",
    layout="wide",
)

st.title("💼 Financial Controller")

tabs = st.tabs(["📅 Daily", "📊 Weekly", "🧪 Scenario"])

# =====================================================================
# DAILY TAB
# =====================================================================
with tabs[0]:
    st.header("Daily Financial Digest")

    selected_date = st.date_input(
        "Select date",
        value=date.today(),
    )

    if st.button("Run Daily Digest"):
        result = tool_run_daily_digest_impl(
            config_dir=CONFIG_DIR,
            data_dir=DATA_DIR,
            log_dir=LOG_DIR,
            as_of_date_str=selected_date.isoformat(),
        )
        if result.get("status") == "success":
            st.success("Daily digest run successfully!")
            
            # Display digest content if available
            digest = result.get("digest", {})
            if digest:
                st.subheader("📝 Digest Summary")
                st.markdown(f"**Date:** {digest.get('date')}")
                
                # Alerts
                alerts = digest.get("alerts", [])
                if alerts:
                    st.warning(f"Found {len(alerts)} Alerts")
                    for a in alerts:
                        st.write(f"- {a}")
                else:
                    st.info("No alerts generated.")

            st.json(result)
        else:
            st.error(f"Error: {result.get('message')}")


# =====================================================================
# WEEKLY TAB
# =====================================================================
with tabs[1]:
    st.header("Weekly Summary")

    week_end = st.date_input(
        "Week ending date",
        value=date.today(),
        key="week_end",
    )

    if st.button("Run Weekly Summary"):
        result = tool_run_weekly_summary_impl(
            log_dir=LOG_DIR,
            week_ending_date_str=week_end.isoformat(),
        )
        if result.get("status") == "success":
            st.success("Weekly summary generated!")
            st.json(result)
        else:
            st.error(f"Error: {result.get('message')}")


# =====================================================================
# SCENARIO TAB
# =====================================================================
with tabs[2]:
    st.header("Scenario Simulation")

    st.markdown("Simulate a transaction to see how it affects budget/rules.")

    col1, col2 = st.columns(2)
    with col1:
        s_amount = st.number_input("Amount", value=100.0)
        s_currency = st.selectbox("Currency", ["USD", "EUR", "GBP"], index=0)
    with col2:
        s_desc = st.text_input("Description", "Grocery shopping")
        s_date = st.date_input("Date", value=date.today(), key="scen_date")

    if st.button("Simulate Transaction"):
        result = tool_simulate_scenario_impl(
            config_dir=CONFIG_DIR,
            amount=float(s_amount),
            currency=s_currency,
            description=s_desc,
            date_str=s_date.isoformat(),
        )
        
        st.subheader("Simulation Results")
        st.json(result)
