# nhse

Research corpus and source material on NHS England digital programmes, starting with a timeline of the Federated Data Platform.

## Status

Early. The FDP timeline has a first batch of sourced entries and a working static viewer. Board-meeting caption backfill (2013-2026) is ongoing.

## What is here

- `spec/fdp-timeline.md` - what the FDP timeline is, the entry schema, the source list, and the roadmap. **Read this first.**
- `fdp/entries/` - FDP timeline entries, one YAML file each. `fdp/index.json` is generated from these by `s/build-index` - never hand-edited.
- `people/` - biographical role timelines (appointment/departure dates) for individuals who recur across topics.
- `nhs-board-transcripts/` - YouTube caption tracks for NHS England Board meetings, 2013 onwards, plus `manifest.tsv` mapping video IDs to titles and URLs.
- `nhs-england-blogs/` - index of every NHS England blog post found, with archive links (`manifest.tsv`, from `s/fetch-blog-index`). Pre-2025 posts were moved to the UK Government Web Archive; see the script's header comment for why its search is effectively broken and how this works around it.
- `index.html`, `css/`, `js/` - the static timeline viewer. No build step: open `index.html` via any static file server.
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
s/build-index                # regenerate fdp/index.json after adding/editing an entry
python3 -m http.server 8000  # preview the site at localhost:8000
```

`s/fetch-transcripts` needs either `yt-dlp` on `PATH` or `uv` installed (it will run yt-dlp via `uvx`). It is idempotent - re-run it whenever a new board meeting is published and it fetches only what is missing.

`s/build-index` needs `pyyaml` (`pip install pyyaml` or equivalent).

## Caption reliability

The transcripts are YouTube auto-captions. They are a **search index, not a source of quotation**. They mistranscribe names and acronyms and drop words - the 7 December 2023 meeting renders "opt-outs" as "ops out".

Use `s/search` to find the moment, then open the timestamped link, listen, and transcribe by hand before quoting anything anywhere.

## Licensing

- Scripts: AGPL-3.0-or-later.
- Prose, including the spec: CC-BY-SA-4.0.
- `nhs-board-transcripts/` is third-party content derived from NHS England's YouTube uploads and is **not** covered by either. Its licensing is an open question recorded in the spec, and must be resolved before this repo is made public.
