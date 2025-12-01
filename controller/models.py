from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

@dataclass
class User:
    user_id: str
    name: str
    accounts: List[str]  # list of account_ids
    envelopes: List[str]  # list of envelope_ids

@dataclass
class Account:
    user_id: str
    account_id: str
    name: str
    currency: str
    type: str
    current_balance: Decimal

@dataclass
class Transaction:
    id: str
    account_id: str
    user_id: str  # NEW
    date: date
    amount: Decimal
    currency: str
    description: str
    raw_category: str = None
    envelope_id: str = None

@dataclass
class Envelope:
    user_id: str
    envelope_id: str
    name: str
    period: str
    budget_amount: Decimal
    budget_currency: str
    priority: str

@dataclass
class RuleConfig:
    id: str
    name: str
    type: str
    parameters: Dict[str, str]
    severity: str

@dataclass
class RuleEvaluation:
    rule_id: str
    status: str
    measured_value: Decimal
    threshold_value: Decimal
    message: str
    severity: str

# ---------------------------------------------------------------------------
# Phase 2 Models
# ---------------------------------------------------------------------------

@dataclass
class Obligation:
    """
    Represents something the controller expects to be true or satisfied
    for the user, usually derived from a rule.

    Examples:
      - "Personal Checking must keep a minimum balance of 2,000 USD."
      - "Rent envelope must be fully funded by the 1st of each month."
    """
    id: str
    user_id: str

    # High-level categorization, e.g. "min_balance", "envelope_budget",
    # "savings_target", "debt_payment", etc.
    type: str

    title: str
    description: Optional[str] = None

    # Optional linkage back to specific entities.
    account_id: Optional[str] = None
    envelope_id: Optional[str] = None
    rule_id: Optional[str] = None

    amount: Optional[float] = None
    currency: Optional[str] = None

    # When this obligation should be satisfied by (if applicable).
    due_date: Optional[date] = None

    # "pending"   -> not yet evaluated or still in force
    # "satisfied" -> condition met
    # "violated"  -> condition missed / breached
    # "dismissed" -> no longer relevant
    status: str = "pending"

    # Free-form additional data (e.g. thresholds, original rule params, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Recommendation:
    """
    Human-readable suggestion produced by the controller based on rules,
    obligations, or detected patterns in the data.

    Examples:
      - "Move 500 USD from Personal Checking to Savings to meet your goal."
      - "You are trending over budget in Discretionary by 20%."
    """
    id: str
    user_id: str

    # Optional linkage back to what triggered the recommendation.
    rule_id: Optional[str] = None
    obligation_id: Optional[str] = None

    # Short label and detailed explanation.
    title: str = ""
    message: str = ""

    # e.g. "info", "warning", "critical"
    severity: str = "info"

    # e.g. "cash_flow", "budget", "risk", "goal_tracking"
    category: Optional[str] = None

    # Optional pointers to related entities.
    account_id: Optional[str] = None
    envelope_id: Optional[str] = None

    # Extra structured data for UI or later processing.
    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ControllerLogEntry:
    """
    Internal log entry for a single controller run or evaluation step.
    This is NOT a user-facing message; it’s for debugging / traceability.

    Example:
      - "Evaluated rule 'min_balance_personal' -> PASS"
      - "Classified transaction tx_123 into envelope 'transport'"
    """
    id: str

    # For grouping logs to a specific daily run / process.
    run_id: Optional[str] = None
    user_id: Optional[str] = None

    timestamp: datetime = field(default_factory=datetime.utcnow)

    # e.g. "DEBUG", "INFO", "WARNING", "ERROR"
    level: str = "INFO"

    # e.g. "ingestion", "classification", "rules", "daily_digest"
    source: str = "controller"

    message: str = ""

    # Arbitrary context data (rule IDs, transaction IDs, etc.)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DailyDigest:
    """
    High-level summary object for a given user and date. This is the
    structured representation of the “Daily digest for YYYY-MM-DD” output.

    It is intentionally flexible: each section can store whatever
    structured data the daily runner wants to keep (accounts, envelopes,
    rule results, etc.).
    """
    id: str
    user_id: str
    date: date

    # Raw sections used to build the human-readable digest.
    # These are kept generic so they can wrap existing Phase 1 types
    # (accounts, envelopes, rule results) without tightly coupling.
    accounts_overview: List[Dict[str, Any]] = field(default_factory=list)
    envelope_usage: List[Dict[str, Any]] = field(default_factory=list)
    rule_evaluations: List[Dict[str, Any]] = field(default_factory=list)

    # Phase 2 additions.
    obligations: List[Obligation] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)

    # Internal controller logs associated with this digest/run.
    logs: List[ControllerLogEntry] = field(default_factory=list)

    generated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)