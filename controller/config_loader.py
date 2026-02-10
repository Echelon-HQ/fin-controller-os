from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List
from dataclasses import dataclass
from controller.models import User, Account, Envelope, RuleConfig, Obligation

# --- DOCKER-FRIENDLY PATH LOGIC ---
# If running in Docker (APP_HOME is set), use /app. Otherwise, use relative path.
if os.getenv("APP_HOME"):
    BASE_DIR = Path(os.getenv("APP_HOME"))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

# Define the global CONFIG_DIR based on the environment
DEFAULT_CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
# ----------------------------------

@dataclass
class ControllerConfig:
    users: Dict[str, User]
    accounts: Dict[str, Account]
    envelopes: Dict[str, Envelope]
    rules: Dict[str, RuleConfig]
    obligations: Dict[str, Obligation]
    classification_map: Dict[str, str]

def _load_json(path: Path):
    if not path.exists():
        return [] # Return empty list/dict if file missing to prevent crash
        # Alternatively: raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_controller_config(config_dir: Path = None) -> ControllerConfig:
    """
    Load configuration. Defaults to the Docker-aware DEFAULT_CONFIG_DIR if not provided.
    """
    if config_dir is None:
        config_dir = DEFAULT_CONFIG_DIR

    # Load raw JSON files
    users_raw = _load_json(config_dir / "users.json") or []
    accounts_raw = _load_json(config_dir / "accounts.json") or []
    envelopes_raw = _load_json(config_dir / "envelopes.json") or []
    rules_raw = _load_json(config_dir / "rules.json") or []
    obligations_raw = _load_json(config_dir / "obligations.json") or []
    classification_raw = _load_json(config_dir / "classification.json") or {}

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
        rule_name = r.get("name") or r.get("title") or r["id"]

        if "parameters" in r and isinstance(r["parameters"], dict):
            parameters = r["parameters"]
        else:
            params: Dict[str, object] = {}
            rtype = r["type"]

            if rtype == "account_minimum_balance":
                params["account_id"] = r["account_id"]
                params["minimum_balance"] = r.get("minimum_balance", r["threshold_amount"])
                if "currency" in r:
                    params["currency"] = r["currency"]

            elif rtype == "envelope_budget_limit":
                params["envelope_id"] = r["envelope_id"]
                if "max_ratio" in r:
                    params["max_ratio"] = r["max_ratio"]
                if "budget_amount" in r:
                    params["budget_amount"] = r["budget_amount"]
                if "currency" in r:
                    params["currency"] = r["currency"]

            elif rtype == "obligation_buffer_check":
                if "lookahead_days" in r:
                    params["lookahead_days"] = r["lookahead_days"]
                if "buffer_ratio" in r:
                    params["buffer_ratio"] = r["buffer_ratio"]

            for k, v in r.items():
                if k not in { "id", "name", "title", "description", "type", "severity", "user_id", "parameters" }:
                    params.setdefault(k, v)

            parameters = params

        rules[r["id"]] = RuleConfig(
            id=r["id"],
            name=rule_name,
            type=r["type"],
            parameters=parameters,
            severity=r["severity"],
        )

    # Build obligations dict
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
