#!/usr/bin/env python3
"""Fetch, normalize, and validate NHS England spending datasets."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import urllib.request
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import duckdb
import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


ROOT = Path(__file__).resolve().parent
SOURCE_REGISTRY = ROOT / "spending" / "data-sources.yaml"
FINANCE_REGISTRY = ROOT / "spending" / "top-level-finances.yaml"
SOURCE_DIR = ROOT / "spending" / "sources"
DATA_DIR = ROOT / "spending" / "data"
TOOL_VERSION = "0.1.0"
PARQUET_ROW_GROUP_SIZE = 64_000

OUTPUT_COLUMNS = [
    "observation_id",
    "department_family",
    "entity",
    "transaction_date",
    "expense_type",
    "expense_area",
    "supplier",
    "transaction_number",
    "amount_gbp",
    "source_amount_raw",
    "currency",
    "vat_registration_number",
    "redaction_status",
    "source_sha256",
    "source_file",
    "source_sheet",
    "source_row",
]


class SpendingDataError(RuntimeError):
    """A source, schema, or reconciliation invariant failed."""


def _jsonable(value: Any) -> Any:
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(_jsonable(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(_jsonable(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise SpendingDataError(f"{path} must contain a YAML mapping")
    return value


def load_source(source_id: str) -> dict[str, Any]:
    registry = _load_yaml(SOURCE_REGISTRY)
    if registry.get("schema_version") != 1:
        raise SpendingDataError("unsupported spending source-registry schema")
    sources = registry.get("sources")
    if not isinstance(sources, list):
        raise SpendingDataError("spending source registry must contain a sources list")
    matches = [source for source in sources if source.get("id") == source_id]
    if len(matches) != 1:
        raise SpendingDataError(f"expected exactly one source named {source_id!r}, found {len(matches)}")
    source = matches[0]
    required = {
        "archive_url",
        "bytes",
        "collection_archive_url",
        "collection_url",
        "filename",
        "id",
        "landing_page_archive_url",
        "landing_page_url",
        "period",
        "publication_date",
        "publication_date_precision",
        "publisher",
        "referenced_licence_archive_url",
        "referenced_licence_url",
        "rights_evidence_archive_url",
        "rights_evidence_url",
        "rights_basis",
        "rights_decision_date",
        "rights_note",
        "rights_status",
        "sha256",
        "source_url",
        "title",
        "workbook",
        "expected",
    }
    missing = required - source.keys()
    if missing:
        raise SpendingDataError(f"source {source_id!r} is missing {', '.join(sorted(missing))}")
    return source


def source_path(source: dict[str, Any]) -> Path:
    return SOURCE_DIR / str(source["filename"])


def release_path(source: dict[str, Any]) -> Path:
    return DATA_DIR / str(source["id"])


def verify_source_file(path: Path, source: dict[str, Any]) -> None:
    expected_bytes = int(source["bytes"])
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise SpendingDataError(f"{path} is {actual_bytes} bytes; expected {expected_bytes}")
    expected_hash = str(source["sha256"])
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise SpendingDataError(f"{path} has SHA-256 {actual_hash}; expected {expected_hash}")


def fetch_source(source: dict[str, Any], use_archive: bool = False) -> Path:
    target = source_path(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        verify_source_file(target, source)
        return target

    url_key = "archive_url" if use_archive else "source_url"
    url = str(source[url_key])
    request = urllib.request.Request(url, headers={"User-Agent": "nhse-research-data/0.1 (+https://github.com/pacharanero/nhse)"})
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{target.name}.", suffix=".part", dir=target.parent, delete=False) as output:
            temporary = Path(output.name)
            with urllib.request.urlopen(request, timeout=60) as response:
                shutil.copyfileobj(response, output, length=1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        verify_source_file(temporary, source)
        os.replace(temporary, target)
        return target
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def _required_text(value: Any, field: str, row_number: int) -> str:
    if not isinstance(value, str):
        raise SpendingDataError(f"row {row_number}: {field} must be non-empty text")
    text = value.strip()
    if not text:
        raise SpendingDataError(f"row {row_number}: {field} must be non-empty text")
    return text


def _identifier(value: Any, field: str, row_number: int, nullable: bool = False) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        if nullable:
            return None
        raise SpendingDataError(f"row {row_number}: {field} must be present")
    if isinstance(value, bool):
        raise SpendingDataError(f"row {row_number}: {field} cannot be boolean")
    if isinstance(value, float):
        if not value.is_integer():
            raise SpendingDataError(f"row {row_number}: {field} has a non-integral numeric identifier")
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def _date(value: Any, row_number: int) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    raise SpendingDataError(f"row {row_number}: Date must be an Excel date, found {type(value).__name__}")


def _money(value: Any, row_number: int, scale: int) -> tuple[Decimal, str]:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise SpendingDataError(f"row {row_number}: AP Amount (£) must be numeric")
    if scale != 2:
        raise SpendingDataError(f"row {row_number}: only two-decimal GBP sources are currently supported")
    try:
        source_amount = Decimal(str(value))
        amount = source_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as error:
        raise SpendingDataError(f"row {row_number}: AP Amount (£) is not finite") from error
    if not amount.is_finite():
        raise SpendingDataError(f"row {row_number}: AP Amount (£) is not finite")
    return amount, format(source_amount, "f")


def parse_workbook(path: Path, source: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    verify_source_file(path, source)
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=False)
    try:
        sheet_name = str(source["workbook"]["sheet"])
        if sheet_name not in workbook.sheetnames:
            raise SpendingDataError(f"workbook does not contain expected sheet {sheet_name!r}")
        sheet = workbook[sheet_name]
        expected_headers = list(source["workbook"]["columns"])
        amount_scale = int(source["workbook"]["amount_scale"])
        if sheet.max_column != len(expected_headers):
            raise SpendingDataError(f"sheet has {sheet.max_column} columns; expected {len(expected_headers)}")

        rows = sheet.iter_rows(min_row=1, max_col=len(expected_headers))
        header_cells = next(rows, None)
        if header_cells is None:
            raise SpendingDataError("workbook sheet is empty")
        actual_headers = [cell.value for cell in header_cells]
        if actual_headers != expected_headers:
            raise SpendingDataError(f"unexpected workbook headers: {actual_headers!r}")

        records: list[dict[str, Any]] = []
        for row_number, cells in enumerate(rows, start=2):
            values = [cell.value for cell in cells]
            if all(value is None or (isinstance(value, str) and not value.strip()) for value in values):
                continue
            formula_columns = [expected_headers[index] for index, cell in enumerate(cells) if cell.data_type == "f"]
            if formula_columns:
                raise SpendingDataError(f"row {row_number}: formulas are not allowed in {', '.join(formula_columns)}")
            error_columns = [expected_headers[index] for index, cell in enumerate(cells) if cell.data_type == "e"]
            if error_columns:
                raise SpendingDataError(f"row {row_number}: Excel errors are not allowed in {', '.join(error_columns)}")

            department_family = _required_text(values[0], "Department family", row_number)
            entity = _required_text(values[1], "Entity", row_number)
            transaction_date = _date(values[2], row_number)
            expense_type = _required_text(values[3], "Expense Type for Report", row_number)
            expense_area = _required_text(values[4], "Expense Area for Report", row_number)
            supplier = _required_text(values[5], "Supplier", row_number)
            transaction_number = _identifier(values[6], "Transaction number", row_number)
            amount, source_amount_raw = _money(values[7], row_number, amount_scale)
            vat_number = _identifier(values[8], "VAT registration number", row_number, nullable=True)
            source_values = {
                "department_family": department_family,
                "entity": entity,
                "transaction_date": transaction_date,
                "expense_type": expense_type,
                "expense_area": expense_area,
                "supplier": supplier,
                "transaction_number": transaction_number,
                "amount_gbp": amount,
                "source_amount_raw": source_amount_raw,
                "vat_registration_number": vat_number,
            }
            identity_input = {
                "schema_version": 1,
                "source_sha256": source["sha256"],
                "source_sheet": sheet_name,
                "source_row": row_number,
                "values": source_values,
            }
            redacted = any(isinstance(value, str) and value.strip().casefold() == "removed" for value in values)
            records.append(
                {
                    "observation_id": hashlib.sha256(_canonical_json(identity_input)).hexdigest(),
                    **source_values,
                    "currency": "GBP",
                    "redaction_status": "source_removed" if redacted else "none",
                    "source_sha256": str(source["sha256"]),
                    "source_file": str(source["filename"]),
                    "source_sheet": sheet_name,
                    "source_row": row_number,
                }
            )
    finally:
        workbook.close()

    records.sort(key=lambda row: (row["source_sha256"], row["source_sheet"], row["source_row"], row["observation_id"]))
    if len({row["observation_id"] for row in records}) != len(records):
        raise SpendingDataError("observation IDs are not unique")

    entity_counts = Counter(row["entity"] for row in records)
    entity_totals: Counter[str] = Counter()
    for row in records:
        entity_totals[row["entity"]] += row["amount_gbp"]
    stats = {
        "rows": len(records),
        "total_gbp": sum((row["amount_gbp"] for row in records), Decimal("0.00")),
        "nhs_england_rows": entity_counts["NHS England"],
        "nhs_england_total_gbp": entity_totals["NHS England"],
        "negative_rows": sum(row["amount_gbp"] < 0 for row in records),
        "missing_vat_rows": sum(row["vat_registration_number"] is None for row in records),
        "minimum_date": min(row["transaction_date"] for row in records),
        "maximum_date": max(row["transaction_date"] for row in records),
        "entity_counts": dict(sorted(entity_counts.items())),
        "entity_totals_gbp": dict(sorted(entity_totals.items())),
    }
    _validate_expected_stats(stats, source["expected"])
    return records, stats


def _validate_expected_stats(stats: dict[str, Any], expected: dict[str, Any]) -> None:
    decimal_fields = {"total_gbp", "nhs_england_total_gbp"}
    for field, expected_value in expected.items():
        actual_value = stats[field]
        if field in decimal_fields:
            expected_value = Decimal(str(expected_value))
        else:
            expected_value = int(expected_value)
        if actual_value != expected_value:
            raise SpendingDataError(f"{field} is {actual_value}; expected {expected_value}")


def _arrow_schema(provenance: dict[str, Any]) -> pa.Schema:
    fields = [
        pa.field("observation_id", pa.string(), nullable=False),
        pa.field("department_family", pa.string(), nullable=False),
        pa.field("entity", pa.string(), nullable=False),
        pa.field("transaction_date", pa.date32(), nullable=False),
        pa.field("expense_type", pa.string(), nullable=False),
        pa.field("expense_area", pa.string(), nullable=False),
        pa.field("supplier", pa.string(), nullable=False),
        pa.field("transaction_number", pa.string(), nullable=False),
        pa.field("amount_gbp", pa.decimal128(18, 2), nullable=False),
        pa.field("source_amount_raw", pa.string(), nullable=False),
        pa.field("currency", pa.string(), nullable=False),
        pa.field("vat_registration_number", pa.string(), nullable=True),
        pa.field("redaction_status", pa.string(), nullable=False),
        pa.field("source_sha256", pa.string(), nullable=False),
        pa.field("source_file", pa.string(), nullable=False),
        pa.field("source_sheet", pa.string(), nullable=False),
        pa.field("source_row", pa.int32(), nullable=False),
    ]
    return pa.schema(fields, metadata={b"nhse.provenance": _canonical_json(provenance)})


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("wb") as raw_output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, mtime=0, compresslevel=9) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text_output:
                writer = csv.DictWriter(text_output, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
                writer.writeheader()
                for record in records:
                    writer.writerow({column: _jsonable(record[column]) for column in OUTPUT_COLUMNS})


def _content_fingerprint(records: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(_canonical_json(record))
        digest.update(b"\n")
    return digest.hexdigest()


def _resource_schema() -> dict[str, Any]:
    types = {
        "observation_id": "string",
        "department_family": "string",
        "entity": "string",
        "transaction_date": "date",
        "expense_type": "string",
        "expense_area": "string",
        "supplier": "string",
        "transaction_number": "string",
        "amount_gbp": "number",
        "source_amount_raw": "string",
        "currency": "string",
        "vat_registration_number": "string",
        "redaction_status": "string",
        "source_sha256": "string",
        "source_file": "string",
        "source_sheet": "string",
        "source_row": "integer",
    }
    return {
        "fields": [
            {"name": column, "type": types[column], **({"decimalChar": "."} if column == "amount_gbp" else {})}
            for column in OUTPUT_COLUMNS
        ],
        "primaryKey": "observation_id",
    }


def _source_provenance(source: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _jsonable(source[key])
        for key in (
            "id",
            "title",
            "period",
            "publication_date",
            "publication_date_precision",
            "publisher",
            "landing_page_url",
            "landing_page_archive_url",
            "collection_url",
            "collection_archive_url",
            "source_url",
            "archive_url",
            "filename",
            "sha256",
            "bytes",
            "rights_status",
            "rights_basis",
            "rights_decision_date",
            "rights_note",
            "rights_evidence_url",
            "rights_evidence_archive_url",
            "referenced_licence_url",
            "referenced_licence_archive_url",
        )
    }


def build_release(path: Path, source: dict[str, Any], target: Path) -> Path:
    records, stats = parse_workbook(path, source)
    content_fingerprint = _content_fingerprint(records)
    provenance = {
        "dataset": "nhs-england-payments-over-25000",
        "dataset_version": f"{source['period']}.1",
        "schema_version": 1,
        "tool": "nhse-research-data",
        "tool_version": TOOL_VERSION,
        "source": _source_provenance(source),
        "normalized_content_sha256": content_fingerprint,
    }

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    backup = target.with_name(f".{target.name}.previous")
    try:
        parquet_path = temporary / "payments.parquet"
        csv_path = temporary / "payments.csv.gz"
        table = pa.Table.from_pylist(records, schema=_arrow_schema(provenance))
        pq.write_table(
            table,
            parquet_path,
            compression="zstd",
            compression_level=3,
            row_group_size=PARQUET_ROW_GROUP_SIZE,
            version="2.6",
            write_statistics=True,
        )
        _write_csv(csv_path, records)

        parquet_hash = sha256_file(parquet_path)
        csv_hash = sha256_file(csv_path)
        validation = {
            "dataset": "nhs-england-payments-over-25000",
            "dataset_version": f"{source['period']}.1",
            "schema_version": 1,
            "source_sha256": source["sha256"],
            "normalized_content_sha256": content_fingerprint,
            "artifacts": {
                "payments.csv.gz": {"bytes": csv_path.stat().st_size, "sha256": csv_hash},
                "payments.parquet": {"bytes": parquet_path.stat().st_size, "sha256": parquet_hash},
            },
            "statistics": _jsonable(stats),
            "status": "passed",
        }
        (temporary / "validation.json").write_bytes(_json_bytes(validation))

        descriptor = {
            "profile": "tabular-data-package",
            "name": f"nhs-england-payments-over-25000-{source['period']}",
            "title": source["title"],
            "version": f"{source['period']}.1",
            "description": "Normalized NHS England payments-over-£25,000 transparency data with physical workbook-row provenance.",
            "licenses": [
                {
                    "name": "OGL-UK-3.0",
                    "path": source["referenced_licence_url"],
                    "title": "Open Government Licence v3.0",
                }
            ],
            "rights": source["rights_note"],
            "rights_status": source["rights_status"],
            "sources": [_source_provenance(source)],
            "nhse": {
                "normalized_content_sha256": content_fingerprint,
                "schema_version": 1,
                "tool_version": TOOL_VERSION,
                "limitations": [
                    "This thresholded payments publication is not a general ledger and does not reconcile one-for-one to annual accrual accounts.",
                    "Supplier text is preserved as published and has not been entity-resolved.",
                    "Negative values are retained and not classified as refunds, reversals or corrections without source evidence.",
                    "The project-owner redistribution decision covers this normalized release, not a raw-workbook mirror.",
                ],
            },
            "resources": [
                {
                    "name": "payments-parquet",
                    "path": "payments.parquet",
                    "format": "parquet",
                    "mediatype": "application/vnd.apache.parquet",
                    "bytes": parquet_path.stat().st_size,
                    "hash": f"sha256:{parquet_hash}",
                    "schema": _resource_schema(),
                },
                {
                    "name": "payments-csv",
                    "path": "payments.csv.gz",
                    "format": "csv",
                    "mediatype": "text/csv",
                    "compression": "gzip",
                    "encoding": "utf-8",
                    "bytes": csv_path.stat().st_size,
                    "hash": f"sha256:{csv_hash}",
                    "schema": _resource_schema(),
                },
            ],
        }
        (temporary / "datapackage.json").write_bytes(_json_bytes(descriptor))

        checksummed = ["datapackage.json", "payments.csv.gz", "payments.parquet", "validation.json"]
        checksum_lines = [f"{sha256_file(temporary / name)}  {name}\n" for name in sorted(checksummed)]
        (temporary / "checksums.sha256").write_text("".join(checksum_lines), encoding="ascii")
        validate_release(temporary, source)

        if backup.exists():
            shutil.rmtree(backup)
        if target.exists():
            target.rename(backup)
        temporary.rename(target)
        if backup.exists():
            shutil.rmtree(backup)
        return target
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        if backup.exists() and not target.exists():
            backup.rename(target)
        raise


def validate_release(target: Path, source: dict[str, Any]) -> None:
    required_files = {"checksums.sha256", "datapackage.json", "payments.csv.gz", "payments.parquet", "validation.json"}
    actual_files = {path.name for path in target.iterdir() if path.is_file()}
    if actual_files != required_files:
        raise SpendingDataError(f"release files are {sorted(actual_files)}; expected {sorted(required_files)}")

    checksum_lines = (target / "checksums.sha256").read_text(encoding="ascii").splitlines()
    expected_checksums = required_files - {"checksums.sha256"}
    checksummed_names = [line.split("  ", 1)[1] for line in checksum_lines]
    if len(checksummed_names) != len(set(checksummed_names)) or set(checksummed_names) != expected_checksums:
        raise SpendingDataError(f"checksums cover {sorted(checksummed_names)}; expected {sorted(expected_checksums)}")
    for line in checksum_lines:
        digest, filename = line.split("  ", 1)
        if sha256_file(target / filename) != digest:
            raise SpendingDataError(f"checksum mismatch for {filename}")

    descriptor = json.loads((target / "datapackage.json").read_text(encoding="utf-8"))
    if descriptor.get("rights_status") != source["rights_status"]:
        raise SpendingDataError("Data Package rights status does not match the source registry")

    connection = duckdb.connect(":memory:")
    try:
        row = connection.execute(
            """
            SELECT count(*), sum(amount_gbp),
                   count(*) FILTER (WHERE entity = 'NHS England'),
                   sum(amount_gbp) FILTER (WHERE entity = 'NHS England'),
                   count(*) FILTER (WHERE amount_gbp < 0),
                   count(*) FILTER (WHERE vat_registration_number IS NULL)
            FROM read_parquet(?)
            """,
            [str(target / "payments.parquet")],
        ).fetchone()
    finally:
        connection.close()
    parquet_stats = {
        "rows": row[0],
        "total_gbp": row[1],
        "nhs_england_rows": row[2],
        "nhs_england_total_gbp": row[3],
        "negative_rows": row[4],
        "missing_vat_rows": row[5],
    }
    _validate_expected_stats(parquet_stats, source["expected"])

    csv_rows = 0
    csv_total = Decimal("0.00")
    with gzip.open(target / "payments.csv.gz", "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != OUTPUT_COLUMNS:
            raise SpendingDataError("CSV column order does not match the canonical schema")
        for record in reader:
            csv_rows += 1
            csv_total += Decimal(record["amount_gbp"])
    if csv_rows != parquet_stats["rows"] or csv_total != parquet_stats["total_gbp"]:
        raise SpendingDataError("CSV and Parquet row counts or totals differ")


def validate_top_level_finances() -> None:
    registry = _load_yaml(FINANCE_REGISTRY)
    if registry.get("schema_version") != 1:
        raise SpendingDataError("unsupported top-level-finance schema")
    years = registry.get("financial_years")
    if not isinstance(years, list):
        raise SpendingDataError("top-level finance registry must contain financial_years")
    source_ids = {source["id"] for source in registry.get("sources", [])}
    for year in years:
        figures = year.get("figures", [])
        by_id = {figure["id"]: figure for figure in figures}
        if len(by_id) != len(figures):
            raise SpendingDataError(f"duplicate figure ID in {year.get('financial_year')}")
        for figure in figures:
            if int(figure["amount_gbp"]) < 0:
                raise SpendingDataError(f"{figure['id']} has a negative headline amount")
            if "source_id" in figure and figure["source_id"] not in source_ids:
                raise SpendingDataError(f"{figure['id']} refers to unknown source {figure['source_id']}")
            if "derived_from" not in figure:
                continue
            parts = [by_id[figure_id] for figure_id in figure["derived_from"]]
            if len(parts) != 2:
                raise SpendingDataError(f"{figure['id']} must derive from exactly two figures")
            if parts[0]["boundary"] != parts[1]["boundary"] or parts[0]["boundary"] != figure["boundary"]:
                raise SpendingDataError(f"{figure['id']} mixes accounting boundaries")
            expected = int(parts[0]["amount_gbp"]) - int(parts[1]["amount_gbp"])
            if int(figure["amount_gbp"]) != expected:
                raise SpendingDataError(f"{figure['id']} is {figure['amount_gbp']}; expected {expected}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    fetch_parser = subparsers.add_parser("fetch", help="download and verify the registered source workbook")
    fetch_parser.add_argument("--source", default="2025-09-payments-over-25000", help="source registry ID")
    fetch_parser.add_argument("--archive", action="store_true", help="download the archived source URL")
    for command, help_text in (
        ("build", "build and validate the local data release"),
        ("validate", "validate source, finance registry, and built release"),
        ("all", "fetch, build, and validate"),
    ):
        command_parser = subparsers.add_parser(command, help=help_text)
        command_parser.add_argument("--source", default="2025-09-payments-over-25000", help="source registry ID")
        if command == "all":
            command_parser.add_argument("--archive", action="store_true", help="download the archived source URL")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        source = load_source(args.source)
        if args.command in {"fetch", "all"}:
            path = fetch_source(source, use_archive=getattr(args, "archive", False))
            print(f"verified source: {path}", file=sys.stderr)
        else:
            path = source_path(source)
            verify_source_file(path, source)

        if args.command in {"build", "all"}:
            target = build_release(path, source, release_path(source))
            print(f"built release: {target}", file=sys.stderr)
        if args.command in {"validate", "all"}:
            validate_top_level_finances()
            validate_release(release_path(source), source)
            print(f"validated release: {release_path(source)}", file=sys.stderr)
        return 0
    except (OSError, SpendingDataError, duckdb.Error, yaml.YAMLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
