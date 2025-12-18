import streamlit as st
from pathlib import Path
from datetime import date
from orchestration.controller_adapter import (
    tool_run_daily_digest_impl,
    tool_run_weekly_summary_impl,
    tool_simulate_scenario_impl,
)

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
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

        st.subheader(f"Status: {status_badge(result['status_label'])}")

        # ----------------------------
        # Accounts
        # ----------------------------
        st.markdown("### 💳 Accounts")
        cols = st.columns(len(result["accounts_summary"]))
        for col, (acc, bal) in zip(cols, result["accounts_summary"].items()):
            col.metric(acc, bal)

        # ----------------------------
        # Envelopes
        # ----------------------------
        st.markdown("### 📦 Envelopes")
        for env_id in result["envelopes_remaining"]:
            spent = result["envelopes_spend"].get(env_id, "0")
            remaining = result["envelopes_remaining"][env_id]
            st.write(f"**{env_id}** — Spent: {spent} | Remaining: {remaining}")

        # ----------------------------
        # Rules
        # ----------------------------
        st.markdown("### ⚠️ Rule Evaluations")
        for ev in result["rule_evaluations"]:
            msg = ev["message"]
            if ev["status"] == "violation":
                st.error(msg)
            elif ev["status"] == "warning":
                st.warning(msg)
            else:
                st.info(msg)

        # ----------------------------
        # Recommendations
        # ----------------------------
        st.markdown("### 🧭 Recommended Actions")

        recommendations = sorted(
            result["recommendations"],
            key=lambda r: normalize_priority(r.get("priority")),
        )

        if not recommendations:
            st.success("No actions required for this day.")
        else:
            for rec in recommendations:
                priority = normalize_priority(rec.get("priority"))

                if priority == 1:
                    container = st.error
                    badge = "🔴 Critical"
                elif priority == 2:
                    container = st.warning
                    badge = "🟠 Important"
                else:
                    container = st.info
                    badge = "🟢 Optional"

                with container(f"{badge} — {rec.get('action_type', 'Action')}"):
                    st.markdown(f"**What to do:** {rec.get('description', '')}")

                    details = rec.get("details") or {}
                    if details:
                        st.markdown("**Details:**")
                        for k, v in details.items():
                            st.write(f"- {k}: {v}")

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

        st.subheader(f"Overall Status: {status_badge(result['overall_status_label'])}")
        st.write(result["weekly_narrative"])

        st.markdown("### 📊 Average Daily Spend per Envelope")
        for env, avg in result["average_daily_spend_per_envelope"].items():
            st.write(f"{env}: {avg}")

        st.markdown("### 🚨 Rule Violations (Count)")
        for rule_id, count in result["rule_violation_counts"].items():
            st.write(f"{rule_id}: {count}")

# =====================================================================
# SCENARIO TAB
# =====================================================================
with tabs[2]:
    st.header("Scenario Simulation")

    sim_date = st.date_input(
        "Scenario date",
        value=date.today(),
        key="scenario_date",
    )

    st.markdown("#### One-off Planned Spend")
    amount = st.text_input("Amount (USD)", value="")
    envelope_id = st.text_input("Envelope ID", value="")
    description = st.text_input("Description", value="")

    if st.button("Simulate Scenario"):
        one_off = None
        if amount and envelope_id:
            one_off = {
                "amount": amount,
                "envelope_id": envelope_id,
                "description": description or "Planned spend",
            }

        result = tool_simulate_scenario_impl(
            config_dir=CONFIG_DIR,
            data_dir=DATA_DIR,
            as_of_date_str=sim_date.isoformat(),
            one_off_spend=one_off,
        )

        st.markdown("### 📦 Baseline Remaining Budgets")
        st.json(result["baseline_envelopes_remaining"])

        st.markdown("### 🧪 Scenario Remaining Budgets")
        st.json(result["scenario_envelopes_remaining"])

        st.markdown("### 📝 Impact Summary")
        st.write(result["impact_summary"])
