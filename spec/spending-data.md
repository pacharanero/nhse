# Spec: NHS England spending data

## Purpose

Turn NHS England financial publications from technically public spreadsheets and PDFs into accurately bounded, source-traceable data that can be queried offline with ordinary tools. This bulk factual layer is separate from the selected editorial events in `spending/entries/`; findings derived from the bulk data may later become sourced timeline entries.

## Accounting boundary

"The NHS budget" is not one number. For 2025/26 the comparable NHS England group budget-to-actual pair is the section 223E revenue resource limit of £203.813 billion and audited total net expenditure of £202.087763 billion. This group comprises NHS England, 42 integrated care boards and Supply Chain Coordination Ltd, but excludes NHS trusts and foundation trusts. The £207.963 billion provider-inclusive NHS revenue limit and DHSC's £210.675916 billion Parliamentary resource DEL answer different questions and must not be substituted for the NHS England group figure.

The typed figures and exact source references live in `spending/top-level-finances.yaml`. Amounts are integer pounds; boundaries, measures and intended uses are explicit so unlike totals cannot be silently compared.

## First detailed source

The first source adapter targets NHS England's September 2025 payments-over-£25,000 workbook. It is deliberately bounded but exercises the main ingestion risks: one sheet whose formatting extends to row 4,428 despite only 2,515 non-empty data rows, five published entities, 239 negative amounts, 584 absent VAT identifiers and mixed string/numeric identifiers. The second release covers all twelve 2024 workbooks: 51,971 current rows totalling £32,326,771,267.64, with exact monthly reconciliation and the superseded July source retained locally for revision analysis. The immutable source facts and expected totals live in `spending/data-sources.yaml`.

The payments publication is not a general ledger and does not reconcile one-for-one to annual accrual accounts. It is a transaction-level transparency series above a publication threshold. Supplier payments, allocations, annual accounts, management reports and procurement notices remain distinct datasets with distinct financial meanings.

## Release format

Each source release builds into:

- `payments.parquet` - the canonical normalized analytical derivative, typed with exact decimal money and date values, ZSTD level 3 compression and fixed row-group sizing.
- `payments.csv.gz` - deterministic UTF-8 compatibility export from the same normalized rows.
- `datapackage.json` - source, schema, rights, limitations and artifact metadata.
- `validation.json` - row counts, signed totals, entity counts, date bounds and invariant results.
- `checksums.sha256` - exact artifact identities.

Revised sources also produce a deterministic correction summary and compressed row-level diff. The July 2024 diff classifies 3,879 superseded rows as removed and 4,508 corrected rows as added. No rows share the documented candidate key because the superseded file contains June dates and transactions; an independent ordered comparison confirms that its non-VAT fields reproduce the registered June workbook exactly.

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
| `purchase_invoice_number` | nullable string | Published purchase-invoice identifier where the source schema provides it (schema v2) |
| `amount_gbp` | decimal(18,2) | Signed amount in pounds at the source report's two-decimal display precision; negatives are retained |
| `source_amount_raw` | string | Exact numeric value exposed by the XLSX parser before two-decimal report normalization |
| `currency` | string | `GBP` for this source |
| `vat_registration_number` | nullable string | Published VAT identifier without numeric interpretation |
| `redaction_status` | string | `none` or `source_removed` |
| `source_id` | string | Registered workbook identity (schema v2) |
| `source_period` | string | Registered calendar period without inferring absent months (schema v2) |
| `source_sha256` | string | Exact source workbook digest |
| `source_file` | string | Stable source filename |
| `source_sheet` | string | Workbook sheet name |
| `source_row` | int32 | One-based physical workbook row |

Unknown sheets, columns, dates, formulas, Excel errors or value types fail closed. The parser skips only fully empty formatted rows. Schema v1 preserves the already published September 2025 shape; schema v2 adds registered source identity, source period and purchase-invoice identifiers for multi-workbook releases. Three September cells contain higher-precision binary values beneath an Excel format that displays two decimal places; `amount_gbp` applies the registered two-decimal scale with explicit half-up rounding while `source_amount_raw` preserves the parser-visible value. The independently checked £1,082,583,670.12 workbook total reconciles to the row-wise displayed amounts. Supplier normalization and procurement matching are separate, reviewable enrichment layers rather than destructive parsing steps.

### Registered workbook exceptions

