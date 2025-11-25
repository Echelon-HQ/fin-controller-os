# controller/ingestion.py
from __future__ import annotations

import csv
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import List

from .models import Transaction


# REQUIRED: These columns MUST exist (case-insensitive)
REQUIRED_COLUMNS = {
    "date": ["date", "transaction date", "posting date", "value date", "transaction_date"],
    "amount": ["amount", "debit", "credit", "total", "amount (usd)", "transaction amount"],
    "description": ["description", "memo", "details", "payee", "narrative", "merchant", "details"],
}

# Optional but recommended
OPTIONAL_BUT_HELPFUL = {
    "transaction_id": ["transaction_id", "id", "reference", "transaction id", "ref"],
    "user_id": ["user_id", "user id", "owner", "customer"],
    "account_id": ["account_id", "account id", "account", "account number"],
    "currency": ["currency", "curr", "ccy", "currency code"],
}


def _find_column(header_row: List[str], candidates: List[str]) -> str | None:
    """Return actual column name if any candidate matches (case-insensitive)."""
    header_lower = [h.strip().lower() for h in header_row]
    for cand in candidates:
        if cand.lower() in header_lower:
            idx = header_lower.index(cand.lower())
            return header_row[idx]
    return None


def load_transactions_csv(path: Path) -> List[Transaction]:
    if not path.exists():
        raise FileNotFoundError(f"Transactions file not found: {path}")

    with path.open("r", encoding="utf-8-sig") as f:  # utf-8-sig handles BOM
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV file is empty or has no headers: {path}")

        headers = reader.fieldnames
        mapped = {}
        missing_required = []

        # === STRICT CHECK: Required columns ===
        for logical_name, candidates in REQUIRED_COLUMNS.items():
            col = _find_column(headers, candidates)
            if col is None:
                missing_required.append(logical_name)
            else:
                mapped[logical_name] = col

        if missing_required:
            raise ValueError(
                f"Missing required columns in {path.name}:\n"
                f"  → Could not find columns for: {', '.join(missing_required)}\n\n"
                f"  Detected headers: {headers}\n\n"
                f"  We look for these variations:\n"
                + "\n".join(
                    f"    • {logical}: {', '.join(candidates)}"
                    for logical, candidates in REQUIRED_COLUMNS.items()
                    if logical in missing_required
                )
            )

        # === Optional columns (with fallback) ===
        for logical_name, candidates in OPTIONAL_BUT_HELPFUL.items():
            col = _find_column(headers, candidates)
            mapped[logical_name] = col  # can be None

        transactions: List[Transaction] = []
        for row_num, row in enumerate(reader, start=2):  # start=2 → row 1 is header
            try:
                raw_date = row[mapped["date"]].strip()
                raw_amount = row[mapped["amount"]].strip().replace(",", "")
                description = row[mapped["description"]].strip()

                # Parse date (supports YYYY-MM-DD and DD/MM/YYYY)
                try:
                    txn_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
                except ValueError:
                    try:
                        txn_date = datetime.strptime(raw_date, "%d/%m/%Y").date()
                    except ValueError:
                        raise ValueError(f"Unsupported date format: '{raw_date}' (use YYYY-MM-DD or DD/MM/YYYY)")

                # Parse amount
                if raw_amount.startswith("(") and raw_amount.endswith(")"):
                    raw_amount = "-" + raw_amount[1:-1]
                amount = Decimal(raw_amount)

                txn_id = row.get(mapped.get("transaction_id", ""), f"txn_auto_{row_num}")
                user_id = row.get(mapped.get("user_id", ""), "unknown_user")
                account_id = row.get(mapped.get("account_id", ""), "unknown_account")
                currency = row.get(mapped.get("currency", ""), "USD").upper()

                transactions.append(Transaction(
                    id=str(txn_id).strip() or f"txn_{row_num}",
                    user_id=str(user_id).strip(),
                    account_id=str(account_id).strip(),
                    date=txn_date,
                    amount=amount,
                    currency=currency,
                    description=description or "No description",
                    raw_category=row.get("raw_category", "").strip() or None,
                ))
            except Exception as e:
                print(f"Warning: Skipping row {row_num} due to error: {e}")
                continue

    print(f"Successfully loaded {len(transactions)} transactions from '{path.name}'")
    return transactions