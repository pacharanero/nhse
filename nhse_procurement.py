#!/usr/bin/env python3
"""Build deterministic procurement-notice enrichment fixtures."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
import unicodedata
import urllib.request
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import duckdb
import yaml


ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "spending" / "procurement-sources.yaml"
SOURCE_DIR = ROOT / "spending" / "sources" / "procurement"
DATA_ROOT = ROOT / "spending" / "data"
DATA_DIR = DATA_ROOT / "procurement-notice-fixtures-2026-10-17"
TOOL_VERSION = "0.1.0"
NAME_NORMALIZATION_VERSION = "supplier-name-v1"
MATCH_RULE_VERSION = "name-candidate-v1"
LEGAL_SUFFIXES = {"LIMITED", "LTD", "LLP", "PLC"}
VALUE_TYPES = {
    "planning_estimate",
    "tender_minimum",
    "tender_ceiling",
    "estimated_lot",
    "award_value",
    "framework_maximum",
    "contract_value",
    "proposed_modification",
    "modification_increment",
    "modified_contract_value",
    "forecast_not_committed",
}


class ProcurementDataError(RuntimeError):
    """A procurement source, schema, or enrichment invariant failed."""


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


def _registry_semantic_sha256(registry: dict[str, Any]) -> str:
    normalized = _jsonable(registry)
    normalized["release"] = dict(normalized["release"])
    normalized["release"].pop("expected_artifacts", None)
    return hashlib.sha256(_canonical_json(normalized)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        registry = yaml.safe_load(handle)
    if not isinstance(registry, dict) or registry.get("schema_version") != 1:
        raise ProcurementDataError("unsupported procurement source-registry schema")
    release = registry.get("release")
    sources = registry.get("sources")
    if not isinstance(release, dict) or not isinstance(sources, list) or not sources:
        raise ProcurementDataError("procurement registry must contain release metadata and sources")
    release_required = {
        "id",
        "limitations",
        "matching_release_ids",
        "normalization_schema_version",
        "observed_on",
        "payment_release",
        "rights_status",
        "rights_url",
        "title",
    }
    if missing := release_required - release.keys():
        raise ProcurementDataError(f"procurement release metadata is missing {', '.join(sorted(missing))}")
    expected_artifacts = release.get("expected_artifacts")
    if expected_artifacts is not None:
        if not isinstance(expected_artifacts, dict) or set(expected_artifacts) != {"procurement.json", "validation.json"}:
            raise ProcurementDataError("expected_artifacts must pin procurement.json and validation.json")
        if any(not re.fullmatch(r"[0-9a-f]{64}", str(digest)) for digest in expected_artifacts.values()):
            raise ProcurementDataError("expected procurement artifact digests must be lowercase SHA-256 values")
    payment_required = {"id", "parquet", "sha256"}
    if missing := payment_required - release["payment_release"].keys():
        raise ProcurementDataError(f"payment release metadata is missing {', '.join(sorted(missing))}")
    source_required = {
        "bytes",
        "filename",
        "id",
        "media_type",
        "monetary_observations",
        "sha256",
        "source_family",
        "source_system",
        "source_url",
    }
    source_ids: list[str] = []
    observation_ids: list[str] = []
    for source in sources:
        if not isinstance(source, dict):
            raise ProcurementDataError("procurement source entries must be mappings")
        if missing := source_required - source.keys():
            raise ProcurementDataError(
                f"procurement source {source.get('id', '<unknown>')!r} is missing {', '.join(sorted(missing))}"
            )
        if source["source_system"] not in {"find-a-tender", "contracts-finder"}:
            raise ProcurementDataError(f"unknown procurement source system {source['source_system']!r}")
        if source["source_system"] == "find-a-tender":
            source_identity_required = {"expected_ocid", "expected_release_ids"}
        else:
            source_identity_required = {"expected_notice_id", "expected_parent_id", "expected_version"}
        if missing := source_identity_required - source.keys():
            raise ProcurementDataError(
                f"procurement source {source['id']!r} is missing {', '.join(sorted(missing))}"
            )
        source_ids.append(str(source["id"]))
        for observation in source["monetary_observations"]:
            required = {
                "currency",
                "expected_amount",
                "id",
                "scope_id",
                "scope_type",
                "source_pointer",
                "value_type",
                "vat_basis",
            }
            if missing := required - observation.keys():
                raise ProcurementDataError(
                    f"monetary observation {observation.get('id', '<unknown>')!r} is missing "
                    f"{', '.join(sorted(missing))}"
                )
            if observation["value_type"] not in VALUE_TYPES:
                raise ProcurementDataError(f"unknown procurement value type {observation['value_type']!r}")
            observation_ids.append(str(observation["id"]))
    if len(source_ids) != len(set(source_ids)):
        raise ProcurementDataError("procurement registry contains duplicate source IDs")
    if len(observation_ids) != len(set(observation_ids)):
        raise ProcurementDataError("procurement registry contains duplicate monetary-observation IDs")
    return registry


def source_path(source: dict[str, Any], source_directory: Path = SOURCE_DIR) -> Path:
    return source_directory / str(source["filename"])


def release_path(registry: dict[str, Any]) -> Path:
    return DATA_ROOT / str(registry["release"]["id"])


def _verify_file(path: Path, expected_bytes: int, expected_sha256: str) -> None:
    if not path.exists():
        raise ProcurementDataError(f"missing procurement source {path}")
    if path.stat().st_size != int(expected_bytes):
        raise ProcurementDataError(f"unexpected byte length for {path}")
    if sha256_file(path) != str(expected_sha256):
        raise ProcurementDataError(f"unexpected SHA-256 for {path}")


def verify_sources(registry: dict[str, Any], source_directory: Path = SOURCE_DIR) -> list[Path]:
    paths: list[Path] = []
    for source in registry["sources"]:
        path = source_path(source, source_directory)
        _verify_file(path, source["bytes"], source["sha256"])
        try:
            value = json.loads(path.read_bytes())
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ProcurementDataError(f"invalid JSON in {path}: {error}") from error
        if not isinstance(value, dict):
            raise ProcurementDataError(f"procurement source {path} must contain a JSON object")
        paths.append(path)
    return paths


def fetch_source(source_id: str, registry: dict[str, Any], source_directory: Path = SOURCE_DIR) -> Path:
    matches = [source for source in registry["sources"] if source["id"] == source_id]
    if len(matches) != 1:
        raise ProcurementDataError(f"expected exactly one procurement source named {source_id!r}")
    source = matches[0]
    source_directory.mkdir(parents=True, exist_ok=True)
    target = source_path(source, source_directory)
    request = urllib.request.Request(
        str(source["source_url"]),
        headers={"User-Agent": "nhse-research-data/0.1 procurement source fetcher"},
    )
    temporary: Path | None = None
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            with tempfile.NamedTemporaryFile(dir=source_directory, prefix=f".{target.name}.", delete=False) as handle:
                temporary = Path(handle.name)
                shutil.copyfileobj(response, handle)
                handle.flush()
                os.fsync(handle.fileno())
        _verify_file(temporary, source["bytes"], source["sha256"])
        temporary.replace(target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return target


def _pointer(value: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise ProcurementDataError(f"JSON pointer must start with '/': {pointer!r}")
    current = value
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (IndexError, ValueError) as error:
                raise ProcurementDataError(f"JSON pointer does not resolve: {pointer}") from error
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise ProcurementDataError(f"JSON pointer does not resolve: {pointer}")
    return current


def _money(value: Any) -> str:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as error:
        raise ProcurementDataError(f"invalid monetary value {value!r}") from error
    if not amount.is_finite():
        raise ProcurementDataError(f"non-finite monetary value {value!r}")
    return format(amount, "f")


def _money_from_text(value: str) -> str:
    matches = re.findall(r"£\s*([0-9][0-9,]*(?:\.[0-9]+)?)([km]?)\b", value, flags=re.IGNORECASE)
    if len(matches) != 1:
        raise ProcurementDataError("registered source excerpt must contain exactly one sterling amount")
    number, suffix = matches[0]
    multiplier = {"": Decimal("1"), "k": Decimal("1000"), "m": Decimal("1000000")}[suffix.lower()]
    return _money(Decimal(number.replace(",", "")) * multiplier)


def normalize_supplier_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).upper()
    normalized = re.sub(r"[^0-9A-Z]+", " ", normalized)
    return " ".join(normalized.split())


def supplier_name_variants(value: str) -> set[str]:
    normalized = normalize_supplier_name(value)
    variants = {normalized}
    parts = normalized.split()
    if parts and parts[-1] in LEGAL_SUFFIXES:
        variants.add(" ".join(parts[:-1]))
    return variants


def identifier_evidence(
    payment_scheme: str | None,
    payment_value: str | None,
    notice_scheme: str | None,
    notice_value: str | None,
) -> dict[str, Any]:
    payment_normalized = payment_value.strip().upper() if payment_value else None
    notice_normalized = notice_value.strip().upper() if notice_value else None
    if payment_scheme and notice_scheme and payment_scheme == notice_scheme and payment_normalized and notice_normalized:
        if payment_normalized == notice_normalized:
            return {"tier": "A", "result": "same_authoritative_identifier", "contradiction": False}
        return {"tier": None, "result": "different_authoritative_identifier", "contradiction": True}
    return {"tier": "D", "result": "no_same_scheme_identifier", "contradiction": False}


def _release_document_url(release: dict[str, Any]) -> str | None:
    candidates: list[dict[str, Any]] = []
    candidates.extend((release.get("tender") or {}).get("documents") or [])
    for award in release.get("awards") or []:
        candidates.extend(award.get("documents") or [])
    for contract in release.get("contracts") or []:
        candidates.extend(contract.get("documents") or [])
    for document in candidates:
        if document.get("id") == release.get("id") and document.get("url"):
            return str(document["url"])
    return None


def _party_observation(
    source: dict[str, Any], release: dict[str, Any], notice_key: str, party: dict[str, Any], index: int
) -> dict[str, Any]:
    identifier = party.get("identifier") or {}
    identifier_scheme = identifier.get("scheme")
    identifier_value = identifier.get("id")
    if identifier_scheme and identifier_value:
        identifier_status = "typed"
    elif identifier_value:
        identifier_status = "scheme_missing"
    else:
        identifier_status = "missing"
    observation = {
        "organisation_observation_id": f"{source['id']}:{release['id']}:{party.get('id', index)}",
        "source_capture_id": source["id"],
        "source_system": source["source_system"],
        "notice_key": notice_key,
        "release_id": release["id"],
        "party_id": party.get("id"),
        "party_id_scope": "release",
        "name": party.get("name"),
        "legal_name": identifier.get("legalName"),
        "roles": sorted(str(role) for role in party.get("roles", [])),
        "identifier_scheme": identifier_scheme,
        "identifier_value": str(identifier_value) if identifier_value is not None else None,
        "identifier_status": identifier_status,
        "source_pointer": f"/records/0/releases/{release['_source_index']}/parties/{index}",
    }
    return observation


def _extract_monetary_observation(
    source: dict[str, Any], config: dict[str, Any], document: dict[str, Any]
) -> dict[str, Any]:
    release_id = config.get("release_id")
    source_pointer = str(config["source_pointer"])
    full_pointer = source_pointer
    ocid: str | None = None
    notice_key: str
    release_date: str | None = None
    if source["source_system"] == "find-a-tender":
        record = document["records"][0]
        ocid = str(record["ocid"])
        releases = record["releases"]
        matches = [(index, release) for index, release in enumerate(releases) if release.get("id") == release_id]
        if len(matches) != 1:
            raise ProcurementDataError(f"expected one release {release_id!r} in source {source['id']!r}")
        release_index, release = matches[0]
        container = release
        full_pointer = f"/records/0/releases/{release_index}{source_pointer}"
        notice_key = f"find-a-tender:{ocid}:{release_id}"
        release_date = release.get("date")
    else:
        container = document
        notice_id = str(document["id"])
        version = document.get("notice", {}).get("version")
        notice_key = f"contracts-finder:{notice_id}:version-{version}"
        release_id = f"{notice_id}-v{version}"
        release_date = document.get("notice", {}).get("publishedDate")

    raw_value = _pointer(container, source_pointer)
    if "source_text_contains" in config:
        if not isinstance(raw_value, str) or str(config["source_text_contains"]) not in raw_value:
            raise ProcurementDataError(f"source text for {config['id']!r} does not contain the registered excerpt")
        source_excerpt = str(config["source_text_contains"])
        amount = _money_from_text(source_excerpt)
    else:
        field = config.get("amount_field")
        if field is not None:
            if not isinstance(raw_value, dict) or field not in raw_value:
                raise ProcurementDataError(f"registered amount field for {config['id']!r} is absent")
            raw_amount = raw_value[field]
            full_pointer = f"{full_pointer}/{field}"
            source_currency = raw_value.get("currency")
            if source_currency is not None and source_currency != config["currency"]:
                raise ProcurementDataError(f"currency mismatch for {config['id']!r}")
        else:
            raw_amount = raw_value
        amount = _money(raw_amount)
        source_excerpt = None
    if amount != _money(config["expected_amount"]):
        raise ProcurementDataError(f"amount mismatch for {config['id']!r}")

    return {
        "monetary_observation_id": config["id"],
        "source_capture_id": source["id"],
        "source_system": source["source_system"],
        "notice_key": notice_key,
        "ocid": ocid,
        "release_id": release_id,
        "release_date": release_date,
        "value_type": config["value_type"],
        "amount": amount,
        "currency": config["currency"],
        "vat_basis": config["vat_basis"],
        "scope_type": config["scope_type"],
        "scope_id": str(config["scope_id"]),
        "source_pointer": full_pointer,
        "source_excerpt": source_excerpt,
        "authority": "observed",
        "commercial_event_id": config.get("commercial_event_id"),
        "aggregation_policy": "do_not_sum_across_observations",
        "is_payment": False,
    }


def _parse_find_tender(
    source: dict[str, Any], document: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    records = document.get("records")
    if not isinstance(records, list) or len(records) != 1:
        raise ProcurementDataError(f"Find a Tender source {source['id']!r} must contain exactly one record")
    record = records[0]
    if record.get("ocid") != source.get("expected_ocid"):
        raise ProcurementDataError(f"unexpected OCID in source {source['id']!r}")
    releases = record.get("releases")
    if not isinstance(releases, list):
        raise ProcurementDataError(f"Find a Tender source {source['id']!r} has no releases")
    release_ids = [release.get("id") for release in releases]
    if release_ids != list(source.get("expected_release_ids", [])):
        raise ProcurementDataError(f"release sequence changed in source {source['id']!r}")

    notices: list[dict[str, Any]] = []
    organisations: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    for release_index, original_release in enumerate(releases):
        release = {**original_release, "_source_index": release_index}
        release_id = str(release["id"])
        ocid = str(record["ocid"])
        notice_key = f"find-a-tender:{ocid}:{release_id}"
        notices.append(
            {
                "notice_key": notice_key,
                "source_capture_id": source["id"],
                "source_system": source["source_system"],
                "source_notice_id": release_id,
                "ocid": ocid,
                "release_id": release_id,
                "release_date": release.get("date"),
                "tags": sorted(str(tag) for tag in release.get("tag", [])),
                "title": (release.get("tender") or {}).get("title"),
                "buyer_party_id": (release.get("buyer") or {}).get("id"),
                "human_url": _release_document_url(release),
                "version": None,
            }
        )
        for party_index, party in enumerate(release.get("parties") or []):
            organisations.append(_party_observation(source, release, notice_key, party, party_index))
        for award_index, award in enumerate(release.get("awards") or []):
            for supplier_index, supplier in enumerate(award.get("suppliers") or []):
                relationships.append(
                    {
                        "relationship_type": "award_supplier",
                        "source_capture_id": source["id"],
                        "notice_key": notice_key,
                        "release_id": release_id,
                        "from_type": "award",
                        "from_id": str(award.get("id")),
                        "to_type": "party",
                        "to_id": str(supplier.get("id")),
                        "source_pointer": (
                            f"/records/0/releases/{release_index}/awards/{award_index}/suppliers/{supplier_index}"
                        ),
                    }
                )
        for contract_index, contract in enumerate(release.get("contracts") or []):
            if contract.get("awardID") is not None:
                relationships.append(
                    {
                        "relationship_type": "contract_award",
                        "source_capture_id": source["id"],
                        "notice_key": notice_key,
                        "release_id": release_id,
                        "from_type": "contract",
                        "from_id": str(contract.get("id")),
                        "to_type": "award",
                        "to_id": str(contract["awardID"]),
                        "source_pointer": f"/records/0/releases/{release_index}/contracts/{contract_index}/awardID",
                    }
                )
        release_documents: list[tuple[str, int, dict[str, Any]]] = []
        for index, item in enumerate((release.get("tender") or {}).get("documents") or []):
            release_documents.append(("tender", index, item))
        for award_index, award in enumerate(release.get("awards") or []):
            for index, item in enumerate(award.get("documents") or []):
                release_documents.append((f"awards/{award_index}", index, item))
        for contract_index, contract in enumerate(release.get("contracts") or []):
            for index, item in enumerate(contract.get("documents") or []):
                release_documents.append((f"contracts/{contract_index}", index, item))
        for owner, document_index, item in release_documents:
            documents.append(
                {
                    "source_capture_id": source["id"],
                    "notice_key": notice_key,
                    "release_id": release_id,
                    "document_id": item.get("id"),
                    "document_type": item.get("documentType"),
                    "url": item.get("url"),
                    "format": item.get("format"),
                    "source_pointer": (
                        f"/records/0/releases/{release_index}/{owner}/documents/{document_index}"
                    ),
                }
            )
    return notices, organisations, relationships, documents


def _parse_contracts_finder(
    source: dict[str, Any], document: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    notice_id = str(document.get("id"))
    notice = document.get("notice")
    if notice_id != source.get("expected_notice_id") or not isinstance(notice, dict) or notice.get("id") != notice_id:
        raise ProcurementDataError(f"unexpected Contracts Finder notice identity in source {source['id']!r}")
    version = notice.get("version")
    if version != source.get("expected_version") or notice.get("parentId") != source.get("expected_parent_id"):
        raise ProcurementDataError(f"unexpected Contracts Finder version or parent in source {source['id']!r}")
    notice_key = f"contracts-finder:{notice_id}:version-{version}"
    notices = [
        {
            "notice_key": notice_key,
            "source_capture_id": source["id"],
            "source_system": source["source_system"],
            "source_notice_id": notice_id,
            "ocid": None,
            "release_id": f"{notice_id}-v{version}",
            "release_date": notice.get("publishedDate"),
            "tags": ["award", "contract"],
            "title": notice.get("title"),
            "buyer_party_id": notice.get("organisationName"),
            "human_url": source.get("human_url"),
            "version": version,
        }
    ]
    organisations = [
        {
            "organisation_observation_id": f"{source['id']}:{notice_id}:buyer",
            "source_capture_id": source["id"],
            "source_system": source["source_system"],
            "notice_key": notice_key,
            "release_id": f"{notice_id}-v{version}",
            "party_id": notice.get("organisationName"),
            "party_id_scope": "notice",
            "name": notice.get("organisationName"),
            "legal_name": notice.get("organisationName"),
            "roles": ["buyer"],
            "identifier_scheme": None,
            "identifier_value": None,
            "identifier_status": "missing",
            "source_pointer": "/notice/organisationName",
        }
    ]
    relationships: list[dict[str, Any]] = []
    if notice.get("parentId"):
        relationships.append(
            {
                "relationship_type": "replaces_notice",
                "source_capture_id": source["id"],
                "notice_key": notice_key,
                "release_id": f"{notice_id}-v{version}",
                "from_type": "notice",
                "from_id": notice_id,
                "to_type": "notice",
                "to_id": str(notice["parentId"]),
                "source_pointer": "/notice/parentId",
            }
        )
    for award_index, award in enumerate(document.get("awards") or []):
        supplier_id = f"award-{award.get('id')}-supplier"
        duns = award.get("dunsNumber")
        organisations.append(
            {
                "organisation_observation_id": f"{source['id']}:{notice_id}:{supplier_id}",
                "source_capture_id": source["id"],
                "source_system": source["source_system"],
                "notice_key": notice_key,
                "release_id": f"{notice_id}-v{version}",
                "party_id": supplier_id,
                "party_id_scope": "notice",
                "name": award.get("supplierName"),
                "legal_name": award.get("supplierName"),
                "roles": ["supplier"],
                "identifier_scheme": "DUNS" if duns else None,
                "identifier_value": str(duns) if duns else None,
                "identifier_status": "typed" if duns else "missing",
                "source_pointer": f"/awards/{award_index}",
            }
        )
        relationships.append(
            {
                "relationship_type": "award_supplier",
                "source_capture_id": source["id"],
                "notice_key": notice_key,
                "release_id": f"{notice_id}-v{version}",
                "from_type": "award",
                "from_id": str(award.get("id")),
                "to_type": "party",
                "to_id": supplier_id,
                "source_pointer": f"/awards/{award_index}/supplierName",
            }
        )
    documents = []
    for index, item in enumerate(document.get("additionalDetails") or []):
        if item.get("dataType") != "Attachment":
            continue
        documents.append(
            {
                "source_capture_id": source["id"],
                "notice_key": notice_key,
                "release_id": f"{notice_id}-v{version}",
                "document_id": item.get("id"),
                "document_type": "contract_attachment",
                "url": None,
                "filename": item.get("filename"),
                "format": item.get("mimeType"),
                "source_pointer": f"/additionalDetails/{index}",
            }
        )
    return notices, organisations, relationships, documents


def _source_capture(source: dict[str, Any], document: dict[str, Any], observed_on: Any) -> dict[str, Any]:
    capture = {
        "source_capture_id": source["id"],
        "source_system": source["source_system"],
        "source_family": source["source_family"],
        "source_url": source["source_url"],
        "observed_on": observed_on,
        "media_type": source["media_type"],
        "bytes": int(source["bytes"]),
        "sha256": source["sha256"],
    }
    if source["source_system"] == "find-a-tender":
        capture["package_metadata"] = {
            key: document.get(key)
            for key in (
                "uri",
                "publishedDate",
                "publisher",
                "license",
                "publicationPolicy",
                "version",
                "extensions",
                "packages",
            )
        }
    else:
        capture["api_version"] = 2
    return capture


def _payment_identifier(vat: Any) -> tuple[str | None, str | None, str]:
    if vat is None or not str(vat).strip():
        return None, None, "missing"
    value = str(vat).strip()
    if set(value) <= {"0"}:
        return None, None, "invalid_or_placeholder"
    return "GB-VAT", value, "present"


def _candidate_rows(
    payment_path: Path,
    payment_release: dict[str, Any],
    organisations: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    matching_release_ids: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    awarded_parties = {
        (relationship["notice_key"], relationship["to_id"])
        for relationship in relationships
        if relationship["relationship_type"] == "award_supplier"
    }
    eligible = [
        organisation
        for organisation in organisations
        if organisation["release_id"] in matching_release_ids
        and "supplier" in organisation["roles"]
        and (organisation["notice_key"], organisation["party_id"]) in awarded_parties
    ]
    connection = duckdb.connect(":memory:")
    try:
        payment_groups = connection.execute(
            """
            SELECT supplier, vat_registration_number,
                   list(observation_id ORDER BY observation_id) AS observation_ids,
                   count(*) AS row_count
            FROM read_parquet(?)
            WHERE entity = 'NHS England'
            GROUP BY supplier, vat_registration_number
            ORDER BY supplier, vat_registration_number NULLS FIRST
            """,
            [str(payment_path)],
        ).fetchall()
    finally:
        connection.close()

    candidates: list[dict[str, Any]] = []
    sets: dict[str, list[str]] = defaultdict(list)
    for supplier, vat, observation_ids, row_count in payment_groups:
        payment_variants = supplier_name_variants(str(supplier))
        for organisation in eligible:
            notice_name = organisation.get("name")
            if not notice_name:
                continue
            notice_variants = supplier_name_variants(str(notice_name))
            shared = sorted(payment_variants & notice_variants)
            if not shared:
                continue
            payment_scheme, payment_value, payment_identifier_status = _payment_identifier(vat)
            evidence = identifier_evidence(
                payment_scheme,
                payment_value,
                organisation.get("identifier_scheme"),
                organisation.get("identifier_value"),
            )
            decision = "rejected" if evidence["contradiction"] else "accepted" if evidence["tier"] == "A" else "needs_review"
            payment_key = hashlib.sha256(
                _canonical_json(
                    {
                        "payment_release": payment_release["id"],
                        "supplier": supplier,
                        "vat_registration_number": vat,
                    }
                )
            ).hexdigest()
            candidate_id = hashlib.sha256(
                _canonical_json(
                    {
                        "payment_key": payment_key,
                        "organisation_observation_id": organisation["organisation_observation_id"],
                        "rule_version": MATCH_RULE_VERSION,
                    }
                )
            ).hexdigest()
            candidate = {
                "candidate_id": candidate_id,
                "relation_type": "payment_supplier_to_organisation",
                "payment_supplier_key": payment_key,
                "payment_release_id": payment_release["id"],
                "payment_release_sha256": payment_release["sha256"],
                "payment_observation_ids": list(observation_ids),
                "payment_row_count": int(row_count),
                "supplier_text_raw": str(supplier),
                "supplier_text_normalized": normalize_supplier_name(str(supplier)),
                "payment_identifier_scheme": payment_scheme,
                "payment_identifier_value": payment_value,
                "payment_identifier_status": payment_identifier_status,
                "organisation_observation_id": organisation["organisation_observation_id"],
                "notice_key": organisation["notice_key"],
                "notice_release_id": organisation["release_id"],
                "notice_party_id": organisation["party_id"],
                "notice_supplier_name": notice_name,
                "notice_supplier_name_normalized": normalize_supplier_name(str(notice_name)),
                "notice_identifier_scheme": organisation["identifier_scheme"],
                "notice_identifier_value": organisation["identifier_value"],
                "name_comparison": "exact_normalized_or_legal_suffix_variant",
                "shared_name_variants": shared,
                "identifier_evidence": evidence,
                "evidence_tier": evidence["tier"],
                "decision": decision,
                "candidate_generation_rule": MATCH_RULE_VERSION,
                "normalization_version": NAME_NORMALIZATION_VERSION,
                "contract_attribution": "not_asserted",
                "notice_value_is_not_payment": True,
            }
            candidates.append(candidate)
            sets[payment_key].append(candidate_id)

    candidate_sets = [
        {
            "payment_supplier_key": payment_key,
            "candidate_ids": sorted(candidate_ids),
            "state": "single_candidate" if len(candidate_ids) == 1 else "ambiguous",
        }
        for payment_key, candidate_ids in sorted(sets.items())
    ]
    candidates.sort(key=lambda item: item["candidate_id"])
    return candidates, candidate_sets


def _derive_release(
    registry: dict[str, Any], registry_path: Path, source_directory: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    release_config = registry["release"]
    payment_config = release_config["payment_release"]
    payment_path = ROOT / str(payment_config["parquet"])
    _verify_file(payment_path, payment_path.stat().st_size, payment_config["sha256"])
    connection = duckdb.connect(":memory:")
    try:
        payment_rows, payment_total = connection.execute(
            "SELECT count(*), sum(amount_gbp) FROM read_parquet(?)",
            [str(payment_path)],
        ).fetchone()
    finally:
        connection.close()

    captures: list[dict[str, Any]] = []
    notices: list[dict[str, Any]] = []
    organisations: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    monetary_observations: list[dict[str, Any]] = []
    for source in registry["sources"]:
        path = source_path(source, source_directory)
        document = json.loads(path.read_bytes())
        captures.append(_source_capture(source, document, release_config["observed_on"]))
        if source["source_system"] == "find-a-tender":
            parsed = _parse_find_tender(source, document)
        else:
            parsed = _parse_contracts_finder(source, document)
        source_notices, source_organisations, source_relationships, source_documents = parsed
        notices.extend(source_notices)
        organisations.extend(source_organisations)
        relationships.extend(source_relationships)
        documents.extend(source_documents)
        for observation_config in source["monetary_observations"]:
            monetary_observations.append(_extract_monetary_observation(source, observation_config, document))

    matching_release_ids = [str(item) for item in release_config["matching_release_ids"]]
    candidates, candidate_sets = _candidate_rows(
        payment_path,
        payment_config,
        organisations,
        relationships,
        matching_release_ids,
    )
    captures.sort(key=lambda item: item["source_capture_id"])
    notices.sort(key=lambda item: item["notice_key"])
    organisations.sort(key=lambda item: item["organisation_observation_id"])
    relationships.sort(
        key=lambda item: (
            item["source_capture_id"],
            item["release_id"],
            item["relationship_type"],
            item["from_id"],
            item["to_id"],
        )
    )
    documents.sort(key=lambda item: (item["source_capture_id"], item["release_id"], str(item["document_id"])))
    monetary_observations.sort(key=lambda item: item["monetary_observation_id"])
    release = {
        "schema_version": int(release_config["normalization_schema_version"]),
        "release_id": release_config["id"],
        "title": release_config["title"],
        "observed_on": release_config["observed_on"],
        "tool": {"name": "nhse_procurement.py", "version": TOOL_VERSION},
        "registry_sha256": _registry_semantic_sha256(registry),
        "rights": {"status": release_config["rights_status"], "url": release_config["rights_url"]},
        "canonical_payment_release": {
            "id": payment_config["id"],
            "artifact": str(payment_config["parquet"]),
            "sha256": payment_config["sha256"],
            "rows": int(payment_rows),
            "total_gbp": _money(payment_total),
            "mutation_policy": "immutable; procurement enrichment is a separate derivative",
        },
        "match_run": {
            "id": f"{release_config['id']}-match-run-1",
            "matching_release_ids": matching_release_ids,
            "candidate_generation_rule": MATCH_RULE_VERSION,
            "normalization_version": NAME_NORMALIZATION_VERSION,
            "organisation_match_does_not_imply_contract_attribution": True,
            "notice_value_is_not_payment": True,
        },
        "source_captures": captures,
        "notices": notices,
        "organisation_observations": organisations,
        "relationships": relationships,
        "documents": documents,
        "monetary_observations": monetary_observations,
        "match_candidate_sets": candidate_sets,
        "match_candidates": candidates,
        "limitations": list(release_config["limitations"]),
    }
    validation = _validation_for(release)
    return release, validation


def _validation_for(release: dict[str, Any]) -> dict[str, Any]:
    relationship_counts: dict[str, int] = defaultdict(int)
    for relationship in release["relationships"]:
        relationship_counts[relationship["relationship_type"]] += 1
    value_counts: dict[str, int] = defaultdict(int)
    for observation in release["monetary_observations"]:
        value_counts[observation["value_type"]] += 1
    decision_counts: dict[str, int] = defaultdict(int)
    for candidate in release["match_candidates"]:
        decision_counts[candidate["decision"]] += 1
    awarded_parties = {
        (relationship["notice_key"], relationship["to_id"])
        for relationship in release["relationships"]
        if relationship["relationship_type"] == "award_supplier"
    }
    organisations = {
        item["organisation_observation_id"]: item for item in release["organisation_observations"]
    }
    candidate_award_gated = all(
        (
            organisations[candidate["organisation_observation_id"]]["notice_key"],
            organisations[candidate["organisation_observation_id"]]["party_id"],
        )
        in awarded_parties
        for candidate in release["match_candidates"]
    )
    replacement_relations = [
        relationship
        for relationship in release["relationships"]
        if relationship["relationship_type"] == "replaces_notice"
    ]
    return {
        "schema_version": 1,
        "release_id": release["release_id"],
        "statistics": {
            "source_captures": len(release["source_captures"]),
            "notices": len(release["notices"]),
            "organisation_observations": len(release["organisation_observations"]),
            "relationships": len(release["relationships"]),
            "relationship_counts": dict(sorted(relationship_counts.items())),
            "documents": len(release["documents"]),
            "monetary_observations": len(release["monetary_observations"]),
            "monetary_observation_counts": dict(sorted(value_counts.items())),
            "match_candidate_sets": len(release["match_candidate_sets"]),
            "match_candidates": len(release["match_candidates"]),
            "match_decision_counts": dict(sorted(decision_counts.items())),
        },
        "invariants": {
            "canonical_payment_release_unchanged": True,
            "notice_values_are_not_payments": all(
                item.get("is_payment") is False and "amount_gbp" not in item
                for item in release["monetary_observations"]
            ),
            "name_only_matches_are_candidates": all(
                item.get("evidence_tier") != "D" or item.get("decision") != "accepted"
                for item in release["match_candidates"]
            ),
            "organisation_matches_do_not_assert_contract_attribution": all(
                item.get("contract_attribution") == "not_asserted" for item in release["match_candidates"]
            ),
            "contracts_finder_replacement_is_not_a_version": (
                len(replacement_relations) == 1
                and replacement_relations[0]["from_id"] != replacement_relations[0]["to_id"]
            ),
            "tenderer_only_parties_excluded_from_award_candidates": candidate_award_gated,
        },
        "limitations": list(release["limitations"]),
    }


def build_release(
    target: Path | None = None,
    registry_path: Path = REGISTRY_PATH,
    source_directory: Path = SOURCE_DIR,
) -> Path:
    registry = load_registry(registry_path)
    target = target or release_path(registry)
    verify_sources(registry, source_directory)
    payment_path = ROOT / str(registry["release"]["payment_release"]["parquet"])
    payment_hash_before = sha256_file(payment_path)
    release, validation = _derive_release(registry, registry_path, source_directory)
    if sha256_file(payment_path) != payment_hash_before:
        raise ProcurementDataError("canonical payment artifact changed while building procurement enrichment")

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        (temporary / "procurement.json").write_bytes(_json_bytes(release))
        (temporary / "validation.json").write_bytes(_json_bytes(validation))
        checksums = "".join(
            f"{sha256_file(temporary / name)}  {name}\n" for name in ("procurement.json", "validation.json")
        )
        (temporary / "checksums.sha256").write_text(checksums, encoding="ascii")
        validate_release(temporary, registry, registry_path=registry_path)
        if target.exists():
            current = {path.name: path.read_bytes() for path in target.iterdir() if path.is_file()}
            rebuilt = {path.name: path.read_bytes() for path in temporary.iterdir() if path.is_file()}
            if current != rebuilt:
                raise ProcurementDataError(
                    f"immutable procurement release {target} already exists with different bytes; use a new release ID"
                )
            return target
        temporary.replace(target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return target


def _expected_monetary_observations(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    expected: dict[str, dict[str, Any]] = {}
    for source in registry["sources"]:
        for config in source["monetary_observations"]:
            if source["source_system"] == "find-a-tender":
                release_id = str(config["release_id"])
                release_index = list(source["expected_release_ids"]).index(config["release_id"])
                notice_key = f"find-a-tender:{source['expected_ocid']}:{release_id}"
                source_pointer = f"/records/0/releases/{release_index}{config['source_pointer']}"
                ocid = source["expected_ocid"]
            else:
                version = source["expected_version"]
                release_id = f"{source['expected_notice_id']}-v{version}"
                notice_key = f"contracts-finder:{source['expected_notice_id']}:version-{version}"
                source_pointer = config["source_pointer"]
                ocid = None
            if config.get("amount_field"):
                source_pointer = f"{source_pointer}/{config['amount_field']}"
            expected[str(config["id"])] = {
                "source_capture_id": source["id"],
                "source_system": source["source_system"],
                "notice_key": notice_key,
                "ocid": ocid,
                "release_id": release_id,
                "value_type": config["value_type"],
                "amount": _money(config["expected_amount"]),
                "currency": config["currency"],
                "vat_basis": config["vat_basis"],
                "scope_type": config["scope_type"],
                "scope_id": str(config["scope_id"]),
                "source_pointer": source_pointer,
                "source_excerpt": config.get("source_text_contains"),
                "authority": "observed",
                "commercial_event_id": config.get("commercial_event_id"),
                "aggregation_policy": "do_not_sum_across_observations",
                "is_payment": False,
            }
    return expected


def _validate_manifest(
    release: dict[str, Any],
    validation: dict[str, Any],
    registry: dict[str, Any],
    registry_path: Path,
) -> None:
    if release.get("schema_version") != 1 or validation.get("schema_version") != 1:
        raise ProcurementDataError("unsupported procurement release schema")
    if release.get("release_id") != registry["release"]["id"] or validation.get("release_id") != release.get("release_id"):
        raise ProcurementDataError("procurement release identity does not match the registry")
    if release.get("registry_sha256") != _registry_semantic_sha256(registry):
        raise ProcurementDataError("procurement release registry digest does not match the registry")
    expected_captures = {
        source["id"]: {
            "source_capture_id": source["id"],
            "source_system": source["source_system"],
            "source_family": source["source_family"],
            "source_url": source["source_url"],
            "observed_on": _jsonable(registry["release"]["observed_on"]),
            "media_type": source["media_type"],
            "bytes": int(source["bytes"]),
            "sha256": source["sha256"],
        }
        for source in registry["sources"]
    }
    capture_ids = [capture.get("source_capture_id") for capture in release.get("source_captures", []) if isinstance(capture, dict)]
    if len(capture_ids) != len(release.get("source_captures", [])) or set(capture_ids) != set(expected_captures):
        raise ProcurementDataError("procurement source captures do not match the registry")
    actual_captures = {
        capture["source_capture_id"]: {
            key: capture.get(key) for key in expected_captures[capture["source_capture_id"]]
        }
        for capture in release.get("source_captures", [])
    }
    if actual_captures != expected_captures:
        raise ProcurementDataError("procurement source captures do not match the registry")
    payment = release.get("canonical_payment_release", {})
    expected_payment = registry["release"]["payment_release"]
    if payment.get("id") != expected_payment["id"] or payment.get("sha256") != expected_payment["sha256"]:
        raise ProcurementDataError("canonical payment identity does not match the procurement registry")
    payment_path = ROOT / str(expected_payment["parquet"])
    if sha256_file(payment_path) != expected_payment["sha256"]:
        raise ProcurementDataError("canonical payment artifact does not match its registered digest")

    notice_keys = [notice["notice_key"] for notice in release.get("notices", [])]
    if len(notice_keys) != len(set(notice_keys)):
        raise ProcurementDataError("procurement release contains duplicate notice keys")
    expected_notice_keys = {
        f"find-a-tender:{source['expected_ocid']}:{release_id}"
        for source in registry["sources"]
        if source["source_system"] == "find-a-tender"
        for release_id in source["expected_release_ids"]
    }
    expected_notice_keys.update(
        f"contracts-finder:{source['expected_notice_id']}:version-{source['expected_version']}"
        for source in registry["sources"]
        if source["source_system"] == "contracts-finder"
    )
    if set(notice_keys) != expected_notice_keys:
        raise ProcurementDataError("procurement notice identities do not match the registry")
    expected_values = _expected_monetary_observations(registry)
    value_ids = [
        observation.get("monetary_observation_id")
        for observation in release.get("monetary_observations", [])
        if isinstance(observation, dict)
    ]
    if len(value_ids) != len(release.get("monetary_observations", [])) or set(value_ids) != set(expected_values):
        raise ProcurementDataError("procurement monetary observations do not match the registry")
    actual_values = {
        observation["monetary_observation_id"]: {
            key: observation.get(key) for key in expected_values[observation["monetary_observation_id"]]
        }
        for observation in release.get("monetary_observations", [])
    }
    if actual_values != expected_values:
        raise ProcurementDataError("procurement monetary observations do not match the registry")
    for observation in release["monetary_observations"]:
        if observation["value_type"] not in VALUE_TYPES or observation.get("is_payment") is not False:
            raise ProcurementDataError("procurement monetary observation crossed the payment semantic boundary")
        if "amount_gbp" in observation:
            raise ProcurementDataError("procurement monetary observation uses the canonical payment amount field")
    assertion_groups: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for observation in release["monetary_observations"]:
        if observation.get("commercial_event_id"):
            key = (observation["commercial_event_id"], observation["currency"], observation["vat_basis"])
            assertion_groups[key].add(observation["amount"])
    if any(len(values) != 1 for values in assertion_groups.values()):
        raise ProcurementDataError("one commercial event contains inconsistent monetary assertions")
    for candidate in release.get("match_candidates", []):
        if "amount_gbp" in candidate:
            raise ProcurementDataError("match candidate contains a payment amount")
        if candidate.get("contract_attribution") != "not_asserted":
            raise ProcurementDataError("supplier candidate asserts unsupported contract attribution")
        if candidate.get("evidence_tier") == "D" and candidate.get("decision") == "accepted":
            raise ProcurementDataError("name-only candidate was accepted")
    expected_candidates, expected_candidate_sets = _candidate_rows(
        payment_path,
        expected_payment,
        release["organisation_observations"],
        release["relationships"],
        [str(item) for item in registry["release"]["matching_release_ids"]],
    )
    if release.get("match_candidates") != expected_candidates or release.get("match_candidate_sets") != expected_candidate_sets:
        raise ProcurementDataError("procurement match candidates do not reproduce from their payment and notice anchors")
    replacement_relations = [
        relationship
        for relationship in release.get("relationships", [])
        if relationship["relationship_type"] == "replaces_notice"
    ]
    if len(replacement_relations) != 1:
        raise ProcurementDataError("expected one Contracts Finder replacement relationship")
    if replacement_relations[0]["from_id"] == replacement_relations[0]["to_id"]:
        raise ProcurementDataError("Contracts Finder replacement was collapsed into a version")
    replacement_source = next(
        source
        for source in registry["sources"]
        if source["source_system"] == "contracts-finder" and source.get("expected_parent_id")
    )
    if (
        replacement_relations[0]["from_id"] != replacement_source["expected_notice_id"]
        or replacement_relations[0]["to_id"] != replacement_source["expected_parent_id"]
    ):
        raise ProcurementDataError("Contracts Finder replacement relationship does not match the registry")
    if validation != _validation_for(release):
        raise ProcurementDataError("procurement validation statistics do not match the release")
    if any(value is not True for value in validation.get("invariants", {}).values()):
        raise ProcurementDataError("procurement release has an unsatisfied validation invariant")


def validate_release(
    target: Path = DATA_DIR,
    registry: dict[str, Any] | None = None,
    *,
    registry_path: Path = REGISTRY_PATH,
    source_directory: Path = SOURCE_DIR,
    verify_against_sources: bool = False,
) -> None:
    registry = registry or load_registry(registry_path)
    expected_files = {"checksums.sha256", "procurement.json", "validation.json"}
    actual_entries = {path.name for path in target.iterdir()}
    if actual_entries != expected_files:
        raise ProcurementDataError("procurement release files do not match the expected artifact set")
    checksum_lines = (target / "checksums.sha256").read_text(encoding="ascii").splitlines()
    expected_checksums = {}
    for line in checksum_lines:
        digest, separator, filename = line.partition("  ")
        if not separator or filename not in {"procurement.json", "validation.json"}:
            raise ProcurementDataError("invalid procurement checksum manifest")
        expected_checksums[filename] = digest
    if set(expected_checksums) != {"procurement.json", "validation.json"}:
        raise ProcurementDataError("incomplete procurement checksum manifest")
    pinned_artifacts = registry["release"].get("expected_artifacts")
    if pinned_artifacts is not None and expected_checksums != pinned_artifacts:
        raise ProcurementDataError("procurement artifact digests do not match the registry")
    for filename, digest in expected_checksums.items():
        if sha256_file(target / filename) != digest:
            raise ProcurementDataError(f"checksum mismatch for {filename}")
    try:
        release = json.loads((target / "procurement.json").read_text(encoding="utf-8"))
        validation = json.loads((target / "validation.json").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ProcurementDataError(f"invalid procurement release JSON: {error}") from error
    if not isinstance(release, dict) or not isinstance(validation, dict):
        raise ProcurementDataError("procurement release artifacts must contain JSON objects")
    try:
        _validate_manifest(release, validation, registry, registry_path)
    except ProcurementDataError:
        raise
    except (AttributeError, IndexError, KeyError, StopIteration, TypeError, ValueError) as error:
        raise ProcurementDataError(f"malformed procurement release structure: {error}") from error
    if verify_against_sources:
        verify_sources(registry, source_directory)
        expected_release, expected_validation = _derive_release(registry, registry_path, source_directory)
        if release != _jsonable(expected_release) or validation != _jsonable(expected_validation):
            raise ProcurementDataError("procurement release does not match the registered source captures")