The D11 historical backfill (2013/14-2023) encountered several genuine source-data shapes and defects beyond the default parser's strictness. Rather than loosen a shared check, each is a named, per-workbook opt-in field in `data-sources.yaml`'s `workbook` block, used only where explicitly registered:

| Field | Effect |
|---|---|
| `ignore_trailing_columns` | Accepts extra populated columns beyond the registered header count (November 2014's stray reference-code column; January 2022's single-character marker cells in seven trailing columns) |
| `permit_non_integral_purchase_invoice_numbers` | Accepts a decimal value in the Purchase invoice number identifier instead of rejecting it (one June 2020 row) |
| `no_transaction_number_column` | The source has no Transaction number column at all; `transaction_number` is `null` for that workbook's rows (May 2019) |
| `no_vat_registration_number_column` | The source has no VAT registration number column at all; `vat_registration_number` is `null` for that workbook's rows (the 2013/14 fiscal-year workbook, which has a "Comments from NHS England" column instead, not captured as a structured field) |
| `permit_numeric_text_fields` | Accepts a numeric cell (coerced to its literal text) in a field normally required to be text (138 February 2018 rows publish the digit `0` in Expense Area) |
| `excluded_rows` + `excluded_rows_reason` (required together) | Skips exact 1-based physical rows confirmed corrupted at the source, with a published count (`excluded_malformed_rows`) and reason rather than a silent drop (five February 2019 rows where a pasted document-server URL shifted later columns) |

Each flag is scoped to the one workbook it is registered against; building or validating any other workbook without the flag still fails closed on the same anomaly. `transaction_number`'s Parquet column is only written as nullable when at least one row in the release actually has a null value, so adding `no_transaction_number_column` to a new source does not change the physical encoding, byte identity, or validated structure of every other already-published release.

## Provenance and reproducibility

The design borrows `sct`'s stable intermediate and source-verification principles and `ods`'s deterministic Parquet, embedded Data Package provenance and release identity. Source version, schema version, dataset version, tool version, normalized content fingerprint and exact artifact SHA-256 are separate identities. Build timestamps, machine names and absolute paths do not enter deterministic artifacts.

The source workbook is downloaded to a same-directory temporary file, checked against its committed byte length and SHA-256, synced and atomically renamed. A failed refresh cannot replace a previously verified source. Repeated clean builds from the same source and dependency lock must produce byte-identical release files.

`spending/spend-by-year.json` (`s/build-spend-summary`) is a small derived summary - one total per registered year, read from each release's own committed `validation.json` rather than recomputed from Parquet - that drives the "Spend over time" chart on `spending/index.html`. Each year's coverage is an explicit mapping (`nhse_spending.SPEND_SUMMARY_COVERAGE`): full calendar year, partial calendar year with its exact month count, or the non-calendar fiscal year. The chart (`js/spend-chart.js`) renders partial and fiscal-year bars with a hatched fill and dashed outline rather than plotting them as if a full year's total were simply smaller, consistent with D9's "never turn an absent month into zero spending."

