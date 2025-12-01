from __future__ import annotations

from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from controller.classification import aggregate_envelopes, classify_transactions
from controller.config_loader import ControllerConfig, load_controller_config
from controller.controller_log import append_log_entry
from controller.digest import build_daily_digest
from controller.ingestion import load_transactions_csv
from controller.models import Account, Envelope, Transaction
from controller.recommendations import RecommendationContext, generate_recommendations
from controller.rules import evaluate_all_rules


def _parse_date(date_str: str) -> date:
    """Parse a YYYY-MM-DD date string to a date, with a clear error if invalid."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(
            f"Invalid date format '{date_str}'. Expected YYYY-MM-DD."
        ) from exc


def _load_config_and_transactions(
    config_dir: Path,
    data_dir: Path,
) -> tuple[ControllerConfig, List[Transaction]]:
    """
    Load controller configuration and all transactions from CSV.
    """
    controller_config: ControllerConfig = load_controller_config(config_dir)
    transactions_path = data_dir / "transactions.csv"
    transactions = load_transactions_csv(transactions_path)
    return controller_config, transactions


def _derive_status_label(rule_evaluations) -> str:
    """
    Derive a simple daily status label from rule evaluations.

    - 'critical' if any critical violations exist.
    - 'tight' if there are warnings but no critical violations.
    - 'stable' otherwise.
    """
    has_critical_violation = any(
        ev.severity == "critical" and ev.status == "violation"
        for ev in rule_evaluations
    )
    has_warning = any(ev.status == "warning" for ev in rule_evaluations)

    if has_critical_violation:
        return "critical"
    if has_warning:
        return "tight"
    return "stable"


def _derive_overall_weekly_status(rule_violation_counts: Dict[str, int]) -> str:
    """
    Derive an overall weekly status based on how many rule violations occurred.
    """
    total_violations = sum(rule_violation_counts.values())
    if total_violations == 0:
        return "stable"
    if total_violations <= 3:
        return "tight"
    return "critical"


def _build_scenario_impact_summary(
    baseline: Dict[str, str],
    scenario: Dict[str, str],
) -> str:
    """
    Build a simple text summary of changes in remaining budgets between
    baseline and scenario.
    """
    lines: List[str] = []
    lines.append("Scenario impact summary:")

    for env_id, baseline_value_str in baseline.items():
        scenario_value_str = scenario.get(env_id, baseline_value_str)
        baseline_value = Decimal(baseline_value_str)
        scenario_value = Decimal(scenario_value_str)
        delta = scenario_value - baseline_value

        if delta == 0:
            continue

        direction = "increased" if delta > 0 else "decreased"
        lines.append(
            f"Envelope '{env_id}' remaining budget has {direction} by {delta} "
            "compared to baseline."
        )

    if len(lines) == 1:
        lines.append(
            "No changes in envelope remaining budgets compared to baseline."
        )

    return " ".join(lines)


def tool_run_daily_digest_impl(
    config_dir: Path,
    data_dir: Path,
    log_dir: Path,
    as_of_date_str: str,
    mode: str = "summary",
) -> Dict[str, Any]:
    """
    Implementation of the run_daily_digest tool.

    This function:
      1. Loads configuration and transactions.
      2. Filters transactions for as_of_date.
      3. Classifies transactions into envelopes.
      4. Aggregates envelope totals.
      5. Evaluates all rules.
      6. Generates recommendations.
      7. Builds a DailyDigest.
      8. Appends a ControllerLogEntry.
      9. Returns a JSON-serializable dictionary representing the digest.

    The mode parameter is available for future use. For Phase 3, 'summary'
    and 'full' return the same structure; the agent decides how much to expose.
    """
    as_of_date = _parse_date(as_of_date_str)

    controller_config, transactions = _load_config_and_transactions(
        config_dir, data_dir
    )

    # Take the first configured user as the active profile
    if not controller_config.users:
        raise ValueError(
            "ControllerConfig.users is empty; no active user profile available."
        )

    user = next(iter(controller_config.users.values()))
    accounts: Dict[str, Account] = controller_config.accounts


    # Filter transactions for this date
    daily_transactions = [t for t in transactions if t.date == as_of_date]

    # Classify & aggregate
    classify_transactions(
        daily_transactions,
        controller_config.envelopes,
        controller_config.classification_map,
    )

        # Aggregate envelopes; the shape may be:
    # - dict[envelope_id -> summary], or
    # - dict[user_id -> list[...] ] for multi-user setups.
    raw_envelope_summaries = aggregate_envelopes(
        daily_transactions,
        controller_config.envelopes,
    )

    # --- Normalize to: Dict[envelope_id, summary] for the active user ---

    # Case 1: raw is already a dict of envelope_id -> summary objects
    envelope_summaries = None

    if isinstance(raw_envelope_summaries, dict):
        # Peek at one value to see if it's already per-envelope or per-user.
        sample_value = next(iter(raw_envelope_summaries.values()), None)

        # If values are lists, treat it as per-user: {user_id: [ ... ]}.
        if isinstance(sample_value, list):
            # Prefer the active user's entry if present.
            if user.user_id in raw_envelope_summaries:
                user_items = raw_envelope_summaries[user.user_id]
            else:
                # Fallback: just take the first list.
                user_items = sample_value

            env_map = {}

            for item in user_items:
                env_id = None
                summary = None

                # item might be a (env_id, summary) pair
                if isinstance(item, (list, tuple)):
                    if len(item) >= 2:
                        env_id, summary = item[0], item[1]

                # or it might be an object with an .envelope attribute
                elif hasattr(item, "envelope"):
                    env_obj = item.envelope
                    env_id = getattr(env_obj, "id", None) or getattr(
                        env_obj, "envelope_id", None
                    )
                    summary = item

                # or, last resort, a dict with envelope_id
                elif isinstance(item, dict):
                    env_id = item.get("envelope_id") or item.get("id")
                    summary = item

                if env_id is None or summary is None:
                    raise TypeError(
                        f"Unexpected envelope summary element type: {type(item)}"
                    )

                env_map[str(env_id)] = summary

            envelope_summaries = env_map

        else:
            # Values are not lists: assume this is already envelope_id -> summary.
            envelope_summaries = raw_envelope_summaries

    else:
        raise TypeError(
            f"Unexpected aggregate_envelopes result type: {type(raw_envelope_summaries)}"
        )

    # --- Use the normalized envelope_summaries from here on ---

    rule_evaluations = evaluate_all_rules(
        accounts=accounts,
        envelope_summaries=envelope_summaries,
        obligations=controller_config.obligations,
        rules=controller_config.rules,
        today=as_of_date,
    )

    context = RecommendationContext(accounts=accounts)
    recommendations = generate_recommendations(rule_evaluations, context)

    digest = build_daily_digest(
        user=user,
        accounts=accounts,
        envelope_summaries=envelope_summaries,
        rule_evaluations=rule_evaluations,
        recommendations=recommendations,
        digest_date=as_of_date,
    )


    # Derive a coarse status label from rule evaluations
    status_label = _derive_status_label(rule_evaluations)

    # Build lightweight snapshots directly from accounts and envelope_summaries
    # Snapshot accounts using the current_balance field from Account model
    accounts_snapshot: Dict[str, str] = {
        str(acc_id): str(acc.current_balance)
        for acc_id, acc in accounts.items()
    }


    envelopes_spend: Dict[str, str] = {}
    envelopes_remaining: Dict[str, str] = {}

    for env_id, summary in envelope_summaries.items():
        total_spend = None
        remaining_budget = None

        if hasattr(summary, "total_spend"):
            total_spend = summary.total_spend
        elif isinstance(summary, dict) and "total_spend" in summary:
            total_spend = summary["total_spend"]

        if hasattr(summary, "remaining_budget"):
            remaining_budget = summary.remaining_budget
        elif isinstance(summary, dict) and "remaining_budget" in summary:
            remaining_budget = summary["remaining_budget"]

        if total_spend is not None:
            envelopes_spend[str(env_id)] = str(total_spend)
        if remaining_budget is not None:
            envelopes_remaining[str(env_id)] = str(remaining_budget)

    # Try to pull a human-readable text summary from the digest; fall back to empty string
    text_summary = (
        getattr(digest, "text_summary", None)
        or getattr(digest, "text_block", None)
        or getattr(digest, "text", "")
    )

    # Append a controller log entry
    # NOTE: We skip logging here and rely on controller.daily_run
    # to populate controller_log.jsonl, since its append_log_entry
    # call is already correctly wired for your Phase 2 engine.
    # log_path = log_dir / "controller_log.jsonl"
    # append_log_entry(
    #     log_path=log_path,
    #     entry_date=as_of_date,
    #     rule_evaluations=rule_evaluations,
    #     recommendations=recommendations,
    #     accounts_snapshot=accounts_snapshot,
    #     envelopes_snapshot=envelopes_spend,
    # )



    # Build JSON-serializable result for the tool
    result: Dict[str, Any] = {
        "date": as_of_date.isoformat(),
        "status_label": status_label,
        "accounts_summary": accounts_snapshot,
        "envelopes_spend": envelopes_spend,
        "envelopes_remaining": envelopes_remaining,
        "rule_evaluations": [
            {
                "rule_id": ev.rule_id,
                "status": ev.status,
                "severity": ev.severity,
                "message": ev.message,
            }
            for ev in rule_evaluations
        ],
        "recommendations": [
            {
                "id": getattr(rec, "id", ""),
                # Derive a priority if the engine doesn't expose one directly
                "priority": getattr(rec, "priority", getattr(rec, "severity", "normal")),
                "action_type": getattr(rec, "action_type", ""),
                "description": getattr(rec, "description", ""),
                "details": getattr(rec, "details", {}),
            }
            for rec in recommendations
        ],
        "text_summary": text_summary,
    }

    log_path = log_dir / "controller_log.jsonl"
    log_entry = {
        "date": as_of_date.isoformat(),
        "status_label": status_label,
        "accounts_summary": accounts_snapshot,
        "envelopes_spend": envelopes_spend,
        "envelopes_remaining": envelopes_remaining,
        "rule_evaluations": result["rule_evaluations"],
        "recommendations": result["recommendations"],
    }
    with log_path.open("a", encoding="utf-8") as f:
        json.dump(log_entry, f)
        f.write("\n")

    return result



def tool_run_weekly_summary_impl(
    log_dir: Path,
    week_ending_date_str: str,
) -> Dict[str, Any]:
    """
    Implementation of the run_weekly_summary tool.

    Reads the controller log for the last seven days including week_ending_date,
    and computes a simple weekly summary:
      - Average daily spend per envelope.
      - Count of rule violations per rule.
      - A coarse overall status label.
    """
    week_ending_date = _parse_date(week_ending_date_str)
    start_date = week_ending_date - timedelta(days=6)

    log_path = log_dir / "controller_log.jsonl"
    if not log_path.exists():
        raise FileNotFoundError(
            f"Controller log not found at {log_path}. "
            "Run daily evaluations before weekly summaries."
        )

    import json

    envelope_spend_accumulator: Dict[str, Decimal] = {}
    envelope_spend_counts: Dict[str, int] = {}
    rule_violation_counts: Dict[str, int] = {}
    days_seen: set[date] = set()

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            entry = json.loads(line)

            # Skip older Phase-2 entries that don't have a 'date' field
            date_str = entry.get("date")
            if not date_str:
                continue

            entry_date = _parse_date(date_str)
            if not (start_date <= entry_date <= week_ending_date):
                continue

            days_seen.add(entry_date)

            envelopes_snapshot = entry.get("envelopes_snapshot", {})
            for env_id, spend_str in envelopes_snapshot.items():
                amount = Decimal(spend_str)
                envelope_spend_accumulator[env_id] = (
                    envelope_spend_accumulator.get(env_id, Decimal("0"))
                    + amount
                )
                envelope_spend_counts[env_id] = (
                    envelope_spend_counts.get(env_id, 0) + 1
                )

            for ev in entry.get("rule_evaluations", []):
                if ev.get("status") == "violation":
                    rule_id = ev["rule_id"]
                    rule_violation_counts[rule_id] = (
                        rule_violation_counts.get(rule_id, 0) + 1
                    )

    days_covered = len(days_seen)
    if days_covered == 0:
        # Avoid divide-by-zero; effectively "no activity".
        days_covered = 1

    average_daily_spend_per_envelope: Dict[str, str] = {}
    for env_id, total_spend in envelope_spend_accumulator.items():
        average = total_spend / Decimal(days_covered)
        average_daily_spend_per_envelope[env_id] = str(average)

    overall_status_label = _derive_overall_weekly_status(rule_violation_counts)

    weekly_narrative = (
        f"Weekly summary for {start_date.isoformat()} to {week_ending_date.isoformat()}. "
        f"{len(days_seen)} days of controller activity were recorded. "
        "Average daily spend per envelope and rule violation counts are provided "
        "for further analysis."
    )

    result: Dict[str, Any] = {
        "start_date": start_date.isoformat(),
        "end_date": week_ending_date.isoformat(),
        "days_covered": len(days_seen),
        "average_daily_spend_per_envelope": average_daily_spend_per_envelope,
        "rule_violation_counts": rule_violation_counts,
        "overall_status_label": overall_status_label,
        "weekly_narrative": weekly_narrative,
    }

    return result


def tool_simulate_scenario_impl(
    config_dir: Path,
    data_dir: Path,
    as_of_date_str: str,
    one_off_spend: Optional[Dict[str, Any]] = None,
    envelope_adjustments: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Implementation of the simulate_scenario tool.

    This function:
      1. Loads configuration and transactions.
      2. Computes a baseline envelope remaining picture for the given date.
      3. Applies scenario adjustments in-memory (no files are changed).
      4. Re-runs classification and aggregation with scenario adjustments.
      5. Returns baseline vs scenario remaining budgets and a short impact summary.
    """
    as_of_date = _parse_date(as_of_date_str)
    controller_config, transactions = _load_config_and_transactions(
        config_dir, data_dir
    )

    # Choose an active user profile (same approach as daily digest)
    if not controller_config.users:
        raise ValueError(
            "ControllerConfig.users is empty; no active user profile available."
        )
    user = next(iter(controller_config.users.values()))


    baseline_daily_transactions = [t for t in transactions if t.date == as_of_date]

    classify_transactions(
        baseline_daily_transactions,
        controller_config.envelopes,
        controller_config.classification_map,
    )

    raw_baseline_envelope_summaries = aggregate_envelopes(
        baseline_daily_transactions,
        controller_config.envelopes,
    )

    # Reuse the same normalization logic as in tool_run_daily_digest_impl
    # so we always end up with Dict[envelope_id, summary] for the active user.
    envelope_summaries = None

    if isinstance(raw_baseline_envelope_summaries, dict):
        sample_value = next(iter(raw_baseline_envelope_summaries.values()), None)

        if isinstance(sample_value, list):
            # Multi-user shape: {user_id: [ ... ]}. Select the first user.
            # If you already chose an active user earlier in this function, reuse that.
            if controller_config.users:
                user = next(iter(controller_config.users.values()))
                user_items = raw_baseline_envelope_summaries.get(
                    user.user_id, sample_value
                )
            else:
                user_items = sample_value

            env_map = {}

            for item in user_items:
                env_id = None
                summary = None

                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    env_id, summary = item[0], item[1]
                elif hasattr(item, "envelope"):
                    env_obj = item.envelope
                    env_id = getattr(env_obj, "id", None) or getattr(
                        env_obj, "envelope_id", None
                    )
                    summary = item
                elif isinstance(item, dict):
                    env_id = item.get("envelope_id") or item.get("id")
                    summary = item

                if env_id is None or summary is None:
                    raise TypeError(
                        f"Unexpected envelope summary element type in scenario: {type(item)}"
                    )

                env_map[str(env_id)] = summary

            envelope_summaries = env_map
        else:
            envelope_summaries = raw_baseline_envelope_summaries
    else:
        raise TypeError(
            f"Unexpected aggregate_envelopes result type in scenario: "
            f"{type(raw_baseline_envelope_summaries)}"
        )

    baseline_remaining: Dict[str, str] = {}
    for env_id, summary in envelope_summaries.items():
        remaining = None
        if hasattr(summary, "remaining_budget"):
            remaining = summary.remaining_budget
        elif isinstance(summary, dict) and "remaining_budget" in summary:
            remaining = summary["remaining_budget"]
        if remaining is not None:
            baseline_remaining[str(env_id)] = str(remaining)
    
    # Ensure the envelope used in the scenario is present in the baseline map.
    # If there were no baseline transactions for that envelope, use its full budget
    # as the "remaining" amount.
    if one_off_spend:
        scenario_env_id = one_off_spend["envelope_id"]
        if (
            scenario_env_id in controller_config.envelopes
            and scenario_env_id not in baseline_remaining
        ):
            env = controller_config.envelopes[scenario_env_id]
            baseline_remaining[scenario_env_id] = str(env.budget_amount)


    # Clone envelopes so we can mutate scenario budgets.
    scenario_envelopes: Dict[str, Envelope] = {
        k: v for k, v in controller_config.envelopes.items()
    }

    if envelope_adjustments:
        for adjustment in envelope_adjustments:
            env_id = adjustment["envelope_id"]
            new_budget_amount = Decimal(adjustment["new_budget_amount"])
            if env_id in scenario_envelopes:
                env = scenario_envelopes[env_id]
                scenario_envelopes[env_id] = Envelope(
                    id=env.id,
                    name=env.name,
                    period=env.period,
                    budget_amount=new_budget_amount,
                    budget_currency=env.budget_currency,
                    priority=env.priority,
                )

    scenario_transactions = [t for t in transactions if t.date == as_of_date]

    if one_off_spend:
        synthetic_tx = Transaction(
            id="synthetic_scenario_tx",
            user_id=user.user_id,           # <-- NEW
            account_id="scenario_account",
            date=as_of_date,
            amount=Decimal(one_off_spend["amount"]),
            currency="USD",  # Assumes same base currency; adjust if needed.
            description=one_off_spend["description"],
            raw_category=None,
            envelope_id=one_off_spend["envelope_id"],
        )
        scenario_transactions.append(synthetic_tx)


    classify_transactions(
        scenario_transactions,
        scenario_envelopes,
        controller_config.classification_map,
    )

    raw_scenario_envelope_summaries = aggregate_envelopes(
        scenario_transactions,
        scenario_envelopes,
    )

    # Normalize scenario summaries to Dict[envelope_id, summary]
    scenario_envelope_summaries = None

    if isinstance(raw_scenario_envelope_summaries, dict):
        sample_value = next(iter(raw_scenario_envelope_summaries.values()), None)

        if isinstance(sample_value, list):
            # Multi-user shape: {user_id: [ ... ]}. Use the same active user.
            user_items = raw_scenario_envelope_summaries.get(
                user.user_id, sample_value
            )

            env_map: Dict[str, Any] = {}

            for item in user_items:
                env_id = None
                summary = None

                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    env_id, summary = item[0], item[1]
                elif hasattr(item, "envelope"):
                    env_obj = item.envelope
                    env_id = getattr(env_obj, "id", None) or getattr(
                        env_obj, "envelope_id", None
                    )
                    summary = item
                elif isinstance(item, dict):
                    env_id = item.get("envelope_id") or item.get("id")
                    summary = item

                if env_id is None or summary is None:
                    raise TypeError(
                        f"Unexpected scenario envelope summary element type: {type(item)}"
                    )

                env_map[str(env_id)] = summary

            scenario_envelope_summaries = env_map
        else:
            # Already envelope_id -> summary
            scenario_envelope_summaries = raw_scenario_envelope_summaries
    else:
        raise TypeError(
            f"Unexpected aggregate_envelopes result type in scenario: "
            f"{type(raw_scenario_envelope_summaries)}"
        )

    scenario_remaining: Dict[str, str] = {}
    for env_id, summary in scenario_envelope_summaries.items():
        remaining = None
        if hasattr(summary, "remaining_budget"):
            remaining = summary.remaining_budget
        elif isinstance(summary, dict) and "remaining_budget" in summary:
            remaining = summary["remaining_budget"]
        if remaining is not None:
            scenario_remaining[str(env_id)] = str(remaining)


    # If, for some reason, the scenario aggregation still didn't
    # produce an entry for the scenario envelope, compute it manually
    # as (budget_amount - scenario spend).
    if one_off_spend:
        scenario_env_id = one_off_spend["envelope_id"]
        spend_amount = Decimal(one_off_spend["amount"])

        if scenario_env_id in controller_config.envelopes:
            env = controller_config.envelopes[scenario_env_id]
            # If aggregator already gave us a value, keep it.
            # Otherwise, assume baseline spend was 0 and subtract the one-off spend.
            if scenario_env_id not in scenario_remaining:
                scenario_remaining[scenario_env_id] = str(
                    env.budget_amount - spend_amount
                )


    impact_summary = _build_scenario_impact_summary(
        baseline_remaining, scenario_remaining
    )

    result: Dict[str, Any] = {
        "baseline_envelopes_remaining": baseline_remaining,
        "scenario_envelopes_remaining": scenario_remaining,
        "impact_summary": impact_summary,
    }

    return result


