# NHS England spending data

This directory contains the source registry, typed top-level financial figures, editorial spending timeline and a reproducible detailed-payments pipeline. Read `../spec/spending-data.md` before adding a source or changing the normalized schema.

## Build the September 2025 release

```sh
uv sync --locked
s/fetch-spending-data
s/build-spending-data
uv run python nhse_spending.py validate
```

The verified workbook is written to the ignored `spending/sources/` directory. Parquet, deterministic CSV.gz, Data Package metadata, validation results and checksums are written to and committed from `spending/data/2025-09-payments-over-25000/`.

Use `s/fetch-spending-data --archive` to fetch the committed Wayback capture instead of the live NHS England URL. Both routes must produce the exact SHA-256 in `data-sources.yaml`.

## Query with DuckDB

No import or database file is required:

```sh
duckdb -c "SELECT entity, count(*) AS payments, sum(amount_gbp) AS total_gbp FROM read_parquet('spending/data/2025-09-payments-over-25000/payments.parquet') GROUP BY entity ORDER BY total_gbp DESC"
```

Filter `entity = 'NHS England'` for the NHS England-parent view. Do not silently exclude CSU rows from whole-workbook totals.

## Add a source

Add immutable source metadata, archive and rights evidence URLs, SHA-256, exact byte length, workbook schema and independently checked reconciliation totals to `data-sources.yaml`. The converter fails closed on schema drift; a structurally different workbook needs an explicit adapter rather than permissive parsing. Run `s/test` and perform two clean builds before treating a new release as deterministic.