`spending/supplier-spend.json` (same `s/build-spend-summary` command, `nhse_spending.build_supplier_spend_summary`) is the equivalent per-supplier derived summary: for every distinct published `supplier` string across all releases, its total rows, total value and a sparse per-year breakdown, grouped directly from each release's own Parquet rather than resolved to a legal entity. The "Search suppliers" tool on `spending/index.html` (`js/supplier-search.js`) matches this raw text by substring only - a company that appears under more than one spelling (an abbreviation, a trading name, a later rebrand) is not merged, the same evidence-tier discipline D7's procurement `match_candidates` already apply to name-only matches. The file is large (published suppliers number in the tens of thousands) so the tool fetches it lazily on first interaction with the search box, not on page load; a `?q=` URL parameter (see `CONTRIBUTING.md`'s "URL querystring convention") pre-runs a search and renders its top result's chart on load, so a finding is a shareable link.

## Historical schema census

`spending/historical-schema-census.json` is the pre-backfill inventory of the canonical publication index as observed on 17 October 2026. It records 144 logical file-link occurrences representing 143 unique source URLs across the 2013/14 direct files and twelve calendar-year collection pages. The duplicate logical occurrence is the 2013/14 Q4 CSV, which is linked from both the landing page and the 2014 collection. Every source record carries its current URL, byte length, SHA-256, detected header, physical workbook sheets and a deterministic schema fingerprint.

The corpus has 17 physical layouts once sheet names and empty auxiliary sheets are distinguished, but only six column profiles. The main ten-column XLSX profile covers 125 occurrences from 2014 through 2024. Separate profiles cover the five Windows-1252 2013/14 CSV links, the combined 2013/14 XLSX, three late-2024 files whose expense headings add “for Report”, nine 2025 files without purchase-invoice numbers, and one May 2019 anomaly without a transaction-number column. Backfill adapters must bind to these observed profiles and continue to reject unregistered drift.

Coverage is explicit. The 2014 collection exposes April through December while the fiscal 2013/14 files cover the earlier transition in a different publication shape. The 2015-2024 calendar collections expose all twelve months. The 2025 collection exposes January through September and records October-December as missing, not zero. Filename revision markers identify December 2014 v2, every 2015 file as v2, January-September 2016 as v2, revised February and March 2018 files, and corrected July 2024; those markers are discovery evidence, not proof of a particular row-level correction.

## Procurement-notice enrichment

Procurement enrichment is an optional derivative, not a mutation of the payment release. `spending/procurement-sources.yaml` registers exact source captures from Find a Tender and Contracts Finder, while `spending/data/procurement-notice-fixtures-2026-10-17/procurement.json` publishes notice releases, release-scoped organisation observations, award-supplier and contract-award relationships, documents, typed monetary observations and payment-supplier candidates. The observation date is part of the immutable release identity. The canonical payment Parquet digest is verified while its row count and signed total are independently queried from that artifact and carried into the derivative.

The first bounded release uses three Find a Tender record packages: the FDP lifecycle, the Transition products framework and the Cass modification. It also uses the Contracts Finder v2 JSON endpoint for the original and replacement FDP publications. The latter remain two GUIDs, each at version 1, connected by `replaces_notice`. Their repeated £182,242,760 values and the Find a Tender contract value share one commercial-event identity and an explicit do-not-sum policy, so independent source assertions cannot be mistaken for three awards.

Every monetary observation has a semantic type, currency, VAT basis, scope, release and exact source pointer. Planning estimates, tender ceilings, framework maxima, awards, contracts, modifications and non-committed forecasts all carry `is_payment: false` and cannot use the canonical `amount_gbp` field. The Cass capture exposes the £10,485 increment and £33,475 modified total but not the original £22,990 as a structured record-package field, so that missing source observation remains a published limitation rather than being silently reconstructed.

Supplier comparison is precision-first. The first match run compares only parties linked from an award in named fixture releases against published 2024 NHS England supplier text. Conservative name normalization generates five review-only candidates covering Palantir, Novartis and Pfizer payment observations. Different identifier schemes, missing or zero-like VAT values, tenderer-only roles and absent names cannot produce an accepted identity. Even an accepted organisation identity would not assert that an individual payment belongs to a procurement or contract.

This first parcel does not complete D7. The Find a Tender package retains extension URLs but the moving extension schemas are not yet frozen, and its exact ignored local captures do not yet have durable archive URLs with matching bytes. Broad bounded-window discovery, cursor provenance, a source-completeness census, durable capture retrieval, reviewed identity decisions and Payments Transparency Register support remain future gates.

## Rights

The historical [data.gov.uk record](https://www.data.gov.uk/dataset/b07015fb-4eb8-4c5c-93ad-d5600bd53f89/payments-over-25k) ([archive](https://web.archive.org/web/20261017133823/https://www.data.gov.uk/dataset/b07015fb-4eb8-4c5c-93ad-d5600bd53f89/payments-over-25k)) identifies the payments-over-£25,000 dataset as [Open Government Licence v3](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) data ([archive](https://web.archive.org/web/20261017133849/https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)). On 17 October 2026 the project owner approved redistribution of the normalized release, relying on that OGL designation and a fair-use/fair-dealing determination. `spending/data-sources.yaml` records the decision, basis and date. It covers the normalized release and does not imply permission to mirror every raw workbook.

## Roadmap

Legend: `[x]` done, `[~]` in progress, `[ ]` not started

- [x] **D1 - Define the 2025/26 NHS England budget and outturn boundary** with exact primary-source references and distinguish DHSC and provider-inclusive controls.
- [x] **D2 - Register the September 2025 payments source** with archived landing, collection and workbook URLs, digest, schema and reconciliation totals.
- [x] **D3 - Build the first deterministic Parquet and CSV.gz release** with row-level provenance, tests and DuckDB validation.
- [x] **D4 - Confirm redistribution rights and publish the first immutable data release.** The normalized September 2025 Parquet and CSV.gz release is committed with Data Package metadata and checksums; the raw workbook remains local.
- [x] **D5 - Ingest all twelve 2024 workbooks**, including the corrected July file, and produce a revision diff. The release contains 51,971 current rows plus a complete 8,387-row added/removed diff against the superseded file recovered from the UK Government Web Archive.
- [x] **D6 - Census all historical schemas before backfilling 2013/14 onward.** The committed census covers 144 logical source occurrences, 17 physical layouts and six column profiles, with exact digests and explicit monthly coverage.
- [~] **D7 - Add procurement-notice enrichment** without treating estimated or awarded values as payments. The first deterministic fixture release establishes the semantic firewall, source relationships and review-only supplier candidates; schema freezing, bounded feed acquisition and reviewed matches remain open.
- [ ] **D8 - Automate source-inventory monitoring** so newly published, removed and corrected workbooks produce reviewable registry changes rather than silent gaps.
- [~] **D9 - Add multi-period analytical views** with explicit coverage and comparability metadata; never turn an absent month into zero spending. The "Spend over time" year-by-year chart and the "Search suppliers" per-supplier tool are both built on this principle, marking every partial, fiscal-year or single-month period explicitly rather than plotting it as a smaller full year. Still open: views below the single-supplier level (by expense type, expense area, or entity over time) and any view that needs more than the already-published per-release/per-supplier totals.
- [ ] **D10 - Define the large-corpus release threshold and migration path** from Git to GitHub Releases or content-addressed storage while preserving artifact identities and links.
- [x] **D11 - Backfill 2013/14 through 2023 into normalized releases**, using the D6 census's 143 catalogued sources and six already-mapped column profiles rather than discovering schemas again. Every calendar year 2014-2023, plus the single combined fiscal-year 2013/14 workbook, is registered, fetched, built and independently validated, bringing total coverage to 809,371 rows and £311.631bn across 2013/14-2024. 2014 is April-December only; January-March 2014 are not published anywhere in the discovered corpus and are recorded as missing, not zero. Five genuine source-data defects and shape variants, confirmed by direct inspection rather than assumed, were each handled with an explicit, reviewed, per-workbook registry opt-in rather than a loosened shared check - see "Registered workbook exceptions" above. The combined fiscal-year 2013/14 workbook was used in preference to its four published quarterly CSVs after confirming by content and row count that they carry the same underlying data in a different format; building a second CSV-reading parser for already-available data was judged disproportionate. Explicit scope decisions, not gaps: every census-flagged revision marker before 2024 (December 2014, all of 2015, January-September 2016, February and March 2018) is published as the current republished file only, without the superseded-file-recovery-and-diff treatment D5 built for July 2024 - consistent with this spec's existing note that those markers are "discovery evidence, not proof of a particular row-level correction," and a larger undertaking than year-by-year registration; recovering and diffing them, if ever wanted, is separate future work, not a backfill defect.
- [ ] **D12 - Harvest Find a Tender's NHS England-scoped OCDS releases in bulk**, extending D7's five individually-registered record-package captures to a bounded, periodic discovery feed, reconciled against whichever payment periods exist using the same name-normalization and review-only evidence-tier boundary as D7's `match_candidates` - never asserting that a notice value is a payment or that a name match is a confirmed identity. Open before this can be built: the exact bulk/search endpoint and its buyer-filter parameter are unverified against the live API - the current registry only proves the per-OCID record-package endpoint works, and D7's Contracts Finder work found the obvious-looking endpoint guess wrong once before. NHS England's organisational identity has changed and merged (NHSX, NHS Digital, predecessor CCGs), so buyer filtering needs an explicit alias list rather than one string match. The date window should start bounded - from NHS England's formation or a chosen recent year - rather than attempt an unbounded historical crawl, following `spec/roadmap.md`'s idempotent-fetcher principle. D12's review-candidate yield is bounded by D11's progress: a notice can only generate a supplier match candidate against payment periods that have actually been ingested, so sequencing D11 alongside or ahead of D12 matters for recall, not just completeness.