def tool_explain_log_entry_impl(
    log_dir: Path,
    date_str: str,
) -> Dict[str, Any]:
    """
    Implementation of the explain_log_entry tool.

    Reads a specific ControllerLogEntry by date and returns a simplified summary
    of rule evaluations and recommendations that an LLM can then turn into a
    narrative explanation.
    """
    target_date = _parse_date(date_str)
    log_path = log_dir / "controller_log.jsonl"

    if not log_path.exists():
        raise FileNotFoundError(
            f"Controller log not found at {log_path}. "
            f"Cannot explain entry for {date_str}."
        )

    import json

    selected_entry: Optional[Dict[str, Any]] = None
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)

            date_str = entry.get("date")
            if not date_str:
                # Skip older Phase-2 style log entries that don't use 'date'
                continue

            entry_date = _parse_date(date_str)
            if entry_date == target_date:
                selected_entry = entry
                break


    if selected_entry is None:
        raise ValueError(f"No controller log entry found for date {date_str}.")

    rule_evaluations = selected_entry.get("rule_evaluations", [])
    recommendations = selected_entry.get("recommendations", [])

    rule_summary_parts: List[str] = []
    for ev in rule_evaluations:
        rule_summary_parts.append(
            f"[{ev.get('severity', '').upper()}:{ev.get('status', '').upper()}] "
            f"{ev.get('message', '')}"
        )
    rule_summary = (
        " ".join(rule_summary_parts)
        if rule_summary_parts
        else "No rule evaluations recorded."
    )

    recommendation_summary_parts: List[str] = []
    for rec in recommendations:
        recommendation_summary_parts.append(
            f"[Priority {rec.get('priority')}] "
            f"{rec.get('action_type')}: {rec.get('description')}"
        )
    recommendation_summary = (
        " ".join(recommendation_summary_parts)
        if recommendation_summary_parts
        else "No recommendations recorded."
    )

    narrative_explanation = (
        "This log entry captures the financial controller's view for the day. "
        "Rule evaluations indicate which constraints were satisfied or violated, "
        "and recommendations describe the concrete actions that could be taken "
        "to improve financial positioning for that date."
    )

    result: Dict[str, Any] = {
        "date": target_date.isoformat(),
        "rule_summary": rule_summary,
        "recommendation_summary": recommendation_summary,
        "narrative_explanation": narrative_explanation,
    }

    return result