from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, List

from controller.models import (
    User,
    Account,
    RuleEvaluation,
    Recommendation,
    DailyDigest,
)
from controller.classification import EnvelopeSummary


def _format_decimal(value: Decimal) -> str:
    return f"{value:.2f}"


def _build_accounts_summary(accounts: Dict[str, Account]) -> List[dict]:
    summary: List[dict] = []
    for acc in accounts.values():
        summary.append(
            {
                "account_id": acc.account_id,
                "name": acc.name,
                "balance": acc.current_balance,
                "currency": acc.currency,
            }
        )
    # Stable ordering by account_id
    summary.sort(key=lambda x: x["account_id"])
    return summary


def _build_envelopes_usage(
    envelope_summaries: Dict[str, EnvelopeSummary],
) -> List[dict]:
    usage: List[dict] = []
    for env_id, summary in envelope_summaries.items():
        envelope = summary.envelope
        spent = summary.total_spend
        remaining = envelope.budget_amount - spent

        usage.append(
            {
                "envelope_id": env_id,
                "name": envelope.name,
                "spent": spent,
                "remaining": remaining,
                "budget_amount": envelope.budget_amount,
                "currency": envelope.budget_currency,
            }
        )

    # Stable ordering by envelope_id
    usage.sort(key=lambda x: x["envelope_id"])
    return usage


def _build_rule_eval_records(
    rule_evaluations: List[RuleEvaluation],
) -> List[dict]:
    records: List[dict] = []
    for ev in rule_evaluations:
        records.append(
            {
                "rule_id": ev.rule_id,
                "status": ev.status,
                "severity": ev.severity,
                "message": ev.message,
                "measured_value": ev.measured_value,
                "threshold_value": ev.threshold_value,
            }
        )
    return records


def _render_text_block(
    digest_date: date,
    accounts_summary: List[dict],
    envelopes_usage: List[dict],
    rule_evaluations: List[RuleEvaluation],
    recommendations: List[Recommendation],
) -> str:
    """
    Builds the human-readable digest text, matching your example:

    Daily digest for 2025-11-20
    ============================================================

    (No explicit 'User: ...' line here; the runner will prepend that.)
    """
    lines: List[str] = []

    # Header
    date_str = digest_date.isoformat()
    lines.append(f"Daily digest for {date_str}")
    lines.append("=" * 60)
    lines.append("")

    # Accounts overview
    lines.append("Accounts overview:")
    for acc in accounts_summary:
        balance_str = _format_decimal(acc["balance"])
        lines.append(
            f"  - {acc['name']} ({acc['account_id']}): "
            f"{balance_str} {acc['currency']}"
        )
    lines.append("")

    # Envelope usage
    lines.append("Envelope usage:")
    for env in envelopes_usage:
        spent_str = _format_decimal(env["spent"])
        remaining_str = _format_decimal(env["remaining"])
        lines.append(
            f"  - {env['name']} ({env['envelope_id']}): "
            f"spent {spent_str} {env['currency']}, "
            f"remaining {remaining_str} {env['currency']}"
        )
    lines.append("")

    # Rule evaluations
    lines.append("Rule evaluations:")
    for ev in rule_evaluations:
        status_label = ev.status.upper()
        lines.append(f"  - [{status_label}] {ev.message}")
    lines.append("")

    # Recommendations (optional section)
    if recommendations:
        lines.append("Recommendations:")
        for rec in recommendations:
            lines.append(f"  - {rec.title}: {rec.message}")
        lines.append("")

    return "\n".join(lines)


def build_daily_digest(
    *,
    user: User,
    accounts: Dict[str, Account],
    envelope_summaries: Dict[str, EnvelopeSummary],
    rule_evaluations: List[RuleEvaluation],
    recommendations: List[Recommendation],
    digest_date: date,
) -> DailyDigest:
    """
    Build a DailyDigest object for the given user and date.

    - Builds:
        - accounts_summary
        - envelopes_spend / envelopes_remaining (inside envelopes_usage)
    - Includes all rule evaluations and recommendations.
    - Creates a human-readable text block (without the explicit 'User: ...' line).
    """

    accounts_summary = _build_accounts_summary(accounts)
    envelopes_usage = _build_envelopes_usage(envelope_summaries)
    rule_eval_records = _build_rule_eval_records(rule_evaluations)

    text_block = _render_text_block(
        digest_date=digest_date,
        accounts_summary=accounts_summary,
        envelopes_usage=envelopes_usage,
        rule_evaluations=rule_evaluations,
        recommendations=recommendations,
    )

    digest = DailyDigest(
        id=f"digest_{user.user_id}_{digest_date.isoformat()}",
        user_id=user.user_id,
        date=digest_date,
        accounts_overview=accounts_summary,
        envelope_usage=envelopes_usage,
        rule_evaluations=rule_eval_records,
        obligations=[],          # can be populated later if you want
        recommendations=recommendations,
        logs=[],
        metadata={
            "text_block": text_block,
            "accounts_summary": accounts_summary,
            "envelopes_spend": [
                {
                    "envelope_id": e["envelope_id"],
                    "spent": e["spent"],
                    "currency": e["currency"],
                }
                for e in envelopes_usage
            ],
            "envelopes_remaining": [
                {
                    "envelope_id": e["envelope_id"],
                    "remaining": e["remaining"],
                    "currency": e["currency"],
                }
                for e in envelopes_usage
            ],
        },
    )

    return digest
