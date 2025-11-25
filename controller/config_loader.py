from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List
from dataclasses import dataclass
from controller.models import User, Account, Envelope, RuleConfig, Obligation

@dataclass
class ControllerConfig:
    users: Dict[str, User]  # key: user_id
    accounts: Dict[str, Account]  # key: account_id
    envelopes: Dict[str, Envelope]  # key: envelope_id
    rules: Dict[str, RuleConfig]  # key: rule_id
    obligations: Dict[str, Obligation]  # key: obligation_id (Obligation.id) - New Phase 2
    classification_map: Dict[str, str]

def _load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_controller_config(config_dir: Path) -> ControllerConfig:
    # Load raw JSON files
    users_raw = _load_json(config_dir / "users.json")
    accounts_raw = _load_json(config_dir / "accounts.json")
    envelopes_raw = _load_json(config_dir / "envelopes.json")
    rules_raw = _load_json(config_dir / "rules.json")
    obligations_raw = _load_json(config_dir / "obligations.json")  # NEW phase 2
    classification_raw = _load_json(config_dir / "classification.json")

    # Build users dict
    users: Dict[str, User] = {}
    for u in users_raw:
        users[u["user_id"]] = User(
            user_id=u["user_id"],
            name=u["name"],
            accounts=u.get("accounts", []),
            envelopes=u.get("envelopes", []),
        )

    # Build accounts dict
    accounts: Dict[str, Account] = {}
    for acc in accounts_raw:
        accounts[acc["account_id"]] = Account(
            account_id=acc["account_id"],
            user_id=acc["user_id"],
            name=acc["name"],
            currency=acc["currency"],
            type=acc["type"],
            current_balance=Decimal(str(acc.get("current_balance", "0"))),
        )

    # Build envelopes dict
    envelopes: Dict[str, Envelope] = {}
    for env in envelopes_raw:
        envelopes[env["envelope_id"]] = Envelope(
            envelope_id=env["envelope_id"],
            user_id=env["user_id"],
            name=env["name"],
            period=env["period"],
            budget_amount=Decimal(str(env["budget_amount"])),
            budget_currency=env["budget_currency"],
            priority=env["priority"],
        )

        # Build rules dict (Phase-1 and Phase-2 compatible)
    rules: Dict[str, RuleConfig] = {}
    for r in rules_raw:
        # Name can be `name` (Phase 1) or `title` (your current JSON)
        rule_name = r.get("name") or r.get("title") or r["id"]

        # Build parameters:
        # 1) If explicit 'parameters' dict exists (Phase 1 style), use it.
        # 2) Otherwise, derive parameters from flattened fields based on type.
        if "parameters" in r and isinstance(r["parameters"], dict):
            parameters = r["parameters"]
        else:
            params: Dict[str, object] = {}
            rtype = r["type"]

            if rtype == "account_minimum_balance":
                # Your JSON:
                #   account_id, threshold_amount, currency
                params["account_id"] = r["account_id"]
                # map threshold_amount -> minimum_balance expected by rules.py
                params["minimum_balance"] = r.get("minimum_balance", r["threshold_amount"])
                if "currency" in r:
                    params["currency"] = r["currency"]

            elif rtype == "envelope_budget_limit":
                # Your JSON:
                #   envelope_id, budget_amount, currency
                params["envelope_id"] = r["envelope_id"]
                # We support either:
                #   - max_ratio (Phase 1 style), OR
                #   - budget_amount (your new style)
                if "max_ratio" in r:
                    params["max_ratio"] = r["max_ratio"]
                if "budget_amount" in r:
                    params["budget_amount"] = r["budget_amount"]
                if "currency" in r:
                    params["currency"] = r["currency"]

            elif rtype == "obligation_buffer_check":
                # Your JSON:
                #   lookahead_days, buffer_ratio
                if "lookahead_days" in r:
                    params["lookahead_days"] = r["lookahead_days"]
                if "buffer_ratio" in r:
                    params["buffer_ratio"] = r["buffer_ratio"]

            # Fallback: copy any other fields into parameters
            for k, v in r.items():
                if k not in {
                    "id",
                    "name",
                    "title",
                    "description",
                    "type",
                    "severity",
                    "user_id",
                    "parameters",
                }:
                    params.setdefault(k, v)

            parameters = params

        rules[r["id"]] = RuleConfig(
            id=r["id"],
            name=rule_name,
            type=r["type"],
            parameters=parameters,
            severity=r["severity"],
        )


    # Build obligations dict (NEW)
    obligations: Dict[str, Obligation] = {}
    for o in obligations_raw:
        obligations[o["id"]] = Obligation(
            id=o["id"],
            user_id=o["user_id"],
            type=o["type"],
            title=o.get("title", o["id"]),
            description=o.get("description"),
            account_id=o.get("account_id"),
            envelope_id=o.get("envelope_id"),
            rule_id=o.get("rule_id"),
            amount=Decimal(str(o["amount"])) if "amount" in o else None,
            currency=o.get("currency"),
            due_date=date.fromisoformat(o["due_date"]) if "due_date" in o else None,
            status=o.get("status", "pending"),
            metadata=o.get("metadata", {}),
        )

    # Build classification map
    classification_map: Dict[str, str] = {
        k.lower(): v for k, v in classification_raw.items()
    }

    return ControllerConfig(
        users=users,
        accounts=accounts,
        envelopes=envelopes,
        rules=rules,
        obligations=obligations,
        classification_map=classification_map,
    )