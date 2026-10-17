# Repository scripts

Scripts are small entry points for repeated repository processes. They run from any working directory, forward arguments and fail on errors.

- `s/build-index [topic]` - validate topic entry YAML and regenerate its JSON index; defaults to `fdp`.
- `s/build-bartlett-index` - regenerate the Tom Bartlett appearance index.
- `s/build-watson-index` - regenerate the Tom Watson appearance index.
- `s/build-edh-index` - regenerate the Everything Digital Health appearance index.
- `s/fetch-transcripts` - fetch missing NHS England board-meeting captions.
- `s/search` - search the caption corpus and produce timestamped YouTube links.
- `s/fetch-blog-index` - update the NHS England blog manifest and archive links.
- `s/fetch-board-papers-index` - update the board-paper source index.
- `s/fetch-spending-data` - fetch and verify a registered spending workbook.
- `s/build-spending-data` - build and validate Parquet and CSV.gz spending artifacts.
- `s/fetch-procurement-data --source <id>` - fetch and verify one exact registered procurement capture.
- `s/build-procurement-data` - build and validate the bounded procurement-enrichment fixture release.
- `s/test` - run the Python unit and determinism tests through the locked `uv` environment.
- `s/up` - commit and push a coherent update using the repository workflow.
