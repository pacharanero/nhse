# NHS England spending data

This directory contains the source registries, typed top-level financial figures, editorial spending timeline, reproducible payment pipeline and capture-pinned procurement-enrichment pipeline. Read `../spec/spending-data.md` before adding a source or changing a normalized schema.

## Build a registered release

```sh
uv sync --locked
s/fetch-spending-data --source 2024-payments-over-25000
s/build-spending-data --source 2024-payments-over-25000
uv run python nhse_spending.py validate --source 2024-payments-over-25000
```

Verified workbooks are written to the ignored `spending/sources/` directory. The 2024 release combines twelve current monthly workbooks in `spending/data/2024-payments-over-25000/`; its correction artifacts compare the superseded July workbook with its replacement. Every calendar year 2014-2023, plus the combined fiscal year 2013/14 workbook, is registered and built the same way (`--source <year>-payments-over-25000`), the result of the D11 historical backfill; see `spending/data/README.md` for each year's exact coverage and any source-level anomalies. The smaller September 2025 release remains available as `--source 2025-09-payments-over-25000`, which is also the command default.

Use `s/fetch-spending-data --archive --source <id>` to fetch registered archive captures instead of live NHS England URLs. Superseded revision inputs are always recovered from their archive. Every route must produce the exact SHA-256 in `data-sources.yaml`.

## Build the spend-over-time chart data

```sh
s/build-spend-summary
```

Regenerates `spend-by-year.json` from every committed release's own `validation.json`, driving the "Spend over time" bar chart on `index.html` (`../js/spend-chart.js`). Each year's coverage (full calendar year, partial calendar year, or fiscal year) is an explicit, reviewed mapping in `nhse_spending.SPEND_SUMMARY_COVERAGE`, not inferred from period strings, so a release can never silently misrepresent as more complete than it is. Run this after building or rebuilding any payments release.

## Build an NHS Digital/HSCIC release

```sh
s/fetch-nhsd-data --source 2013-14-nhsd-spend-information
s/build-nhsd-data --source 2013-14-nhsd-spend-information
uv run python nhse_spending.py nhsd-validate --source 2013-14-nhsd-spend-information
s/build-nhsd-summary
```

`spending/nhsd-data-sources.yaml` registers NHS Digital's (formerly HSCIC's) own pre-merger "spend information" series - ten fiscal years, 2013/14 through 2022/23, each `--source <fiscal-year>-nhsd-spend-information`. This is a **legally and editorially separate corpus** from NHS England's own payments: see "NHS Digital / HSCIC spend information (pre-merger)" in `../spec/spending-data.md` for why, its structurally different schema, and the open TPP-absence finding it surfaces. Every digital.nhs.uk source URL now 404s after the NHS Digital/NHS England merger, so `nhsd-fetch` always downloads from the registered UK Government Web Archive capture; there is no live-vs-archive choice to make. `s/build-nhsd-summary` regenerates `nhsd-spend-by-year.json`, its own chart series on `index.html`, never summed into `spend-by-year.json`'s NHS England totals.

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

Glob across every committed release to search for one supplier across all years. `union_by_name=true` is required because schema v1 releases (currently only September 2025) lack the `source_id`/`source_period`/`purchase_invoice_number` columns schema v2 adds:

```sh
duckdb -c "
SELECT supplier, source_file, count(*) AS payments, sum(amount_gbp) AS total_gbp
FROM read_parquet('spending/data/*-payments-over-25000/payments.parquet', union_by_name = true)
WHERE supplier ILIKE '%phoenix partnership%'
GROUP BY supplier, source_file
ORDER BY source_file
"
```

Match on `supplier` as published, not a resolved legal entity - the same company can appear under more than one spelling (an all-caps abbreviation, a trading name, a later rebrand) with no guarantee the registry links them. Treat a second plausible name as a candidate to check by hand, not as the same row count. The published site's "Search suppliers" tool on `index.html` (`spending/supplier-spend.json`, built by `s/build-spend-summary`) runs the same raw-text, no-entity-resolution substring search pre-aggregated by year, for anyone who would rather not run DuckDB themselves.

This `*-payments-over-25000/payments.parquet` glob deliberately does not match NHS Digital/HSCIC's own pre-merger releases, which use different artifact names (`nhsd-spend.parquet`) precisely so they are never silently pulled into an NHS England cross-year query. Query them explicitly:

```sh
duckdb -c "
SELECT source_period, supplier, count(*) AS payments, sum(amount_gbp) AS total_gbp
FROM read_parquet('spending/data/*-nhsd-spend-information/nhsd-spend.parquet')
WHERE supplier ILIKE '%phoenix partnership%'
GROUP BY source_period, supplier
ORDER BY source_period
"
```

## Add a source

Add immutable source metadata, archive and rights evidence URLs, SHA-256, exact byte length, workbook schema and independently checked reconciliation totals to `data-sources.yaml`. The converter fails closed on schema drift; a structurally different workbook needs an explicit adapter rather than permissive parsing. Run `s/test` and perform two clean builds before treating a new release as deterministic.

## Refresh the historical census

```sh
uv run python nhse_spending.py inventory --observed-on YYYY-MM-DD
```

The command follows the canonical NHS England index and every linked year collection, caches raw files under ignored `spending/sources/inventory/`, and regenerates `historical-schema-census.json`. Review URL, digest, coverage and schema changes before committing the census. The current snapshot records 144 logical file-link occurrences representing 143 unique URLs, 17 physical workbook/CSV layouts and six column profiles.
