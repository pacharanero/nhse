from __future__ import annotations

import datetime as dt
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

import nhse_nhsd_spending as nhsd


COLUMNS = {
    "department_family": "Department Family",
    "entity": "Entity",
    "transaction_date": "Invoice Date",
    "expense_type": "Consolidated Expense Type",
    "expense_area": "Expense area",
    "supplier": "Supplier",
    "purchase_invoice_number": "Purchase Invoice Number",
    "amount_gbp": "Invoice Value £",
    "description": "Description",
}

HEADER_ROW = ",".join(COLUMNS.values()) + "\r\n"


class NhsdSpendingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _csv(self, body_rows: list[str], *, preamble: list[str] | None = None, encoding: str = "utf-8-sig") -> Path:
        preamble = preamble or []
        text = "".join(f"{line}\r\n" for line in preamble) + HEADER_ROW + "".join(f"{row}\r\n" for row in body_rows)
        path = self.root / "fixture.csv"
        path.write_bytes(text.encode(encoding))
        return path

    def _source(self, path: Path, *, header_row: int = 1, encoding: str = "utf-8-sig", expected: dict | None = None) -> dict:
        return {
            "id": "fixture-nhsd",
            "title": "Fixture NHSD spend",
            "period": "2019-20",
            "publisher": "NHS Digital",
            "landing_page_url": "https://example.test/landing",
            "landing_page_archive_url": "https://example.test/landing/archive",
            "source_url": "https://example.test/source.csv",
            "archive_url": "https://example.test/source/archive.csv",
            "filename": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
            "rights_status": "test-only",
            "rights_basis": "test fixture",
            "rights_decision_date": dt.date(2026, 10, 25),
            "rights_note": "Fixture data",
            "rights_evidence_url": "https://example.test/rights",
            "rights_evidence_archive_url": "https://example.test/rights/archive",
            "referenced_licence_url": "https://example.test/licence",
            "referenced_licence_archive_url": "https://example.test/licence/archive",
            "csv": {"encoding": encoding, "header_row": header_row, "columns": dict(COLUMNS)},
            "expected": expected
            or {
                "rows": 2,
                "total_gbp": "140.26",
                "entity": "NHS Digital",
                "negative_rows": 1,
                "minimum_date": "2019-04-08",
                "maximum_date": "2019-05-01",
            },
        }

    def test_build_is_deterministic_and_queryable(self) -> None:
        path = self._csv(
            [
                "Department of Health and Social Care,NHS Digital,08/04/2019,Workpackages,Product Development,118 LTD,201903000713401,\" 384,453.99 \",Workpackages",
                "Department of Health and Social Care,NHS Digital,01/05/2019,Workpackages,Product Development,AIRE LOGIC LTD,INV0001,-384313.73,Workpackages",
            ]
        )
        source = self._source(path, expected={
            "rows": 2,
            "total_gbp": "140.26",
            "entity": "NHS Digital",
            "negative_rows": 1,
            "minimum_date": "2019-04-08",
            "maximum_date": "2019-05-01",
        })
        first = nhsd.build_release(path, source, self.root / "first")
        second = nhsd.build_release(path, source, self.root / "second")

        first_files = {item.name: item.read_bytes() for item in first.iterdir()}
        second_files = {item.name: item.read_bytes() for item in second.iterdir()}
        self.assertEqual(first_files, second_files)

        connection = duckdb.connect(":memory:")
        try:
            result = connection.execute(
                "SELECT count(*), sum(amount_gbp), min(transaction_date), max(transaction_date) FROM read_parquet(?)",
                [str(first / "nhsd-spend.parquet")],
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(result, (2, nhsd.Decimal("140.26"), dt.date(2019, 4, 8), dt.date(2019, 5, 1)))

        nhsd.validate_release(first, source, verify_against_source=True, source_file=path)

        validation = json.loads((first / "validation.json").read_text(encoding="utf-8"))
        self.assertEqual(validation["statistics"]["entity"], "NHS Digital")
        self.assertEqual(validation["statistics"]["negative_rows"], 1)

    def test_preamble_rows_and_swapped_column_order_are_handled_by_name(self) -> None:
        # The physical column order places "Expense area" before "Consolidated
        # Expense Type" (as the real 2021-22/2022-23 NHSD files do), while the
        # registry's columns mapping keeps its ordinary, unswapped canonical
        # meanings; the parser must still locate each field by header text.
        reordered_header = (
            "Department Family,Entity,Invoice Date,Expense area,Consolidated Expense Type,"
            "Supplier,Purchase Invoice Number,Invoice Value £,Description"
        )
        preamble = [
            "Supplier Invoices and Credit Notes greater than £25k Apr 21 to Mar 22,,,,,,,,",
            "(values exclude recoverable VAT),,,,,,,,",
            ",,,,,,,,",
        ]
        body = "Department of Health and Social Care,NHS Digital,08/04/2019,Product Development,Workpackages,118 LTD,201903000713401,384453.99,Workpackages\r\n"
        text = "".join(f"{line}\r\n" for line in preamble) + reordered_header + "\r\n" + body
        path = self.root / "swapped.csv"
        path.write_bytes(text.encode("utf-8-sig"))

        source = self._source(
            path,
            header_row=4,
            expected={
                "rows": 1,
                "total_gbp": "384453.99",
                "entity": "NHS Digital",
                "negative_rows": 0,
                "minimum_date": "2019-04-08",
                "maximum_date": "2019-04-08",
            },
        )
        records, stats = nhsd.parse_csv(path, source)
        self.assertEqual(stats["rows"], 1)
        self.assertEqual(records[0]["expense_area"], "Product Development")
        self.assertEqual(records[0]["expense_type"], "Workpackages")

    def test_unexpected_header_fails_closed(self) -> None:
        path = self.root / "bad-header.csv"
        path.write_bytes(b"Wrong Header,Entity,Invoice Date\r\ndata,NHS Digital,08/04/2019\r\n")
        source = self._source(path, header_row=1)
        with self.assertRaises(nhsd.NhsdDataError):
            nhsd.parse_csv(path, source)

    def test_multiple_entities_in_one_source_fails_closed(self) -> None:
        path = self._csv(
            [
                "Department of Health and Social Care,NHS Digital,08/04/2019,Workpackages,Product Development,118 LTD,201903000713401,100.00,Workpackages",
                "Department of Health and Social Care,HSCIC,01/05/2019,Workpackages,Product Development,AIRE LOGIC LTD,INV0001,100.00,Workpackages",
            ]
        )
        source = self._source(path)
        with self.assertRaises(nhsd.NhsdDataError):
            nhsd.parse_csv(path, source)

    def test_redacted_row_is_flagged(self) -> None:
        path = self._csv(
            [
                "Department of Health and Social Care,NHS Digital,08/04/2019,Workpackages,Product Development,REMOVED,201903000713401,100.00,Workpackages",
            ]
        )
        source = self._source(
            path,
            expected={
                "rows": 1,
                "total_gbp": "100.00",
                "entity": "NHS Digital",
                "negative_rows": 0,
                "minimum_date": "2019-04-08",
                "maximum_date": "2019-04-08",
            },
        )
        records, _ = nhsd.parse_csv(path, source)
        self.assertEqual(records[0]["redaction_status"], "source_removed")

    def test_cp1252_pound_sign_header_decodes(self) -> None:
        path = self.root / "cp1252.csv"
        text = HEADER_ROW + "Department of Health,HSCIC,17/12/2012,Computer Software,GPES,PHOENIX PARTNERSHIP (LEEDS) LTD,3652,\"32,144.87\",Computer Software\r\n"
        path.write_bytes(text.encode("cp1252"))
        source = self._source(
            path,
            encoding="cp1252",
            expected={
                "rows": 1,
                "total_gbp": "32144.87",
                "entity": "HSCIC",
                "negative_rows": 0,
                "minimum_date": "2012-12-17",
                "maximum_date": "2012-12-17",
            },
        )
        records, stats = nhsd.parse_csv(path, source)
        self.assertEqual(stats["entity"], "HSCIC")
        self.assertEqual(records[0]["supplier"], "PHOENIX PARTNERSHIP (LEEDS) LTD")

    def test_registry_loads_and_covers_ten_fiscal_years(self) -> None:
        registry = nhsd.load_registry()
        self.assertEqual(len(registry["sources"]), 10)
        periods = sorted(source["period"] for source in registry["sources"])
        self.assertEqual(
            periods,
            ["2013-14", "2014-15", "2015-16", "2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23"],
        )

    def test_build_nhsd_spend_summary_excludes_nhs_england_registry(self) -> None:
        target = self.root / "nhsd-spend-by-year.json"
        nhsd.build_nhsd_spend_summary(target)
        summary = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(len(summary["years"]), 10)
        self.assertIn("never be summed", summary["note"])
        self.assertEqual(summary["years"][0]["period"], "2013-14")
        self.assertEqual(summary["years"][0]["entity"], "HSCIC")


if __name__ == "__main__":
    unittest.main()
