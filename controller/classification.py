from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from .models import Envelope, Transaction


@dataclass
class EnvelopeSummary:
    """
    Summarizes spending for a single user's envelope over a period.
    """
    user_id: str
    envelope: Envelope
    total_spend: Decimal
    remaining_budget: Decimal


def classify_transactions(
    transactions: List[Transaction],
    envelopes: Dict[str, Envelope],
    classification_map: Dict[str, str],
    user_id_map: Optional[Dict[str, str]] = None
) -> None:
    """
    Mutate transactions in place to assign envelope identifiers.

    If user_id_map is provided, only assign envelopes belonging to the transaction's user.
    Classification is based on a simple mapping from lowercase keyword to envelope_id.
    """
    for txn in transactions:
        description_lower = txn.description.lower()
        assigned_envelope_id = None
        for keyword, envelope_id in classification_map.items():
            if keyword in description_lower:
                # If user_id_map is provided, make sure envelope belongs to this user
                if user_id_map is None or user_id_map.get(envelope_id) == txn.account_id:
                    assigned_envelope_id = envelope_id
                    break
        txn.envelope_id = assigned_envelope_id


def aggregate_envelopes(
    transactions: List[Transaction],
    envelopes: Dict[str, Envelope]
) -> Dict[str, List["EnvelopeSummary"]]:  # user_id → list of summaries
    """
    Correctly calculate spending as POSITIVE amounts for outflows.
    Only debit transactions (amount < 0) count as envelope spending.
    Income, transfers, refunds (positive) do NOT reduce envelope budgets.
    """
    totals: Dict[str, Dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for txn in transactions:
        if txn.envelope_id is None:
            continue
        if txn.amount >= 0:  # ←←← THIS IS THE KEY FIX
            continue  # Income, salary, refunds, transfers → do NOT count as spending
        if txn.envelope_id not in envelopes:
            continue

        envelope = envelopes[txn.envelope_id]
        # Use ABSOLUTE value of negative transactions → spending is always positive
        spending = abs(txn.amount)
        totals[envelope.user_id][txn.envelope_id] += spending

    # Build summaries
    summaries: Dict[str, List[EnvelopeSummary]] = defaultdict(list)
    for envelope_id, envelope in envelopes.items():
        user_id = envelope.user_id
        total_spend = totals[user_id].get(envelope_id, Decimal("0"))
        remaining = envelope.budget_amount - total_spend

        summaries[user_id].append(EnvelopeSummary(
            user_id=user_id,
            envelope=envelope,
            total_spend=total_spend,
            remaining_budget=remaining if remaining >= 0 else Decimal("0")
        ))

    return summaries