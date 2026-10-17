# Spec: NHS England spending data

## Purpose

Turn NHS England financial publications from technically public spreadsheets and PDFs into accurately bounded, source-traceable data that can be queried offline with ordinary tools. This bulk factual layer is separate from the selected editorial events in `spending/entries/`; findings derived from the bulk data may later become sourced timeline entries.

## Accounting boundary

"The NHS budget" is not one number. For 2025/26 the comparable NHS England group budget-to-actual pair is the section 223E revenue resource limit of £203.813 billion and audited total net expenditure of £202.087763 billion. This group comprises NHS England, 42 integrated care boards and Supply Chain Coordination Ltd, but excludes NHS trusts and foundation trusts. The £207.963 billion provider-inclusive NHS revenue limit and DHSC's £210.675916 billion Parliamentary resource DEL answer different questions and must not be substituted for the NHS England group figure.

The typed figures and exact source references live in `spending/top-level-finances.yaml`. Amounts are integer pounds; boundaries, measures and intended uses are explicit so unlike totals cannot be silently compared.

## First detailed source

The first source adapter targets NHS England's September 2025 payments-over-£25,000 workbook. It is deliberately bounded but exercises the main ingestion risks: one sheet whose formatting extends to row 4,428 despite only 2,515 non-empty data rows, five published entities, 239 negative amounts, 584 absent VAT identifiers and mixed string/numeric identifiers. The immutable source facts and expected reconciliation totals live in `spending/data-sources.yaml`.

The payments publication is not a general ledger and does not reconcile one-for-one to annual accrual accounts. It is a transaction-level transparency series above a publication threshold. Supplier payments, allocations, annual accounts, management reports and procurement notices remain distinct datasets with distinct financial meanings.

## Release format

Each source release builds into:

- `payments.parquet` - the canonical normalized analytical derivative, typed with exact decimal money and date values, ZSTD level 3 compression and fixed row-group sizing.
- `payments.csv.gz` - deterministic UTF-8 compatibility export from the same normalized rows.
- `datapackage.json` - source, schema, rights, limitations and artifact metadata.
- `validation.json` - row counts, signed totals, entity counts, date bounds and invariant results.
- `checksums.sha256` - exact artifact identities.

DuckDB queries Parquet directly, so a mutable `.duckdb` database is not a publication format. SQLite may be added later only for a concrete lookup or full-text-search use case. NDJSON is useful for irregular joined documents such as SNOMED CT concepts, but adds repeated keys and weaker typing to this regular table, so it is not a default spending release.

Downloaded workbooks are ignored by Git. Code, pinned dependencies, source registries, schemas, tests and the first small normalized release are committed together so its provenance remains reviewable. If the historical corpus grows beyond a practical Git footprint, later immutable artifacts should move to GitHub Releases or content-addressed object/OCI storage without changing their Data Package identities.

## Normalized payment schema

Every row preserves both analytical values and workbook provenance:

| Column | Type | Meaning |
|---|---|---|
| `observation_id` | string | SHA-256 identity derived from schema version, source digest, sheet, physical row and canonical source-row values |
| `department_family` | string | Published department family |
| `entity` | string | Published paying entity; filter `NHS England` for the parent view |
| `transaction_date` | date | Published transaction date |
| `expense_type` | string | Published expense type |
| `expense_area` | string | Published expense area |
| `supplier` | string | Published supplier text, not silently entity-resolved |
| `transaction_number` | string | Published transaction number preserved as an identifier |
| `amount_gbp` | decimal(18,2) | Signed amount in pounds at the source report's two-decimal display precision; negatives are retained |
| `source_amount_raw` | string | Exact numeric value exposed by the XLSX parser before two-decimal report normalization |
| `currency` | string | `GBP` for this source |
| `vat_registration_number` | nullable string | Published VAT identifier without numeric interpretation |
| `redaction_status` | string | `none` or `source_removed` |
| `source_sha256` | string | Exact source workbook digest |
| `source_file` | string | Stable source filename |
| `source_sheet` | string | Workbook sheet name |
| `source_row` | int32 | One-based physical workbook row |

Unknown sheets, columns, dates, formulas, Excel errors or value types fail closed. The parser skips only fully empty formatted rows. Three September cells contain higher-precision binary values beneath an Excel format that displays two decimal places; `amount_gbp` applies the registered two-decimal scale with explicit half-up rounding while `source_amount_raw` preserves the parser-visible value. The independently checked £1,082,583,670.12 workbook total reconciles to the row-wise displayed amounts. Supplier normalization and procurement matching are separate, reviewable enrichment layers rather than destructive parsing steps.

## Provenance and reproducibility

The design borrows `sct`'s stable intermediate and source-verification principles and `ods`'s deterministic Parquet, embedded Data Package provenance and release identity. Source version, schema version, dataset version, tool version, normalized content fingerprint and exact artifact SHA-256 are separate identities. Build timestamps, machine names and absolute paths do not enter deterministic artifacts.

The source workbook is downloaded to a same-directory temporary file, checked against its committed byte length and SHA-256, synced and atomically renamed. A failed refresh cannot replace a previously verified source. Repeated clean builds from the same source and dependency lock must produce byte-identical release files.

## Rights

The historical [data.gov.uk record](https://www.data.gov.uk/dataset/b07015fb-4eb8-4c5c-93ad-d5600bd53f89/payments-over-25k) ([archive](https://web.archive.org/web/20261017133823/https://www.data.gov.uk/dataset/b07015fb-4eb8-4c5c-93ad-d5600bd53f89/payments-over-25k)) identifies the payments-over-£25,000 dataset as [Open Government Licence v3](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) data ([archive](https://web.archive.org/web/20261017133849/https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)). On 17 October 2026 the project owner approved redistribution of the normalized release, relying on that OGL designation and a fair-use/fair-dealing determination. `spending/data-sources.yaml` records the decision, basis and date. It covers the normalized release and does not imply permission to mirror every raw workbook.

## Roadmap

Legend: `[x]` done, `[~]` in progress, `[ ]` not started

- [x] **D1 - Define the 2025/26 NHS England budget and outturn boundary** with exact primary-source references and distinguish DHSC and provider-inclusive controls.
- [x] **D2 - Register the September 2025 payments source** with archived landing, collection and workbook URLs, digest, schema and reconciliation totals.
- [x] **D3 - Build the first deterministic Parquet and CSV.gz release** with row-level provenance, tests and DuckDB validation.
- [x] **D4 - Confirm redistribution rights and publish the first immutable data release.** The normalized September 2025 Parquet and CSV.gz release is committed with Data Package metadata and checksums; the raw workbook remains local.
- [ ] **D5 - Ingest all twelve 2024 workbooks**, including the corrected July file, and produce a revision diff.
- [ ] **D6 - Census all historical schemas before backfilling 2013/14 onward.**
- [ ] **D7 - Add procurement-notice enrichment** without treating estimated or awarded values as payments.
- [ ] **D8 - Automate source-inventory monitoring** so newly published, removed and corrected workbooks produce reviewable registry changes rather than silent gaps.
- [ ] **D9 - Add multi-period analytical views** with explicit coverage and comparability metadata; never turn an absent month into zero spending.
- [ ] **D10 - Define the large-corpus release threshold and migration path** from Git to GitHub Releases or content-addressed storage while preserving artifact identities and links.
