from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
from decimal import Decimal
from uuid import uuid4

from controller.models import (
    Account,
    RuleEvaluation,
    Recommendation,
)

import logging
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Recommendation Context (Phase 2)
# -----------------------------------------------------------------------------

@dataclass
class RecommendationContext:
    """
    Provides contextual information that can help generate better recommendations.

    For now:
        - accounts (Dict[str, Account]) is sufficient.
    """
    accounts: Dict[str, Account]


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------

def _priority_from_severity(severity: str) -> int:
    """
    Maps severity → numeric priority.
    Lower number = higher priority.
    """
    severity = severity.lower()

    if severity == "critical":
        return 1
    if severity == "warning":
        return 2
    if severity == "info":
        return 3

    return 4  # default lowest priority


def _map_rule_to_action(rule_eval: RuleEvaluation) -> str:
    """
    Maps rule types → recommendation actions.
    """
    rid = rule_eval.rule_id.lower()

    # Account minimum balance rule → transfer suggestion
    if "account_minimum_balance" in rid:
        return "transfer"

    # Envelope overspending → spending adjustment
    if "envelope_budget_limit" in rid:
        return "spend_adjustment"

    # Obligation violation → fund obligation immediately
    if "obligation_buffer_check" in rid and rule_eval.status == "violation":
        return "obligation_funding"

    # Obligation warning → monitor obligation
    if "obligation_buffer_check" in rid and rule_eval.status == "warning":
        return "monitor_obligation"

    # Default catch-all
    return "general_advice"


# -----------------------------------------------------------------------------
# Main Recommendation Generator
# -----------------------------------------------------------------------------

def generate_recommendations(
    rule_evaluations: List[RuleEvaluation],
    context: RecommendationContext,
) -> List[Recommendation]:
    """
    Takes rule evaluations and produces a sorted list of Recommendation objects.
    """

    logger.debug(
        "Generating recommendations from %d rule evaluations",
        len(rule_evaluations),
    )

    output: List[Recommendation] = []

    for r in rule_evaluations:
        if r.status == "pass":
            logger.debug(
                "Skipping rule '%s' with status 'pass' (no recommendation)",
                r.rule_id,
            )
            continue  # ignore successful rule checks

        action = _map_rule_to_action(r)
        priority = _priority_from_severity(r.severity)

        logger.debug(
            "Rule '%s' (status=%s, severity=%s) mapped to action '%s' with priority=%s",
            r.rule_id,
            r.status,
            r.severity,
            action,
            priority,
        )

        if r.status == "violation":
            title = f"Action required: {action.replace('_', ' ').title()}"
        elif r.status == "warning":
            title = f"Warning: {action.replace('_', ' ').title()}"
        else:
            title = action.replace("_", " ").title()

        rec = Recommendation(
            id=str(uuid4()),
            user_id="user_001",   # TODO: pass real user_id if multi-user
            rule_id=r.rule_id,
            obligation_id=None,
            title=title,
            message=r.message,
            severity=r.severity,
            category=action,
            account_id=None,
            envelope_id=None,
            metadata={
                "rule_id": r.rule_id,
                "status": r.status,
                "priority": priority,
                "measured_value": str(r.measured_value),
                "threshold_value": str(r.threshold_value),
            },
        )

        output.append(rec)

    logger.debug(
        "Generated %d recommendations", len(output)
    )

    # Sort final list by priority
    output.sort(key=lambda rec: rec.metadata["priority"])

    return output
