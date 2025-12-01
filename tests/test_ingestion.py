### `tests/test_ingestion.py`

```python
import unittest
from pathlib import Path
from decimal import Decimal

from controller.ingestion import load_transactions_csv

class TestIngestion(unittest.TestCase):
    """
    Tests for the transaction ingestion pipeline.
    """

    def setUp(self) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        self.data_dir = self.project_root / "data"

    def test_load_transactions_csv_returns_transactions(self) -> None:
        transactions_path = self.data_dir / "transactions.csv"
        transactions = load_transactions_csv(transactions_path)

        self.assertGreaterEqual(
            len(transactions),
            1,
            msg="Expected at least one transaction in the synthetic CSV file.",
        )

        first = transactions[0]
        self.assertIsNotNone(first.id, "Transaction id should not be None.")
        self.assertIsInstance(
            first.amount,
            Decimal,
            msg="Transaction amount should be a Decimal instance.",
        )
        self.assertIsNotNone(first.date, "Transaction date should not be None.")


if __name__ == "__main__":
    unittest.main()
