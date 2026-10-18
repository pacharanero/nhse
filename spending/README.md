# NHS England spending data

This directory contains the source registries, typed top-level financial figures, editorial spending timeline, reproducible payment pipeline and capture-pinned procurement-enrichment pipeline. Read `../spec/spending-data.md` before adding a source or changing a normalized schema.

## Build a registered release

```sh
uv sync --locked
s/fetch-spending-data --source 2024-payments-over-25000
s/build-spending-data --source 2024-payments-over-25000
uv run python nhse_spending.py validate --source 2024-payments-over-25000
```

Verified workbooks are written to the ignored `spending/sources/` directory. The 2024 release combines twelve current monthly workbooks in `spending/data/2024-payments-over-25000/`; its correction artifacts compare the superseded July workbook with its replacement. The 2023 release (`--source 2023-payments-over-25000`) combines the twelve calendar-year 2023 workbooks the same way, with no superseded revision. The smaller September 2025 release remains available as `--source 2025-09-payments-over-25000`, which is also the command default.

Use `s/fetch-spending-data --archive --source <id>` to fetch registered archive captures instead of live NHS England URLs. Superseded revision inputs are always recovered from their archive. Every route must produce the exact SHA-256 in `data-sources.yaml`.

## Build the procurement fixtures

```sh
s/fetch-procurement-data --source find-tender-fdp
s/fetch-procurement-data --source find-tender-transition-products
s/fetch-procurement-data --source find-tender-cass-modification
s/fetch-procurement-data --source contracts-finder-fdp-original
s/fetch-procurement-data --source contracts-finder-fdp-replacement
s/build-procurement-data
uv run python nhse_spending.py procurement-validate
```

`procurement-sources.yaml` registers five exact official captures: three Find a Tender record packages and both Contracts Finder FDP publications. The captures remain ignored under `spending/sources/procurement/`; the committed immutable derivative in `data/procurement-notice-fixtures-2026-10-17/` retains their digests, notice and release identities, typed non-payment values, source relationships and review-only supplier candidates. It never writes procurement values or matches into the canonical payment rows. The registered APIs are mutable, so retain the verified local captures: a clean refetch is not guaranteed until durable archive URLs with matching bytes are registered.

## Query with DuckDB

No import or database file is required:

```sh
duckdb -c "SELECT source_period, count(*) AS payments, sum(amount_gbp) AS total_gbp FROM read_parquet('spending/data/2024-payments-over-25000/payments.parquet') GROUP BY source_period ORDER BY source_period"
```

Filter `entity = 'NHS England'` for the NHS England-parent view. Do not silently exclude CSU rows from whole-workbook totals. `source_period` and `source_id` identify each current monthly workbook in schema v2.

## Add a source

Add immutable source metadata, archive and rights evidence URLs, SHA-256, exact byte length, workbook schema and independently checked reconciliation totals to `data-sources.yaml`. The converter fails closed on schema drift; a structurally different workbook needs an explicit adapter rather than permissive parsing. Run `s/test` and perform two clean builds before treating a new release as deterministic.

## Refresh the historical census

```sh
uv run python nhse_spending.py inventory --observed-on YYYY-MM-DD
```

The command follows the canonical NHS England index and every linked year collection, caches raw files under ignored `spending/sources/inventory/`, and regenerates `historical-schema-census.json`. Review URL, digest, coverage and schema changes before committing the census. The current snapshot records 144 logical file-link occurrences representing 143 unique URLs, 17 physical workbook/CSV layouts and six column profiles.
