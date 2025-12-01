from __future__ import annotations

import argparse
from datetime import datetime, date
from pathlib import Path
from typing import List

from .classification import classify_transactions, aggregate_envelopes
from .config_loader import load_controller_config
from .ingestion import load_transactions_csv
from .rules import evaluate_all_rules


def _parse_date(date_str: str) -> date:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD.") from exc


def run_daily_evaluation(config_dir: Path, data_dir: Path, as_of_date: date) -> None:
    # Load all config once
    config = load_controller_config(config_dir)
    transactions: List[Transaction] = load_transactions_csv(data_dir / "transactions.csv")

    # Filter to only transactions on the evaluation date
    daily_transactions = [t for t in transactions if t.date == as_of_date]

    if not daily_transactions:
        print(f"No transactions found on {as_of_date}")
        return

    print(f"\nDAILY FINANCIAL EVALUATION – {as_of_date}")
    print("=" * 70)

    # Process each user
    for user_id, user in config.users.items():
        print(f"\nUser: {user.name} ({user_id})")
        print("-" * 50)

        # Gather user's accounts and envelopes
        user_accounts = {
            acc.account_id: acc
            for acc in config.accounts.values()
            if acc.user_id == user_id
        }
        user_envelopes = {
            env.envelope_id: env
            for env in config.envelopes.values()
            if env.user_id == user_id
        }

        # Filter transactions belonging to this user's accounts
        user_txns = [
            t for t in daily_transactions
            if t.account_id in user_accounts
        ]

        if not user_txns:
            print("  No transactions today.")
            continue

        # CLASSIFY: assign envelope_id based on description keywords
        classify_transactions(
            transactions=user_txns,
            envelopes=user_envelopes,                    # Fixed: was missing
            classification_map=config.classification_map
        )

        # AGGREGATE: compute spend per envelope
        summaries_by_user = aggregate_envelopes(user_txns, user_envelopes)
        user_summaries = summaries_by_user.get(user_id, [])

        # Flatten for rule engine (expects envelope_id → summary)
        flat_summaries = {
            s.envelope.envelope_id: s
            for s in user_summaries
        }

        # EVALUATE RULES
        rule_evaluations = evaluate_all_rules(
            accounts=user_accounts,
            envelope_summaries=flat_summaries,
            rules=config.rules
        )

        # PRINT ACCOUNTS
        print("\nAccounts:")
        for acc in user_accounts.values():
            print(f"  • {acc.name} ({acc.account_id}): {acc.current_balance:,.2f} {acc.currency}")

        # PRINT ENVELOPE SPENDING
        print("\nEnvelope Spending Today:")
        if not user_summaries:
            print("  No classified spending.")
        else:
            for summary in user_summaries:
                env = summary.envelope
                spent = summary.total_spend
                remaining = summary.remaining_budget
                pct_used = (spent / env.budget_amount * 100) if env.budget_amount > 0 else 0
                pct_used = min(pct_used, 999.9)  # Cap at 999.9% for overspending
                print(
                    f"  • {env.name} ({env.priority})\n"
                    f"    Spent: {spent:,.2f} / Budget: {env.budget_amount:,.2f} {env.budget_currency}\n"
                    f"    Remaining: {remaining:,.2f} ({pct_used:.1f}% used)"
                )

        # PRINT RULE VIOLATIONS
        print("\nRule Check:")
        if not rule_evaluations:
            print("  All rules passed")
        else:
            for ev in rule_evaluations:
                status_icon = "VIOLATION" if ev.status == "violation" else "WARNING" if ev.status == "warning" else "PASS"
                print(f"  [{status_icon}] {ev.message}")

        print("\n" + "—" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Financial Controller – Daily Evaluation (Phase 1)"
    )
    parser.add_argument("--config-dir", type=Path, default="config", help="Config directory (default: config)")
    parser.add_argument("--data-dir", type=Path, default="data", help="Data directory (default: data)")
    parser.add_argument(
        "--as-of-date",
        type=_parse_date,
        default=date.today(),
        help="Date to evaluate (YYYY-MM-DD, default: today)",
    )
    args = parser.parse_args()

    run_daily_evaluation(
        config_dir=args.config_dir.expanduser().resolve(),
        data_dir=args.data_dir.expanduser().resolve(),
        as_of_date=args.as_of_date,
    )


if __name__ == "__main__":
    main()