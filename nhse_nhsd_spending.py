#!/usr/bin/env python3
"""Fetch, normalize, and validate NHS Digital / HSCIC pre-merger spend-information CSVs.

NHS Digital (formerly the Health and Social Care Information Centre, HSCIC)
published its own "spend information" series on digital.nhs.uk, separately
from NHS England's payments-over-£25,000 publication, until the 1 February
2023 merger folded NHS Digital into NHS England. The two corpora use
genuinely different column schemas, preamble shapes, and encodings, and the
two bodies were legally distinct until the merger: this module and its
registry (spending/nhsd-data-sources.yaml) are kept separate from
nhse_spending.py's NHS England pipeline, and NHSD releases are never summed
into NHS England's own spend-by-year totals.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "spending" / "nhsd-data-sources.yaml"
SOURCE_DIR = ROOT / "spending" / "sources" / "nhsd"
DATA_DIR = ROOT / "spending" / "data"
TOOL_VERSION = "0.1.0"
PARQUET_ROW_GROUP_SIZE = 64_000

# Verified against all ten registered CSVs: every row in every file parses
# cleanly as day/month/year with no ambiguous or alternate format observed.
DATE_FORMAT = "%d/%m/%Y"

OUTPUT_COLUMNS = [
    "observation_id",
    "department_family",
    "entity",
    "transaction_date",
    "expense_type",
    "expense_area",
    "supplier",
    "purchase_invoice_number",
    "amount_gbp",
    "source_amount_raw",
    "currency",
    "description",
    "redaction_status",
    "source_id",
    "source_period",
    "source_sha256",
    "source_file",
    "source_row",
]

# The registry's csv.columns mapping must cover exactly these canonical fields.
CANONICAL_CSV_FIELDS = [
    "department_family",
    "entity",
    "transaction_date",
    "expense_type",
    "expense_area",
    "supplier",
    "purchase_invoice_number",
    "amount_gbp",
    "description",
]


class NhsdDataError(RuntimeError):
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
        raise NhsdDataError(f"{path} must contain a YAML mapping")
    return value


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    registry = _load_yaml(path)
    if registry.get("schema_version") != 1:
        raise NhsdDataError("unsupported NHSD source-registry schema")
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        raise NhsdDataError("NHSD source registry must contain a non-empty sources list")
    source_ids = [source.get("id") for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise NhsdDataError("NHSD source registry contains duplicate source IDs")

    required = {
        "id",
        "title",
        "period",
        "publisher",
        "landing_page_url",
        "landing_page_archive_url",
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
        "csv",
        "expected",
    }
    for source in sources:
        missing = required - source.keys()
        if missing:
            raise NhsdDataError(f"NHSD source {source.get('id', '<unknown>')!r} is missing {', '.join(sorted(missing))}")
        csv_config = source["csv"]
        csv_required = {"encoding", "header_row", "columns"}
        missing_csv = csv_required - csv_config.keys()
        if missing_csv:
            raise NhsdDataError(f"NHSD source {source['id']!r} csv config is missing {', '.join(sorted(missing_csv))}")
        columns = csv_config["columns"]
        if set(columns.keys()) != set(CANONICAL_CSV_FIELDS):
            raise NhsdDataError(f"NHSD source {source['id']!r} csv.columns must map exactly {sorted(CANONICAL_CSV_FIELDS)}")
        if len(set(columns.values())) != len(columns):
            raise NhsdDataError(f"NHSD source {source['id']!r} csv.columns maps two fields to the same header text")
    return registry


def load_source(source_id: str, registry: dict[str, Any] | None = None) -> dict[str, Any]:
    registry = registry or load_registry()
    matches = [source for source in registry["sources"] if source.get("id") == source_id]
    if len(matches) != 1:
        raise NhsdDataError(f"expected exactly one NHSD source named {source_id!r}, found {len(matches)}")
    return matches[0]


def source_path(source: dict[str, Any]) -> Path:
    return SOURCE_DIR / str(source["filename"])


def release_path(source: dict[str, Any]) -> Path:
    return DATA_DIR / str(source["id"])


def verify_source_file(path: Path, source: dict[str, Any]) -> None:
    expected_bytes = int(source["bytes"])
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise NhsdDataError(f"{path} is {actual_bytes} bytes; expected {expected_bytes}")
    expected_hash = str(source["sha256"])
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise NhsdDataError(f"{path} has SHA-256 {actual_hash}; expected {expected_hash}")


def fetch_source(source: dict[str, Any]) -> Path:
    # Every registered digital.nhs.uk source URL now 404s following the NHS
    # Digital/NHS England merger; only the UK Government Web Archive capture
    # is live, so unlike nhse_spending.py there is no live-vs-archive choice.
    target = source_path(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        verify_source_file(target, source)
        return target

    url = str(source["archive_url"])
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


def verify_registered_source(source: dict[str, Any]) -> Path:
    path = source_path(source)
    verify_source_file(path, source)
    return path


def _normalize_header_cell(value: str) -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip()


def _required_text(value: str, field: str, row_number: int) -> str:
    text = value.strip()
    if not text:
        raise NhsdDataError(f"row {row_number}: {field} must be non-empty text")
    return text


def _identifier(value: str, field: str, row_number: int, nullable: bool = False) -> str | None:
    text = value.strip()
    if not text:
        if nullable:
            return None
        raise NhsdDataError(f"row {row_number}: {field} must be present")
    return text


def _date(value: str, row_number: int) -> dt.date:
    text = value.strip()
    try:
        return dt.datetime.strptime(text, DATE_FORMAT).date()
    except ValueError as error:
        raise NhsdDataError(f"row {row_number}: Invoice date {text!r} does not match {DATE_FORMAT}") from error


def _money(value: str, row_number: int) -> tuple[Decimal, str]:
    cleaned = value.strip().replace(",", "").replace("£", "").strip()
    if not cleaned:
        raise NhsdDataError(f"row {row_number}: Invoice value must be present")
    try:
        source_amount = Decimal(cleaned)
    except InvalidOperation as error:
        raise NhsdDataError(f"row {row_number}: Invoice value {value!r} is not numeric") from error
    amount = source_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if not amount.is_finite():
        raise NhsdDataError(f"row {row_number}: Invoice value is not finite")
    return amount, format(source_amount, "f")


def parse_csv(path: Path, source: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    verify_source_file(path, source)
    csv_config = source["csv"]
    encoding = str(csv_config["encoding"])
    header_row = int(csv_config["header_row"])
    column_map: dict[str, str] = csv_config["columns"]

    raw = path.read_bytes()
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError as error:
        raise NhsdDataError(f"source does not decode as registered encoding {encoding!r}") from error
    rows = list(csv.reader(text.splitlines(keepends=True)))
    if len(rows) < header_row:
        raise NhsdDataError(f"source has {len(rows)} logical rows; registered header_row is {header_row}")

    header_cells = [_normalize_header_cell(cell) for cell in rows[header_row - 1]]
    if len(set(header_cells)) != len(header_cells):
        raise NhsdDataError(f"header row has duplicate column names: {header_cells!r}")
    expected_headers = set(column_map.values())
    if set(header_cells) != expected_headers:
        raise NhsdDataError(f"unexpected header row {header_cells!r}; expected exactly {sorted(expected_headers)}")
    column_index = {field: header_cells.index(header_text) for field, header_text in column_map.items()}
    width = len(header_cells)

    records: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows[header_row:], start=header_row + 1):
        if all(not cell.strip() for cell in row):
            continue
        if len(row) != width:
            raise NhsdDataError(f"row {row_number}: has {len(row)} cells; expected {width}")

        department_family = _required_text(row[column_index["department_family"]], "Department Family", row_number)
        entity = _required_text(row[column_index["entity"]], "Entity", row_number)
        transaction_date = _date(row[column_index["transaction_date"]], row_number)
        expense_type = _required_text(row[column_index["expense_type"]], "Consolidated Expense Type", row_number)
        expense_area = _required_text(row[column_index["expense_area"]], "Expense area", row_number)
        supplier = _required_text(row[column_index["supplier"]], "Supplier", row_number)
        purchase_invoice_number = _identifier(
            row[column_index["purchase_invoice_number"]], "Purchase Invoice Number", row_number, nullable=True
        )
        amount, source_amount_raw = _money(row[column_index["amount_gbp"]], row_number)
        description = _required_text(row[column_index["description"]], "Description", row_number)

        source_values = {
            "department_family": department_family,
            "entity": entity,
            "transaction_date": transaction_date,
            "expense_type": expense_type,
            "expense_area": expense_area,
            "supplier": supplier,
            "purchase_invoice_number": purchase_invoice_number,
            "amount_gbp": amount,
            "source_amount_raw": source_amount_raw,
            "description": description,
        }
        identity_input = {
            "schema": "nhsd-spend-information.v1",
            "source_sha256": source["sha256"],
            "source_row": row_number,
            "values": source_values,
        }
        redacted = any(cell.strip().casefold() == "removed" for cell in row)
        record = {
            "observation_id": hashlib.sha256(_canonical_json(identity_input)).hexdigest(),
            **source_values,
            "currency": "GBP",
            "redaction_status": "source_removed" if redacted else "none",
            "source_id": str(source["id"]),
            "source_period": str(source["period"]),
            "source_sha256": str(source["sha256"]),
            "source_file": str(source["filename"]),
            "source_row": row_number,
        }
        records.append(record)

    records.sort(key=lambda row: (row["source_row"], row["observation_id"]))
    if len({row["observation_id"] for row in records}) != len(records):
        raise NhsdDataError("observation IDs are not unique")

    stats = _record_statistics(records)
    _validate_expected_stats(stats, source["expected"])
    return records, stats


def _record_statistics(records: list[dict[str, Any]]) -> dict[str, Any]:
    entities = sorted({row["entity"] for row in records})
    if len(entities) != 1:
        raise NhsdDataError(f"expected exactly one distinct Entity value per NHSD release, found {entities}")
    return {
        "rows": len(records),
        "total_gbp": sum((row["amount_gbp"] for row in records), Decimal("0.00")),
        "entity": entities[0],
        "negative_rows": sum(row["amount_gbp"] < 0 for row in records),
        "minimum_date": min(row["transaction_date"] for row in records),
        "maximum_date": max(row["transaction_date"] for row in records),
    }


def _validate_expected_stats(stats: dict[str, Any], expected: dict[str, Any]) -> None:
    decimal_fields = {"total_gbp"}
    date_fields = {"minimum_date", "maximum_date"}
    for field, expected_value in expected.items():
        if field not in stats:
            raise NhsdDataError(f"{field} is not a recognized statistic for this source's rows")
        actual_value = stats[field]
        if field in decimal_fields:
            expected_value = Decimal(str(expected_value))
        elif field in date_fields:
            expected_value = dt.date.fromisoformat(str(expected_value))
        elif field == "entity":
            expected_value = str(expected_value)
        else:
            expected_value = int(expected_value)
        if actual_value != expected_value:
            raise NhsdDataError(f"{field} is {actual_value}; expected {expected_value}")


def _arrow_schema(provenance: dict[str, Any], columns: list[str]) -> pa.Schema:
    types: dict[str, tuple[pa.DataType, bool]] = {
        "observation_id": (pa.string(), False),
        "department_family": (pa.string(), False),
        "entity": (pa.string(), False),
        "transaction_date": (pa.date32(), False),
        "expense_type": (pa.string(), False),
        "expense_area": (pa.string(), False),
        "supplier": (pa.string(), False),
        "purchase_invoice_number": (pa.string(), True),
        "amount_gbp": (pa.decimal128(18, 2), False),
        "source_amount_raw": (pa.string(), False),
        "currency": (pa.string(), False),
        "description": (pa.string(), False),
        "redaction_status": (pa.string(), False),
        "source_id": (pa.string(), False),
        "source_period": (pa.string(), False),
        "source_sha256": (pa.string(), False),
        "source_file": (pa.string(), False),
        "source_row": (pa.int32(), False),
    }
    fields = [pa.field(column, types[column][0], nullable=types[column][1]) for column in columns]
    return pa.schema(fields, metadata={b"nhse.nhsd.provenance": _canonical_json(provenance)})


def _write_csv(path: Path, records: list[dict[str, Any]], columns: list[str]) -> None:
    import gzip
    import io

    with path.open("wb") as raw_output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, mtime=0, compresslevel=9) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text_output:
                writer = csv.DictWriter(text_output, fieldnames=columns, lineterminator="\n")
                writer.writeheader()
                for record in records:
                    writer.writerow({column: _jsonable(record[column]) for column in columns})


def _content_fingerprint(records: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(_canonical_json(record))
        digest.update(b"\n")
    return digest.hexdigest()


def _typed_csv_record(record: dict[str, str]) -> dict[str, Any]:
    typed: dict[str, Any] = dict(record)
    typed["transaction_date"] = dt.date.fromisoformat(record["transaction_date"])
    typed["amount_gbp"] = Decimal(record["amount_gbp"])
    typed["source_row"] = int(record["source_row"])
    typed["purchase_invoice_number"] = record["purchase_invoice_number"] or None
    return typed


def _expected_observation_id(record: dict[str, Any]) -> str:
    value_fields = [
        "department_family",
        "entity",
        "transaction_date",
        "expense_type",
        "expense_area",
        "supplier",
        "purchase_invoice_number",
        "amount_gbp",
        "source_amount_raw",
        "description",
    ]
    identity_input = {
        "schema": "nhsd-spend-information.v1",
        "source_sha256": record["source_sha256"],
        "source_row": record["source_row"],
        "values": {field: record[field] for field in value_fields},
    }
    return hashlib.sha256(_canonical_json(identity_input)).hexdigest()


def _resource_schema(columns: list[str]) -> dict[str, Any]:
    types = {
        "observation_id": "string",
        "department_family": "string",
        "entity": "string",
        "transaction_date": "date",
        "expense_type": "string",
        "expense_area": "string",
        "supplier": "string",
        "purchase_invoice_number": "string",
        "amount_gbp": "number",
        "source_amount_raw": "string",
        "currency": "string",
        "description": "string",
        "redaction_status": "string",
        "source_id": "string",
        "source_period": "string",
        "source_sha256": "string",
        "source_file": "string",
        "source_row": "integer",
    }
    return {
        "fields": [
            {"name": column, "type": types[column], **({"decimalChar": "."} if column == "amount_gbp" else {})}
            for column in columns
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
            "publisher",
            "landing_page_url",
            "landing_page_archive_url",
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
    records, stats = parse_csv(path, source)
    content_fingerprint = _content_fingerprint(records)
    provenance = {
        "dataset": "nhs-digital-spend-information",
        "dataset_version": f"{source['period']}.1",
        "schema_version": 1,
        "tool": "nhse-research-data",
        "tool_version": TOOL_VERSION,
        "normalized_content_sha256": content_fingerprint,
        "source": _source_provenance(source),
    }

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    backup = target.with_name(f".{target.name}.previous")
    try:
        parquet_path = temporary / "nhsd-spend.parquet"
        csv_path = temporary / "nhsd-spend.csv.gz"
        table = pa.Table.from_pylist(records, schema=_arrow_schema(provenance, OUTPUT_COLUMNS))
        pq.write_table(
            table,
            parquet_path,
            compression="zstd",
            compression_level=3,
            row_group_size=PARQUET_ROW_GROUP_SIZE,
            version="2.6",
            write_statistics=True,
        )
        _write_csv(csv_path, records, OUTPUT_COLUMNS)

        parquet_hash = sha256_file(parquet_path)
        csv_hash = sha256_file(csv_path)
        validation = {
            "dataset": "nhs-digital-spend-information",
            "dataset_version": f"{source['period']}.1",
            "schema_version": 1,
            "normalized_content_sha256": content_fingerprint,
            "artifacts": {
                "nhsd-spend.csv.gz": {"bytes": csv_path.stat().st_size, "sha256": csv_hash},
                "nhsd-spend.parquet": {"bytes": parquet_path.stat().st_size, "sha256": parquet_hash},
            },
            "statistics": _jsonable(stats),
            "status": "passed",
            "source_sha256": source["sha256"],
        }
        descriptor = {
            "profile": "tabular-data-package",
            "name": f"nhs-digital-spend-information-{source['period']}",
            "title": source["title"],
            "version": f"{source['period']}.1",
            "description": (
                "Normalized NHS Digital (formerly HSCIC) spend-information transparency data, "
                "published separately from NHS England pre-merger, with physical source-row provenance."
            ),
            "licenses": [
                {"name": "OGL-UK-3.0", "path": source["referenced_licence_url"], "title": "Open Government Licence v3.0"}
            ],
            "rights": source["rights_note"],
            "rights_status": source["rights_status"],
            "sources": [_source_provenance(source)],
            "nhse": {
                "normalized_content_sha256": content_fingerprint,
                "schema_version": 1,
                "tool_version": TOOL_VERSION,
                "limitations": [
                    "NHS Digital (formerly HSCIC) was a legally distinct body from NHS England until their 1 February 2023 merger; these rows are never summed into NHS England's own payments totals.",
                    "This thresholded spend publication is not a general ledger and does not reconcile one-for-one to annual accrual accounts.",
                    "Supplier text is preserved as published and has not been entity-resolved.",
                    "Negative values are retained and not classified as refunds, reversals or corrections without source evidence.",
                    "The project-owner redistribution decision for this source relies on the archived publication page's own 'freely re-usable under the same terms as data.gov.uk' statement.",
                ],
            },
            "resources": [
                {
                    "name": "nhsd-spend-parquet",
                    "path": "nhsd-spend.parquet",
                    "format": "parquet",
                    "mediatype": "application/vnd.apache.parquet",
                    "bytes": parquet_path.stat().st_size,
                    "hash": f"sha256:{parquet_hash}",
                    "schema": _resource_schema(OUTPUT_COLUMNS),
                },
                {
                    "name": "nhsd-spend-csv",
                    "path": "nhsd-spend.csv.gz",
                    "format": "csv",
                    "mediatype": "text/csv",
                    "compression": "gzip",
                    "encoding": "utf-8",
                    "bytes": csv_path.stat().st_size,
                    "hash": f"sha256:{csv_hash}",
                    "schema": _resource_schema(OUTPUT_COLUMNS),
                },
            ],
        }
        (temporary / "validation.json").write_bytes(_json_bytes(validation))
        (temporary / "datapackage.json").write_bytes(_json_bytes(descriptor))

        checksummed = ["datapackage.json", "nhsd-spend.csv.gz", "nhsd-spend.parquet", "validation.json"]
        checksum_lines = [f"{sha256_file(temporary / name)}  {name}\n" for name in sorted(checksummed)]
        (temporary / "checksums.sha256").write_text("".join(checksum_lines), encoding="ascii")
        validate_release(temporary, source, verify_against_source=True, source_file=path)

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


def validate_release(
    target: Path,
    source: dict[str, Any],
    *,
    verify_against_source: bool = False,
    source_file: Path | None = None,
) -> None:
    import gzip

    required_files = {"checksums.sha256", "datapackage.json", "nhsd-spend.csv.gz", "nhsd-spend.parquet", "validation.json"}
    actual_files = {path.name for path in target.iterdir() if path.is_file()}
    if actual_files != required_files:
        raise NhsdDataError(f"release files are {sorted(actual_files)}; expected {sorted(required_files)}")

    checksum_lines = (target / "checksums.sha256").read_text(encoding="ascii").splitlines()
    expected_checksums = required_files - {"checksums.sha256"}
    checksummed_names = [line.split("  ", 1)[1] for line in checksum_lines]
    if len(checksummed_names) != len(set(checksummed_names)) or set(checksummed_names) != expected_checksums:
        raise NhsdDataError(f"checksums cover {sorted(checksummed_names)}; expected {sorted(expected_checksums)}")
    for line in checksum_lines:
        digest, filename = line.split("  ", 1)
        if sha256_file(target / filename) != digest:
            raise NhsdDataError(f"checksum mismatch for {filename}")

    descriptor = json.loads((target / "datapackage.json").read_text(encoding="utf-8"))
    if descriptor.get("rights_status") != source["rights_status"]:
        raise NhsdDataError("Data Package rights status does not match the source registry")
    if descriptor.get("sources") != [_source_provenance(source)]:
        raise NhsdDataError("Data Package sources do not match the source registry")

    validation = json.loads((target / "validation.json").read_text(encoding="utf-8"))
    if validation.get("source_sha256") != source["sha256"]:
        raise NhsdDataError("validation source digest does not match the source registry")

    parquet_records = pq.read_table(target / "nhsd-spend.parquet").to_pylist()
    content_fingerprint = _content_fingerprint(parquet_records)
    if validation.get("normalized_content_sha256") != content_fingerprint:
        raise NhsdDataError("validation content fingerprint does not match Parquet rows")
    if descriptor.get("nhse", {}).get("normalized_content_sha256") != content_fingerprint:
        raise NhsdDataError("Data Package content fingerprint does not match Parquet rows")

    observation_ids = [record["observation_id"] for record in parquet_records]
    if len(observation_ids) != len(set(observation_ids)):
        raise NhsdDataError("Parquet observation IDs are not unique")
    if any(record["source_row"] < 1 for record in parquet_records):
        raise NhsdDataError("Parquet contains an invalid source row")
    if any(record["currency"] != "GBP" for record in parquet_records):
        raise NhsdDataError("Parquet contains a non-GBP currency")
    if any(record["redaction_status"] not in {"none", "source_removed"} for record in parquet_records):
        raise NhsdDataError("Parquet contains an invalid redaction status")
    if any(record["observation_id"] != _expected_observation_id(record) for record in parquet_records):
        raise NhsdDataError("Parquet observation ID does not match its values and source provenance")

    expected_binding = (source["sha256"], source["filename"])
    actual_bindings = {(record["source_sha256"], record["source_file"]) for record in parquet_records}
    if actual_bindings != {expected_binding}:
        raise NhsdDataError("Parquet row provenance does not match the source registry")

    if verify_against_source:
        expected_records, _ = parse_csv(source_file or source_path(source), source)
        if parquet_records != expected_records:
            raise NhsdDataError("Parquet rows do not match the registered source CSV")

    connection = duckdb.connect(":memory:")
    try:
        row = connection.execute(
            """
            SELECT count(*), sum(amount_gbp), count(*) FILTER (WHERE amount_gbp < 0), min(transaction_date), max(transaction_date)
            FROM read_parquet(?)
            """,
            [str(target / "nhsd-spend.parquet")],
        ).fetchone()
    finally:
        connection.close()
    parquet_stats = {
        "rows": row[0],
        "total_gbp": row[1],
        "entity": source["expected"]["entity"],
        "negative_rows": row[2],
        "minimum_date": row[3],
        "maximum_date": row[4],
    }
    _validate_expected_stats(parquet_stats, source["expected"])

    csv_rows = 0
    csv_total = Decimal("0.00")
    csv_records: list[dict[str, Any]] = []
    with gzip.open(target / "nhsd-spend.csv.gz", "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != OUTPUT_COLUMNS:
            raise NhsdDataError("CSV column order does not match the canonical schema")
        for record in reader:
            csv_rows += 1
            csv_total += Decimal(record["amount_gbp"])
            csv_records.append(_typed_csv_record(record))
    if csv_rows != parquet_stats["rows"] or csv_total != parquet_stats["total_gbp"]:
        raise NhsdDataError("CSV and Parquet row counts or totals differ")
    if csv_records != parquet_records:
        raise NhsdDataError("CSV and Parquet normalized rows or row order differ")


# All ten registered fiscal years are full fiscal-year releases; none is a
# partial period. Coverage stays an explicit per-source mapping rather than a
# blanket assumption, consistent with nhse_spending.SPEND_SUMMARY_COVERAGE.
NHSD_SPEND_SUMMARY_COVERAGE: dict[str, dict[str, Any]] = {
    "2013-14-nhsd-spend-information": {"kind": "fiscal_year", "label": "2013/14"},
    "2014-15-nhsd-spend-information": {"kind": "fiscal_year", "label": "2014/15"},
    "2015-16-nhsd-spend-information": {"kind": "fiscal_year", "label": "2015/16"},
    "2016-17-nhsd-spend-information": {"kind": "fiscal_year", "label": "2016/17"},
    "2017-18-nhsd-spend-information": {"kind": "fiscal_year", "label": "2017/18"},
    "2018-19-nhsd-spend-information": {"kind": "fiscal_year", "label": "2018/19"},
    "2019-20-nhsd-spend-information": {"kind": "fiscal_year", "label": "2019/20"},
    "2020-21-nhsd-spend-information": {"kind": "fiscal_year", "label": "2020/21"},
    "2021-22-nhsd-spend-information": {"kind": "fiscal_year", "label": "2021/22"},
    "2022-23-nhsd-spend-information": {"kind": "fiscal_year", "label": "2022/23"},
}


def build_nhsd_spend_summary(target: Path | None = None) -> Path:
    registry = load_registry()
    registered_ids = {str(source["id"]) for source in registry["sources"]}
    if set(NHSD_SPEND_SUMMARY_COVERAGE) - registered_ids:
        raise NhsdDataError("NHSD spend summary coverage refers to an unregistered source")

    years: list[dict[str, Any]] = []
    for source in registry["sources"]:
        source_id = str(source["id"])
        coverage = NHSD_SPEND_SUMMARY_COVERAGE.get(source_id)
        if coverage is None:
            continue
        validation_path = release_path(source) / "validation.json"
        if not validation_path.exists():
            raise NhsdDataError(f"no committed NHSD release found for {source_id}; build it first")
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        stats = validation["statistics"]
        years.append(
            {
                "source_id": source_id,
                "period": str(source["period"]),
                "label": coverage["label"],
                "coverage": coverage["kind"],
                "entity": stats["entity"],
                "rows": stats["rows"],
                "total_gbp": str(Decimal(stats["total_gbp"])),
            }
        )
    years.sort(key=lambda year: year["period"])

    summary = {
        "schema_version": 1,
        "generated_from": sorted(NHSD_SPEND_SUMMARY_COVERAGE),
        "note": (
            "NHS Digital (formerly HSCIC) was a legally distinct body from NHS England until their "
            "1 February 2023 merger. This series is published separately and must never be summed "
            "into NHS England's own spend-by-year totals."
        ),
        "years": years,
    }
    target = target or (ROOT / "spending" / "nhsd-spend-by-year.json")
    target.write_bytes(_json_bytes(summary))
    return target


if __name__ == "__main__":
    raise SystemExit("run via: uv run python nhse_spending.py nhsd-fetch|nhsd-build|nhsd-validate --source <id>")
