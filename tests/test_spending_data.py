from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import duckdb
import openpyxl

import nhse_spending


HEADERS = [
    "Department family",
    "Entity",
    "Date",
    "Expense Type for Report",
    "Expense Area for Report",
    "Supplier",
    "Transaction number",
    "AP Amount (£)",
    "VAT registration number",
]


class SpendingDataTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _workbook(self, headers: list[str] = HEADERS) -> Path:
        path = self.root / "fixture.xlsx"
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Payments"
        sheet.append(headers)
        sheet.append(["Department of Health", "NHS England", dt.date(2025, 9, 1), "Services", "Digital", "Supplier A", 1001, 10.254, "123456789"])
        sheet.append(["Department of Health", "NHS England", dt.date(2025, 9, 2), "Services", "Digital", "Removed", "1002", -2.25, None])
        sheet.append(["Department of Health", "North of England CSU", dt.date(2025, 9, 3), "Goods", "Operations", "Supplier B", "1003", 5, None])
        workbook.save(path)
        return path

    def _source(self, path: Path) -> dict:
        return {
            "id": "fixture",
            "title": "Fixture payments",
            "period": "2025-09",
            "publication_date": dt.date(2025, 10, 1),
            "publication_date_precision": "month",
            "publisher": "NHS England",
            "landing_page_url": "https://example.test/landing",
            "landing_page_archive_url": "https://example.test/landing/archive",
            "collection_url": "https://example.test/collection",
            "collection_archive_url": "https://example.test/collection/archive",
            "source_url": "https://example.test/source.xlsx",
            "archive_url": "https://example.test/source/archive.xlsx",
            "filename": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
            "rights_status": "test-only",
            "rights_basis": "test fixture",
            "rights_decision_date": dt.date(2025, 10, 1),
            "rights_note": "Fixture data",
            "rights_evidence_url": "https://example.test/rights",
            "rights_evidence_archive_url": "https://example.test/rights/archive",
            "referenced_licence_url": "https://example.test/licence",
            "referenced_licence_archive_url": "https://example.test/licence/archive",
            "workbook": {"sheet": "Payments", "amount_scale": 2, "columns": HEADERS},
            "expected": {
                "rows": 3,
                "total_gbp": "13.00",
                "nhs_england_rows": 2,
                "nhs_england_total_gbp": "8.00",
                "negative_rows": 1,
                "missing_vat_rows": 2,
            },
        }

    def test_build_is_deterministic_and_queryable(self) -> None:
        path = self._workbook()
        source = self._source(path)
        first = nhse_spending.build_release(path, source, self.root / "first")
        second = nhse_spending.build_release(path, source, self.root / "second")

        first_files = {item.name: item.read_bytes() for item in first.iterdir()}
        second_files = {item.name: item.read_bytes() for item in second.iterdir()}
        self.assertEqual(first_files, second_files)

        connection = duckdb.connect(":memory:")
        try:
            result = connection.execute(
                """
                SELECT count(*), sum(amount_gbp), min(source_row), max(source_row),
                       min(source_amount_raw),
                       max(source_amount_raw) FILTER (WHERE transaction_number = '1001')
                FROM read_parquet(?)
                """,
                [str(first / "payments.parquet")],
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(result, (3, nhse_spending.Decimal("13.00"), 2, 4, "-2.25", "10.254"))

        validation = json.loads((first / "validation.json").read_text(encoding="utf-8"))
        self.assertEqual(validation["statistics"]["entity_counts"]["NHS England"], 2)
        self.assertEqual(validation["statistics"]["entity_totals_gbp"]["NHS England"], "8.00")

    def test_schema_drift_fails_closed(self) -> None:
        wrong_headers = copy.copy(HEADERS)
        wrong_headers[7] = "Amount"
        path = self._workbook(wrong_headers)
        source = self._source(path)
        with self.assertRaisesRegex(nhse_spending.SpendingDataError, "unexpected workbook headers"):
            nhse_spending.build_release(path, source, self.root / "release")

    def test_top_level_finances_reconcile(self) -> None:
        nhse_spending.validate_top_level_finances()


if __name__ == "__main__":
    unittest.main()
