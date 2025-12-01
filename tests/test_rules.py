import unittest
from decimal import Decimal
from pathlib import Path

from controller.classification import classify_transactions, aggregate_envelopes
from controller.config_loader import load_controller_config
from controller.ingestion import load_transactions_csv
from controller.rules import evaluate_all_rules
from controller.models import RuleEvaluation

class TestRules(unittest.TestCase):
    """
    Tests for the minimal rules engine (Phase 1 behavior).
    """

    def setUp(self) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        self.config_dir = self.project_root / "config"
        self.data_dir = self.project_root / "data"

        self.controller_config = load_controller_config(self.config_dir)
        self.accounts = self.controller_config.accounts
        self.envelopes = self.controller_config.envelopes
        self.rules = self.controller_config.rules

    def test_rules_evaluate_without_errors(self) -> None:
        transactions_path = self.data_dir / "transactions.csv"
        transactions = load_transactions_csv(transactions_path)

        # classify and aggregate over all transactions
        classify_transactions(
            transactions,
            self.envelopes,
            self.controller_config.classification_map,
        )
        envelope_summaries = aggregate_envelopes(transactions, self.envelopes)

        evaluations = evaluate_all_rules(
            accounts=self.accounts,
            envelope_summaries=envelope_summaries,
            obligations=self.controller_config.obligations if hasattr(self.controller_config, "obligations") else {},
            rules=self.rules,
            as_of_date=None if not hasattr(self, "as_of_date") else getattr(self, "as_of_date"),
        )

        self.assertIsInstance(
            evaluations,
            list,
            msg="evaluate_all_rules should return a list of RuleEvaluation objects.",
        )
        for ev in evaluations:
            self.assertIsInstance(
                ev,
                RuleEvaluation,
                msg="Each item returned by evaluate_all_rules should be a RuleEvaluation.",
            )

    def test_account_minimum_balance_rule_structure(self) -> None:
        # ensure that account min balance rule produces Decimal typed measured/threshold
        transactions_path = self.data_dir / "transactions.csv"
        transactions = load_transactions_csv(transactions_path)

        classify_transactions(
            transactions,
            self.envelopes,
            self.controller_config.classification_map,
        )
        envelope_summaries = aggregate_envelopes(transactions, self.envelopes)

        evaluations = evaluate_all_rules(
            accounts=self.accounts,
            envelope_summaries=envelope_summaries,
            obligations=self.controller_config.obligations if hasattr(self.controller_config, "obligations") else {},
            rules=self.rules,
            as_of_date=None if not hasattr(self, "as_of_date") else getattr(self, "as_of_date"),
        )

        account_rules = [ev for ev in evaluations if "Minimum balance" in ev.message or "balance" in ev.message]
        self.assertGreaterEqual(
            len(account_rules),
            1,
            msg="Expected at least one account minimum balance rule evaluation.",
        )
        for ev in account_rules:
            self.assertIsInstance(ev.measured_value, Decimal)
            self.assertIsInstance(ev.threshold_value, Decimal)


if __name__ == "__main__":
    unittest.main()
