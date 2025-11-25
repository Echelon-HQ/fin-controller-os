from __future__ import annotations

from decimal import Decimal
from datetime import date
from typing import Dict, List

from controller.models import Account, RuleConfig, RuleEvaluation, Obligation
from controller.classification import EnvelopeSummary
from collections import defaultdict


def evaluate_account_minimum_balance_rules(
    accounts: Dict[str, Account],
    rules: Dict[str, RuleConfig],
) -> List[RuleEvaluation]:
    evaluations: List[RuleEvaluation] = []
    for rule in rules.values():
        if rule.type != "account_minimum_balance":
            continue

        account_id = rule.parameters["account_id"]
        if account_id not in accounts:
            # Ignore rules for accounts not present in this context (user)
            continue

        minimum_balance = Decimal(str(rule.parameters["minimum_balance"]))
        account = accounts[account_id]
        current_balance = account.current_balance

        if current_balance < minimum_balance:
            status = "violation"
            message = (
                f"Account '{account.name}' balance {current_balance} "
                f"is below the minimum required {minimum_balance}."
            )
        else:
            status = "pass"
            message = (
                f"Account '{account.name}' balance {current_balance} "
                f"meets the minimum required {minimum_balance}."
            )

        evaluations.append(
            RuleEvaluation(
                rule_id=rule.id,
                status=status,
                measured_value=current_balance,
                threshold_value=minimum_balance,
                message=message,
                severity=rule.severity,
            )
        )
    return evaluations


def evaluate_envelope_budget_limit_rules(
    envelope_summaries: Dict[str, EnvelopeSummary],
    rules: Dict[str, RuleConfig],
) -> List[RuleEvaluation]:
    evaluations: List[RuleEvaluation] = []
    for rule in rules.values():
        if rule.type != "envelope_budget_limit":
            continue

        params = rule.parameters
        envelope_id = params["envelope_id"]
        if envelope_id not in envelope_summaries:
            # Ignore rules for envelopes not present in this context (user)
            continue

        summary = envelope_summaries[envelope_id]
        envelope = summary.envelope

        # Determine limit style:
        # - Phase 1: max_ratio only (limit = envelope.budget_amount * max_ratio)
        # - Phase 2: optional budget_amount override + optional max_ratio
        max_ratio_raw = params.get("max_ratio")
        budget_amount_raw = params.get("budget_amount")

        # Base budget for the rule
        if budget_amount_raw is not None:
            limit_budget = Decimal(str(budget_amount_raw))
        else:
            limit_budget = envelope.budget_amount

        # How much of that budget is allowed (ratio)
        if max_ratio_raw is not None:
            limit_ratio = Decimal(str(max_ratio_raw))
        else:
            limit_ratio = Decimal("1.0")  # default: can use full limit_budget

        spent = summary.total_spend

        if limit_budget == 0:
            status = "warning"
            ratio = Decimal("0")
            message = (
                f"Envelope '{envelope.name}' has a budget of zero. "
                f"Consider adjusting configuration."
            )
            threshold = Decimal("0")
        else:
            allowed_spend = limit_budget * limit_ratio
            ratio = spent / limit_budget

            if spent > allowed_spend:
                status = "violation"
                message = (
                    f"Envelope '{envelope.name}' has spent {spent:.2f} "
                    f"which exceeds the allowed {allowed_spend:.2f} "
                    f"(limit_budget={limit_budget:.2f}, limit_ratio={limit_ratio:.2f})."
                )
            else:
                status = "pass"
                message = (
                    f"Envelope '{envelope.name}' has spent {spent:.2f}, "
                    f"within the allowed {allowed_spend:.2f} "
                    f"(limit_budget={limit_budget:.2f}, limit_ratio={limit_ratio:.2f})."
                )
            threshold = limit_ratio  # we still record ratio as the threshold

        evaluations.append(
            RuleEvaluation(
                rule_id=rule.id,
                status=status,
                measured_value=ratio,
                threshold_value=threshold,
                message=message,
                severity=rule.severity,
            )
        )
    return evaluations



def evaluate_obligation_buffer_rules(
    obligations: Dict[str, Obligation],
    rules: Dict[str, RuleConfig],
    today: date,
) -> List[RuleEvaluation]:
    """
    Evaluate rules of type 'obligation_buffer_check' using a time buffer window.

    RuleConfig.parameters:
        - lookahead_days: int (default: 7)
        - buffer_ratio: float/decimal in [0, 1] (default: 0.2)

    Obligation expectations:
        - due_date: date (if None, we skip time-based evaluation)
        - status: 'pending' | 'satisfied' | 'violated' | 'dismissed' (etc.)
        - metadata.get("progress_ratio"): 0.0–1.0 (optional, default 0.0)

    Logic:
        - If obligation is 'satisfied' or 'dismissed' -> ignored.
        - If due_date < today and not satisfied -> status 'violation'.
        - If 0 <= days_until_due <= lookahead_days AND
              progress_ratio < (1 - buffer_ratio)
          -> status 'warning'.
        - Otherwise -> status 'pass'.
    """
    evaluations: List[RuleEvaluation] = []

    for rule in rules.values():
        if rule.type != "obligation_buffer_check":
            continue

        params = rule.parameters
        lookahead_days = int(params.get("lookahead_days", 7))
        buffer_ratio_raw = params.get("buffer_ratio", "0.2")
        buffer_ratio = Decimal(str(buffer_ratio_raw))

        required_progress = Decimal("1") - buffer_ratio

        for obl in obligations.values():
            # Skip resolved obligations
            if obl.status in ("satisfied", "dismissed"):
                continue

            # Must have a due date for buffer logic
            if obl.due_date is None:
                continue

            days_until_due = (obl.due_date - today).days

            progress_raw = obl.metadata.get("progress_ratio", 0.0)
            try:
                progress_ratio = Decimal(str(progress_raw))
            except Exception:
                progress_ratio = Decimal("0")

            if days_until_due < 0:
                status = "violation"
                message = (
                    f"Obligation '{obl.title}' is past due "
                    f"(due {obl.due_date.isoformat()}) and not satisfied."
                )
            elif 0 <= days_until_due <= lookahead_days and progress_ratio < required_progress:
                status = "warning"
                message = (
                    f"Obligation '{obl.title}' is due in {days_until_due} day(s) "
                    f"with progress ratio {progress_ratio:.2f}, below required "
                    f"{required_progress:.2f}."
                )
            else:
                status = "pass"
                message = (
                    f"Obligation '{obl.title}' is not at risk within the next "
                    f"{lookahead_days} day(s)."
                )

            evaluations.append(
                RuleEvaluation(
                    rule_id=rule.id,
                    status=status,
                    measured_value=progress_ratio,
                    threshold_value=required_progress,
                    message=message,
                    severity=rule.severity,
                )
            )

    return evaluations


def evaluate_all_rules(
    accounts: Dict[str, Account],
    envelope_summaries: Dict[str, EnvelopeSummary],
    rules: Dict[str, RuleConfig],
    obligations: Dict[str, Obligation],
    today: date,
) -> List[RuleEvaluation]:
    """
    Evaluate all rules applicable to the given accounts, envelopes, and obligations.
    Rules for accounts/envelopes/obligations not present are ignored automatically.
    """
    evaluations: List[RuleEvaluation] = []
    evaluations.extend(evaluate_account_minimum_balance_rules(accounts, rules))
    evaluations.extend(evaluate_envelope_budget_limit_rules(envelope_summaries, rules))
    evaluations.extend(evaluate_obligation_buffer_rules(obligations, rules, today))
    return evaluations
