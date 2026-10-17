# nhse

Source-linked research data on NHS England digital programmes, governance and spending.

## Status

Public. Live at <https://pacharanero.github.io/nhse/>, with an FDP timeline of 90 sourced entries and a spending-data area that distinguishes NHS England's accounting-group budget, audited outturn and detailed payment publications. Board-meeting caption backfill is complete through 2026.

## What is here

- `spec/fdp-timeline.md` - what the FDP timeline is, the entry schema, the source list, and the roadmap. **Read this first.**
- `spec/spending-data.md` - accounting boundaries, source policy, normalized payment schema, release format and spending-data roadmap.
- `spec/roadmap.md` - notes on where this repo is headed beyond the FDP timeline, including an early-stage idea for an "atlas of vendor capture" across registers of interest, meeting transparency logs, and revolving-door appointments.
- `fdp/entries/` - FDP timeline entries, one YAML file each. `fdp/index.json` is generated from these by `s/build-index` - never hand-edited.
- `fdp/bartlett-appearances.yaml` - lightweight cumulative-appearance tracker (date, title, url) rendered as small numbered dots on the timeline, not full entries. `fdp/bartlett-appearances.json` is generated from this by `s/build-bartlett-index`. See "Appearance trackers" in `CONTRIBUTING.md`.
- `people/` - biographical role timelines (appointment/departure dates) for individuals who recur across topics.
- `spending/` - typed top-level financial figures, the detailed-source registry, reproducible build instructions and a separate five-entry editorial timeline.
- `nhs-board-transcripts/` - YouTube caption tracks for NHS England Board meetings, 2013 onwards, plus `manifest.tsv` mapping video IDs to titles and URLs.
- `nhs-england-blogs/` - index of every NHS England blog post found, with archive links (`manifest.tsv`, from `s/fetch-blog-index`). 1,825 posts indexed so far (2017 onwards - nothing earlier is showing up in either archive yet), each with a Wayback Machine link and a UK Government Web Archive link. Pre-2025 posts were moved to UKGWA; see the script's header comment for why its own search is effectively broken and how this works around it.
- `index.html` - landing page linking to each utility. `fdp/index.html` is the FDP timeline viewer and `spending/index.html` explains the spending figures and release status. All pages share `css/app.css` and the light/dark theme toggle.
- `s/` - the repeated processes.
- `CONTRIBUTING.md` - how to add an entry, including the archive-at-entry-time step.

Each new research topic beyond FDP gets its own top-level folder following the same `<topic>/entries/*.yaml` pattern - see `CONTRIBUTING.md`.

## What this is not

Not a campaign site and not an argument. Entries state what happened, when, with a link. Interpretation lives in the writing that draws on this, not in the data.

## Quick start

```sh
s/fetch-transcripts          # gather any board-meeting captions not already present
s/search 'federated data'    # search all transcripts, get timestamped YouTube links
s/search -C 6 'opt.?out'     # wider context around each hit
s/fetch-blog-index           # build/extend the NHS England blog post index + archive links
s/build-index                # regenerate fdp/index.json after adding/editing an entry
s/build-bartlett-index       # regenerate fdp/bartlett-appearances.json after editing that file
uv sync --locked             # install the exact spending-pipeline dependencies
s/fetch-spending-data        # download and verify the registered September 2025 workbook
s/build-spending-data        # build and validate local Parquet and CSV.gz artifacts
s/test                       # run parser, determinism, query, and finance-registry tests
python3 -m http.server 8000  # preview the site at localhost:8000
```

`s/fetch-transcripts` needs either `yt-dlp` on `PATH` or `uv` installed (it will run yt-dlp via `uvx`). It is idempotent - re-run it whenever a new board meeting is published and it fetches only what is missing.

The timeline index builders use the system `python3` and PyYAML. The spending pipeline uses the fully pinned `uv.lock` environment: `openpyxl` parses workbook structure, PyArrow writes typed Parquet, DuckDB independently validates analytical queries and PyYAML reads committed registries. Raw workbooks remain local; normalized releases are committed with provenance, validation and checksums.

Styling (`css/app.css`) is generated from `css/tailwind.css` via `npm install && npm run build:css` - only needed if you're changing markup or styles, not for viewing the site. See "Styling" in `CONTRIBUTING.md`.

## Caption reliability

The transcripts are YouTube auto-captions. They are a **search index, not a source of quotation**. They mistranscribe names and acronyms and drop words - the 7 December 2023 meeting renders "opt-outs" as "ops out".

Use `s/search` to find the moment, then open the timestamped link, listen, and transcribe by hand before quoting anything anywhere.

## Acknowledgements

This timeline exists because of reporting, research, FOI requests, and campaigning done by people and organisations outside NHS England. Particular thanks to:

**Journalists and researchers**

- Tom Bartlett - independent FDP commentator and former NHS England employee; Bartlett Data blog, and Computer Weekly's "Inside FDP" column series
- Peter Geoghegan and Lucas Amin - Democracy for Sale and the London Review of Books, for the "Project Onion" investigation into Palantir's lobbying
- Mary Fitzgerald and Cori Crider - openDemocracy, for the original 2020 COVID Data Store reporting
- Adam Bychawski - openDemocracy
- Rhiannon Osborne and Adrian O'Dowd - The BMJ
- George Monbiot - The Guardian
- Lindsay Clark - The Register
- Miles Dilworth - Daily Mail
- Simon Childs - Novara Media
- Steve Black - healthcare consultant and former NHS data scientist, widely quoted on FDP benefit claims
- Nye Hudson - for the FOI request (via WhatDoTheyKnow) behind the only public trust-level FDP usage data this timeline has been able to draw on

**Organisations**

- Foxglove, including Rosa Curling - litigation and campaigning against the COVID Data Store and FDP contracts since 2020
- Good Law Project - legal action over Palantir's redacted FDP contract
- The National Data Guardian's office, under Dr Nicola Byrne - sustained, named public scrutiny of FDP data access and public trust
- The Health Foundation and the Office for Statistics Regulation - independent analysis that directly contradicted NHS England's own published benefit claims
- DAUK (Doctors' Association UK), 38 Degrees, and NHS Analysts Together - petitions, protest organisation, and an anonymous internal staff letter calling for the Palantir partnership to end

If you've written about the FDP and you're not listed here, or we've got your affiliation wrong, please open an issue (see "Propose an entry" on the [timeline itself](https://pacharanero.github.io/nhse/fdp/)) or get in touch.

## Licensing

- Scripts: AGPL-3.0-or-later.
- Prose, including the spec: CC-BY-SA-4.0.
- Binary documents in `fdp/sources/` are third-party primary-source material retained for evidence and preservation. They are not covered by the repository's software or prose licences; copyright and other rights remain with their original owners.
- `nhs-board-transcripts/` is third-party content derived from NHS England's YouTube uploads and is not covered by either repository licence.
- Downloaded spending workbooks remain local. The normalized September 2025 spending release is redistributed under OGL v3 and the project owner's recorded fair-use/fair-dealing determination; its Data Package carries the source evidence, decision and limitations.
