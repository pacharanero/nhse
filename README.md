# nhse

Research corpus and source material on NHS England digital programmes, starting with a timeline of the Federated Data Platform.

## Status

Public. Live at <https://pacharanero.github.io/nhse/>, landing on a list of utilities - currently just the FDP timeline, at <https://pacharanero.github.io/nhse/fdp/>, with 46 sourced entries and a working static viewer. Board-meeting caption backfill (2013-2026) is ongoing.

## What is here

- `spec/fdp-timeline.md` - what the FDP timeline is, the entry schema, the source list, and the roadmap. **Read this first.**
- `spec/roadmap.md` - notes on where this repo is headed beyond the FDP timeline, including an early-stage idea for an "atlas of vendor capture" across registers of interest, meeting transparency logs, and revolving-door appointments.
- `fdp/entries/` - FDP timeline entries, one YAML file each. `fdp/index.json` is generated from these by `s/build-index` - never hand-edited.
- `people/` - biographical role timelines (appointment/departure dates) for individuals who recur across topics.
- `nhs-board-transcripts/` - YouTube caption tracks for NHS England Board meetings, 2013 onwards, plus `manifest.tsv` mapping video IDs to titles and URLs.
- `nhs-england-blogs/` - index of every NHS England blog post found, with archive links (`manifest.tsv`, from `s/fetch-blog-index`). 1,825 posts indexed so far (2017 onwards - nothing earlier is showing up in either archive yet), each with a Wayback Machine link and a UK Government Web Archive link. Pre-2025 posts were moved to UKGWA; see the script's header comment for why its own search is effectively broken and how this works around it.
- `index.html` - landing page linking to each utility. `fdp/index.html` is the FDP timeline viewer, served at `/fdp/`. Both share `css/app.css` (compiled Tailwind CSS + daisyUI, light/dark theme toggle) and viewing needs no build step - just open via any static file server. Editing styles does need a build step; see "Styling" in `CONTRIBUTING.md`.
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
python3 -m http.server 8000  # preview the site at localhost:8000 (FDP timeline at /fdp/)
```

`s/fetch-transcripts` needs either `yt-dlp` on `PATH` or `uv` installed (it will run yt-dlp via `uvx`). It is idempotent - re-run it whenever a new board meeting is published and it fetches only what is missing.

`s/build-index` needs `pyyaml` (`pip install pyyaml` or equivalent).

Styling (`css/app.css`) is generated from `css/tailwind.css` via `npm install && npm run build:css` - only needed if you're changing markup or styles, not for viewing the site. See "Styling" in `CONTRIBUTING.md`.

## Caption reliability

The transcripts are YouTube auto-captions. They are a **search index, not a source of quotation**. They mistranscribe names and acronyms and drop words - the 7 December 2023 meeting renders "opt-outs" as "ops out".

Use `s/search` to find the moment, then open the timestamped link, listen, and transcribe by hand before quoting anything anywhere.

## Licensing

- Scripts: AGPL-3.0-or-later.
- Prose, including the spec: CC-BY-SA-4.0.
- `nhs-board-transcripts/` is third-party content derived from NHS England's YouTube uploads and is **not** covered by either. Its licensing is an open question recorded in the spec, and must be resolved before this repo is made public.
