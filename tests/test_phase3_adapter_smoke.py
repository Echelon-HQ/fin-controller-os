from __future__ import annotations

from pathlib import Path

from orchestration.controller_adapter import (
    tool_run_daily_digest_impl,
    tool_run_weekly_summary_impl,
    tool_simulate_scenario_impl,
    tool_explain_log_entry_impl,
)


CONFIG_DIR = Path("config")
DATA_DIR = Path("data")
LOG_DIR = Path("log")


def test_run_daily_digest_smoke():
    result = tool_run_daily_digest_impl(
        config_dir=CONFIG_DIR,
        data_dir=DATA_DIR,
        log_dir=LOG_DIR,
        as_of_date_str="2025-11-20",
        mode="summary",
    )

    # Basic shape checks
    for key in [
        "date",
        "status_label",
        "accounts_summary",
        "envelopes_spend",
        "envelopes_remaining",
        "rule_evaluations",
        "recommendations",
        "text_summary",
    ]:
        assert key in result

    assert isinstance(result["accounts_summary"], dict)
    assert isinstance(result["envelopes_spend"], dict)
    assert isinstance(result["envelopes_remaining"], dict)
    assert isinstance(result["rule_evaluations"], list)
    assert isinstance(result["recommendations"], list)


def test_run_weekly_summary_smoke():
    # Make sure we have at least a few days of log entries first.
    # This will create entries for 7 days in the log.
    for day in range(20, 27):
        tool_run_daily_digest_impl(
            config_dir=CONFIG_DIR,
            data_dir=DATA_DIR,
            log_dir=LOG_DIR,
            as_of_date_str=f"2025-11-{day:02d}",
            mode="summary",
        )

    result = tool_run_weekly_summary_impl(
        log_dir=LOG_DIR,
        week_ending_date_str="2025-11-26",
    )

    for key in [
        "start_date",
        "end_date",
        "days_covered",
        "average_daily_spend_per_envelope",
        "rule_violation_counts",
        "overall_status_label",
        "weekly_narrative",
    ]:
        assert key in result

    assert isinstance(result["average_daily_spend_per_envelope"], dict)
    assert isinstance(result["rule_violation_counts"], dict)
    assert isinstance(result["days_covered"], int)


def test_simulate_scenario_smoke():
    # Use a date you know has some transactions
    as_of_date = "2025-11-20"

    result = tool_simulate_scenario_impl(
        config_dir=CONFIG_DIR,
        data_dir=DATA_DIR,
        as_of_date_str=as_of_date,
        one_off_spend={
            "amount": "1500.00",
            "envelope_id": "discretionary",  # adjust if your ID is different
            "description": "Test sofa purchase",
        },
        envelope_adjustments=None,
    )

    for key in [
        "baseline_envelopes_remaining",
        "scenario_envelopes_remaining",
        "impact_summary",
    ]:
        assert key in result

    baseline = result["baseline_envelopes_remaining"]
    scenario = result["scenario_envelopes_remaining"]

    assert isinstance(baseline, dict)
    assert isinstance(scenario, dict)
    assert isinstance(result["impact_summary"], str)

    # At least one envelope should differ between baseline and scenario
    assert any(
        baseline.get(env_id) != scenario.get(env_id)
        for env_id in baseline.keys()
    )


def test_explain_log_entry_smoke():
    # Ensure the log has this date recorded
    tool_run_daily_digest_impl(
        config_dir=CONFIG_DIR,
        data_dir=DATA_DIR,
        log_dir=LOG_DIR,
        as_of_date_str="2025-11-20",
        mode="summary",
    )

    result = tool_explain_log_entry_impl(
        log_dir=LOG_DIR,
        date_str="2025-11-20",
    )

    for key in [
        "date",
        "rule_summary",
        "recommendation_summary",
        "narrative_explanation",
    ]:
        assert key in result

    assert isinstance(result["rule_summary"], str)
    assert isinstance(result["recommendation_summary"], str)
    assert isinstance(result["narrative_explanation"], str)
    assert result["date"] == "2025-11-20"