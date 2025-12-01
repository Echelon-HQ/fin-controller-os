from __future__ import annotations

import argparse
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict

from controller.classification import classify_transactions, aggregate_envelopes, EnvelopeSummary
from controller.config_loader import load_controller_config
from controller.ingestion import load_transactions_csv
from controller.rules import evaluate_all_rules
from controller.recommendations import RecommendationContext, generate_recommendations
from controller.digest import build_daily_digest
from controller.controller_log import append_log_entry, DEFAULT_LOG_PATH
from controller.models import Transaction, Account, Envelope, User  # adjust if some are unused


def _parse_date(date_str: str) -> date:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date format '{date_str}'. Expected YYYY-MM-DD."
        ) from exc


def run_daily_evaluation(config_dir: Path, data_dir: Path, as_of_date: date) -> None:
    # Load all config once (Phase 2: includes obligations)
    config = load_controller_config(config_dir)
    transactions: List[Transaction] = load_transactions_csv(
        data_dir / "transactions.csv"
    )

    # Filter to only transactions on the evaluation date
    daily_transactions = [t for t in transactions if t.date == as_of_date]

    if not daily_transactions:
        print(f"No transactions found on {as_of_date}")
        return

    # Process each user
    for user_id, user in config.users.items():
        # Gather user's accounts and envelopes
        user_accounts: Dict[str, Account] = {
            acc.account_id: acc
            for acc in config.accounts.values()
            if acc.user_id == user_id
        }
        user_envelopes: Dict[str, Envelope] = {
            env.envelope_id: env
            for env in config.envelopes.values()
            if env.user_id == user_id
        }
        user_obligations = {
            oid: obl for oid, obl in config.obligations.items()
            if obl.user_id == user_id
        }

        # Filter transactions belonging to this user's accounts
        user_txns: List[Transaction] = [
            t for t in daily_transactions
            if t.account_id in user_accounts
        ]

        if not user_txns:
            # Still helpful to say something for this user
            print(f"\nDaily digest for {as_of_date.isoformat()}")
            print("=" * 60)
            print(f"User: {user.name} ({user_id})")
            print("  No transactions today.")
            print(f"Controller log updated at: {DEFAULT_LOG_PATH.resolve()}")
            print("\n" + "—" * 70)
            continue

        # CLASSIFY: assign envelope_id based on description keywords
        classify_transactions(
            transactions=user_txns,
            envelopes=user_envelopes,
            classification_map=config.classification_map,
        )

        # AGGREGATE: compute spend per envelope (by user)
        summaries_by_user = aggregate_envelopes(user_txns, user_envelopes)
        user_summaries: List[EnvelopeSummary] = summaries_by_user.get(user_id, [])

        # Flatten for rule engine and digest (expects envelope_id → summary)
        flat_summaries = {
            s.envelope.envelope_id: s
            for s in user_summaries
        }

        # EVALUATE RULES (Phase 2: includes obligation buffer rules)
        rule_evaluations = evaluate_all_rules(
            accounts=user_accounts,
            envelope_summaries=flat_summaries,
            rules=config.rules,
            obligations=user_obligations,
            today=as_of_date,
        )

        # RECOMMENDATIONS
        rec_context = RecommendationContext(accounts=user_accounts)
        recommendations = generate_recommendations(
            rule_evaluations=rule_evaluations,
            context=rec_context,
        )

        # BUILD DAILY DIGEST (structured + human-readable text block)
        digest = build_daily_digest(
            user=user,
            accounts=user_accounts,
            envelope_summaries=flat_summaries,
            rule_evaluations=rule_evaluations,
            recommendations=recommendations,
            digest_date=as_of_date,
        )

        # CONTROLLER LOG (JSONL)
        append_log_entry(
            message=(
                f"Daily run completed for user {user.user_id} "
                f"on {as_of_date.isoformat()}"
            ),
            level="INFO",
            source="daily_run",
            run_id=f"run_{user.user_id}_{as_of_date.isoformat()}",
            user_id=user.user_id,
            context={
                "num_transactions": len(user_txns),
                "num_recommendations": len(recommendations),
                "num_rule_evaluations": len(rule_evaluations),
            },
        )

        # PRINT DIGEST – match example style
        # digest.metadata["text_block"] contains the core body produced by digest.py
        text_block = digest.metadata.get("text_block", "")
        lines = text_block.splitlines()

        print("")  # spacer between users

        if len(lines) >= 2:
            # First two lines are expected to be:
            #   "Daily digest for YYYY-MM-DD"
            #   "============================================================"
            print(lines[0])
            print(lines[1])
            print(f"User: {user.name} ({user_id})")
            # Print the rest of the text block as-is
            for line in lines[2:]:
                print(line)
        else:
            # Fallback if text_block structure ever changes
            print(f"Daily digest for {as_of_date.isoformat()}")
            print("=" * 60)
            print(f"User: {user.name} ({user_id})")
            if text_block:
                print(text_block)

        # Final log line
        print(f"Controller log updated at: {DEFAULT_LOG_PATH.resolve()}")
        print("\n" + "—" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Financial Controller – Daily Evaluation (Phase 2)"
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default="config",
        help="Config directory (default: config)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default="data",
        help="Data directory (default: data)",
    )
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
