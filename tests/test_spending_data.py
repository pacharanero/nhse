from __future__ import annotations

import copy
import datetime as dt
import hashlib
import io
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

import duckdb
import openpyxl

import nhse_spending
import nhse_spending_inventory


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

HEADERS_V2 = [
    "Department family",
    "Entity",
    "Date",
    "Expense Type",
    "Expense Area",
    "Supplier",
    "Transaction number",
    "AP Amount (£)",
    "VAT registration number",
    "Purchase invoice number",
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
            "normalization_schema_version": 1,
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

    def test_multi_workbook_release_includes_revision_diff(self) -> None:
        def workbook(name: str, date: dt.date, transaction: str, vat: str | None) -> Path:
            path = self.root / name
            document = openpyxl.Workbook()
            sheet = document.active
            sheet.title = "Payments"
            sheet.append(HEADERS_V2)
            sheet.append(
                [
                    "Department of Health",
                    "NHS England",
                    date,
                    "Services",
                    "Digital",
                    "Supplier A",
                    transaction,
                    10,
                    vat,
                    f"INV-{transaction}",
                ]
            )
            document.save(path)
            return path

        june = workbook("june.xlsx", dt.date(2024, 6, 30), "1001", "123")
        original = workbook("july-original.xlsx", dt.date(2024, 6, 30), "1001", None)
        corrected = workbook("july-corrected.xlsx", dt.date(2024, 7, 31), "1002", "456")

        def entry(identifier: str, period: str, path: Path) -> dict:
            return {
                "id": identifier,
                "title": identifier,
                "period": period,
                "publication_date": dt.date(2024, 8, 1),
                "publication_date_precision": "day",
                "source_url": f"https://example.test/{path.name}",
                "archive_url": f"https://example.test/archive/{path.name}",
                "filename": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
                "workbook": {"sheet": "Payments", "amount_scale": 2, "columns": HEADERS_V2},
                "expected": {
                    "rows": 1,
                    "total_gbp": "10.00",
                    "nhs_england_rows": 1,
                    "nhs_england_total_gbp": "10.00",
                    "negative_rows": 0,
                    "missing_vat_rows": 1 if path == original else 0,
                },
            }

        source = {
            "id": "2024-fixture",
            "title": "2024 fixture",
            "normalization_schema_version": 2,
            "period": "2024",
            "publication_date": dt.date(2024, 8, 1),
            "publication_date_precision": "day",
            "publisher": "NHS England",
            "landing_page_url": "https://example.test/landing",
            "landing_page_archive_url": "https://example.test/landing/archive",
            "collection_url": "https://example.test/collection",
            "collection_archive_url": "https://example.test/collection/archive",
            "rights_status": "test-only",
            "rights_basis": "test fixture",
            "rights_decision_date": dt.date(2024, 8, 1),
            "rights_note": "Fixture data",
            "rights_evidence_url": "https://example.test/rights",
            "rights_evidence_archive_url": "https://example.test/rights/archive",
            "referenced_licence_url": "https://example.test/licence",
            "referenced_licence_archive_url": "https://example.test/licence/archive",
            "expected": {
                "rows": 2,
                "total_gbp": "20.00",
                "nhs_england_rows": 2,
                "nhs_england_total_gbp": "20.00",
                "negative_rows": 0,
                "missing_vat_rows": 0,
            },
            "workbooks": [
                entry("2024-06-fixture", "2024-06", june),
                entry("2024-07-fixture-corrected", "2024-07", corrected),
            ],
            "revisions": [entry("2024-07-fixture-original", "2024-07", original)],
            "revision_diff": {
                "id": "2024-07-correction",
                "original_source_id": "2024-07-fixture-original",
                "corrected_source_id": "2024-07-fixture-corrected",
                "baseline_source_id": "2024-06-fixture",
            },
        }

        with mock.patch.object(nhse_spending, "SOURCE_DIR", self.root):
            release = nhse_spending.build_release([june, corrected], source, self.root / "annual")
            second_release = nhse_spending.build_release([june, corrected], source, self.root / "annual-second")

        first_files = {item.name: item.read_bytes() for item in release.iterdir()}
        second_files = {item.name: item.read_bytes() for item in second_release.iterdir()}
        self.assertEqual(first_files, second_files)

        revision = json.loads((release / "july-2024-correction.json").read_text(encoding="utf-8"))
        self.assertEqual(revision["comparison"]["removed_rows"], 1)
        self.assertEqual(revision["comparison"]["added_rows"], 1)
        self.assertTrue(revision["diagnosis"]["ordered_rows_equal_to_baseline_excluding_vat"])

        connection = duckdb.connect(":memory:")
        try:
            result = connection.execute(
                "SELECT source_period, purchase_invoice_number FROM read_parquet(?) ORDER BY source_period",
                [str(release / "payments.parquet")],
            ).fetchall()
        finally:
            connection.close()
        self.assertEqual(result, [("2024-06", "INV-1001"), ("2024-07", "INV-1002")])

    def test_revision_fingerprint_includes_parser_visible_amount(self) -> None:
        record = {
            "department_family": "Department of Health",
            "entity": "NHS England",
            "transaction_date": dt.date(2024, 7, 1),
            "expense_type": "Services",
            "expense_area": "Digital",
            "supplier": "Supplier A",
            "transaction_number": "1001",
            "purchase_invoice_number": "INV-1001",
            "amount_gbp": nhse_spending.Decimal("10.25"),
            "source_amount_raw": "10.254",
            "currency": "GBP",
            "vat_registration_number": "123",
            "redaction_status": "none",
        }
        changed = {**record, "source_amount_raw": "10.253"}
        self.assertNotEqual(nhse_spending._semantic_row(record), nhse_spending._semantic_row(changed))

    def test_committed_releases_validate(self) -> None:
        for source_id in ("2024-payments-over-25000", "2025-09-payments-over-25000"):
            source = nhse_spending.load_source(source_id)
            nhse_spending.validate_release(nhse_spending.release_path(source), source)

    def test_top_level_finances_reconcile(self) -> None:
        nhse_spending.validate_top_level_finances()


class SpendingInventoryTest(unittest.TestCase):
    def test_filename_month_detection_handles_published_variants(self) -> None:
        self.assertEqual(nhse_spending_inventory._month_from_filename("25k-report-sept-2015-v2.xlsx"), 9)
        self.assertEqual(nhse_spending_inventory._month_from_filename("25k-spend-ocotober-2017.xlsx"), 10)
        self.assertIsNone(nhse_spending_inventory._month_from_filename("payments-greater-25k-report-Q4-1314.csv"))

    def test_column_profiles_ignore_physical_sheet_layout(self) -> None:
        headers = ["Entity", "Supplier", "AP Amount (£)"]
        first = {
            "format": "xlsx",
            "sheets": [
                {"name": "Payments", "header_row": 1, "headers": headers},
                {"name": "Sheet2", "header_row": None, "headers": []},
            ],
        }
        second = {
            "format": "xlsx",
            "sheets": [{"name": "Report", "header_row": 1, "headers": headers}],
        }

        self.assertNotEqual(
            nhse_spending_inventory._schema_projection(first),
            nhse_spending_inventory._schema_projection(second),
        )
        self.assertEqual(
            nhse_spending_inventory._column_projection(first),
            nhse_spending_inventory._column_projection(second),
        )

    def test_inventory_cache_is_url_specific_and_refreshable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = nhse_spending_inventory._cache_path(root, "https://example.test/a/report.xlsx")
            second = nhse_spending_inventory._cache_path(root, "https://example.test/b/report.xlsx")
            self.assertNotEqual(first, second)

            first.write_bytes(b"stale")
            with mock.patch.object(
                nhse_spending_inventory.urllib.request,
                "urlopen",
                return_value=io.BytesIO(b"fresh"),
            ):
                nhse_spending_inventory._download(
                    "https://example.test/a/report.xlsx",
                    first,
                    refresh=True,
                )
            self.assertEqual(first.read_bytes(), b"fresh")

    def test_committed_census_is_internally_consistent(self) -> None:
        path = Path(__file__).parent.parent / "spending" / "historical-schema-census.json"
        inventory = json.loads(path.read_text(encoding="utf-8"))
        schema_ids = {schema["id"] for schema in inventory["schemas"]}
        column_profile_ids = {profile["id"] for profile in inventory["column_profiles"]}
        source_urls = [file["source_url"] for file in inventory["files"]]

        self.assertEqual(inventory["file_count"], len(inventory["files"]))
        self.assertEqual(inventory["unique_source_count"], len(set(source_urls)))
        self.assertEqual(inventory["schema_count"], len(schema_ids))
        self.assertEqual(inventory["column_profile_count"], len(column_profile_ids))
        self.assertEqual(inventory["file_count"], 144)
        self.assertEqual(inventory["unique_source_count"], 143)
        self.assertEqual(inventory["schema_count"], 17)
        self.assertEqual(inventory["column_profile_count"], 6)
        self.assertTrue(all(file["schema_id"] in schema_ids for file in inventory["files"]))
        self.assertTrue(all(file["column_profile_id"] in column_profile_ids for file in inventory["files"]))

        schema_counts = Counter(file["schema_id"] for file in inventory["files"])
        for schema in inventory["schemas"]:
            self.assertEqual(schema["file_count"], schema_counts[schema["id"]])
            projection = nhse_spending_inventory._schema_projection(
                next(file["inspection"] for file in inventory["files"] if file["schema_id"] == schema["id"])
            )
            self.assertEqual(schema["projection"], projection)
            self.assertEqual(schema["sha256"], hashlib.sha256(nhse_spending_inventory._canonical_json(projection)).hexdigest())

        profile_counts = Counter(file["column_profile_id"] for file in inventory["files"])
        for profile in inventory["column_profiles"]:
            self.assertEqual(profile["file_count"], profile_counts[profile["id"]])
            projection = nhse_spending_inventory._column_projection(
                next(
                    file["inspection"]
                    for file in inventory["files"]
                    if file["column_profile_id"] == profile["id"]
                )
            )
            self.assertEqual(profile["projection"], projection)
            self.assertEqual(profile["sha256"], hashlib.sha256(nhse_spending_inventory._canonical_json(projection)).hexdigest())

        for collection in inventory["collections"]:
            linked = [inventory["files"][index] for index in collection["file_indexes"]]
            self.assertEqual(collection["file_count"], len(linked))
            self.assertTrue(all(file["collection_id"] == collection["id"] for file in linked))
            if collection["id"] != "2013-14":
                self.assertEqual(
                    set(collection["observed_months"]) | set(collection["missing_months"]),
                    set(range(1, 13)),
                )
                self.assertFalse(set(collection["observed_months"]) & set(collection["missing_months"]))

        duplicate_url = "https://www.england.nhs.uk/wp-content/uploads/2014/11/payments-greater-25k-report-Q4-1314.csv"
        duplicate_periods = {file["period"] for file in inventory["files"] if file["source_url"] == duplicate_url}
        self.assertEqual(duplicate_periods, {"2013-14"})


if __name__ == "__main__":
    unittest.main()
