import sys
from pathlib import Path
from datetime import date

import streamlit as st

# -------------------------------------------------------------------
# Ensure project root is on PYTHONPATH (required for Streamlit)
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from orchestration.controller_adapter import (
    tool_run_daily_digest_impl,
    tool_run_weekly_summary_impl,
    tool_simulate_scenario_impl,
)

# -------------------------------------------------------------------
# Page configuration
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Financial Controller",
    layout="wide",
)

st.title("💼 Financial Controller Dashboard")

# -------------------------------------------------------------------
# Tabs
# -------------------------------------------------------------------
tab_daily, tab_weekly, tab_scenario = st.tabs(
    ["📅 Daily", "📊 Weekly", "🧪 Scenario"]
)

# ===================================================================
# DAILY TAB
# ===================================================================
with tab_daily:
    col1, col2 = st.columns([2, 1])

    with col1:
        selected_date = st.date_input(
            "Evaluation date",
            value=date.today(),
            key="daily_date",
        )

    with col2:
        run_controller = st.button(
            "▶ Run Daily Digest",
            use_container_width=True,
        )

    if run_controller:
        with st.spinner("Running financial controller..."):
            result = tool_run_daily_digest_impl(
                config_dir=BASE_DIR / "config",
                data_dir=BASE_DIR / "data",
                log_dir=BASE_DIR / "log",
                as_of_date_str=selected_date.isoformat(),
            )

        # --------------------------------------------------------------
        # Status
        # --------------------------------------------------------------
        status = result["status_label"]
        st.metric("Daily Status", status.upper())

        # --------------------------------------------------------------
        # Accounts & Envelopes
        # --------------------------------------------------------------
        left_col, right_col = st.columns(2)

        with left_col:
            st.markdown("## 🏦 Accounts")
            st.table(
                [
                    {"Account": acc, "Balance": bal}
                    for acc, bal in result["accounts_summary"].items()
                ]
            )

        with right_col:
            st.markdown("## 📦 Envelopes")
            for env_id, remaining in result["envelopes_remaining"].items():
                spent = float(result["envelopes_spend"].get(env_id, "0"))
                remaining_f = float(remaining)
                total = spent + remaining_f

                progress = spent / total if total > 0 else 0

                st.write(f"**{env_id}**")
                st.progress(min(progress, 1.0))
                st.caption(f"Spent: {spent} · Remaining: {remaining}")

        # --------------------------------------------------------------
        # Rules
        # --------------------------------------------------------------
        st.markdown("## 📏 Rule Evaluations")
        for rule in result["rule_evaluations"]:
            icon = (
                "❌" if rule["status"] == "violation"
                else "⚠️" if rule["status"] == "warning"
                else "✅"
            )
            st.write(f"{icon} **{rule['rule_id']}**")
            st.caption(rule["message"])

        # --------------------------------------------------------------
        # Advanced Recommendations
        # --------------------------------------------------------------
        st.markdown("## 🧭 Recommended Actions")

        recommendations = sorted(
            result["recommendations"],
            key=lambda r: int(r.get("priority", 99)),
        )

        if not recommendations:
            st.success("No actions required for this day.")
        else:
            for rec in recommendations:
                try:
                    priority = int(rec["priority"])
                except (ValueError, TypeError):
                    priority = 99

                if priority <= 1:
                    badge = "🔴 Critical"
                    container = st.error
                elif priority == 2:
                    badge = "🟠 Important"
                    container = st.warning
                else:
                    badge = "🟢 Optional"
                    container = st.info

                with container(f"{badge} — {rec['action_type']}"):
                    st.markdown(f"**What to do:** {rec['description']}")

                    if rec.get("details"):
                        st.markdown("**Details:**")
                        for k, v in rec["details"].items():
                            st.write(f"- {k}: {v}")

        with st.expander("🔍 Raw controller output"):
            st.json(result)

# ===================================================================
# WEEKLY TAB
# ===================================================================
with tab_weekly:
    st.subheader("📊 Weekly Summary")

    week_ending = st.date_input(
        "Week ending date",
        value=date.today(),
        key="weekly_date",
    )

    if st.button("Run Weekly Summary"):
        with st.spinner("Computing weekly summary..."):
            weekly = tool_run_weekly_summary_impl(
                log_dir=BASE_DIR / "log",
                week_ending_date_str=week_ending.isoformat(),
            )

        st.metric("Overall Status", weekly["overall_status_label"].upper())
        st.metric("Days Covered", weekly["days_covered"])

        st.markdown("### Average Daily Spend per Envelope")
        st.table(
            [
                {"Envelope": k, "Avg Daily Spend": v}
                for k, v in weekly["average_daily_spend_per_envelope"].items()
            ]
        )

        st.markdown("### Rule Violations")
        if not weekly["rule_violation_counts"]:
            st.success("No rule violations this week 🎉")
        else:
            st.table(
                [
                    {"Rule": k, "Violations": v}
                    for k, v in weekly["rule_violation_counts"].items()
                ]
            )

# ===================================================================
# SCENARIO TAB
# ===================================================================
with tab_scenario:
    st.subheader("🧪 Scenario Simulation")

    sim_date = st.date_input(
        "Scenario date",
        value=date.today(),
        key="scenario_date",
    )

    amount = st.text_input("One-off spend amount (e.g. 1500.00)")
    envelope_id = st.text_input("Envelope ID (e.g. discretionary)")
    description = st.text_input("Description", value="Planned purchase")

    if st.button("Run Scenario"):
        if not amount or not envelope_id:
            st.error("Amount and envelope ID are required.")
        else:
            with st.spinner("Running scenario simulation..."):
                scenario = tool_simulate_scenario_impl(
                    config_dir=BASE_DIR / "config",
                    data_dir=BASE_DIR / "data",
                    as_of_date_str=sim_date.isoformat(),
                    one_off_spend={
                        "amount": amount,
                        "envelope_id": envelope_id,
                        "description": description,
                    },
                )

            st.markdown("### Baseline Remaining")
            st.json(scenario["baseline_envelopes_remaining"])

            st.markdown("### Scenario Remaining")
            st.json(scenario["scenario_envelopes_remaining"])

            st.info(scenario["impact_summary"])
