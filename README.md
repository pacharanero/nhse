# nhse

Research corpus and source material on NHS England digital programmes, starting with a timeline of the Federated Data Platform.

## Status

Early. Phase 1 is data gathering: accumulate primary sources and extract dated, citable facts. The timeline visualisation comes later, once the corpus is worth rendering.

## What is here

- `spec/fdp-timeline.md` - what the timeline is, the entry schema, the source list, and the roadmap. **Read this first.**
- `nhs-board-transcripts/` - YouTube caption tracks for NHS England Board meetings, 2013 onwards, plus `manifest.tsv` mapping video IDs to titles and URLs.
- `s/` - the repeated processes.

## What this is not

Not a campaign site and not an argument. Entries state what happened, when, with a link. Interpretation lives in the writing that draws on this, not in the data.

## Quick start

```sh
s/fetch-transcripts          # gather any board-meeting captions not already present
s/search 'federated data'    # search all transcripts, get timestamped YouTube links
s/search -C 6 'opt.?out'     # wider context around each hit
```

`s/fetch-transcripts` needs either `yt-dlp` on `PATH` or `uv` installed (it will run yt-dlp via `uvx`). It is idempotent - re-run it whenever a new board meeting is published and it fetches only what is missing.

## Caption reliability

The transcripts are YouTube auto-captions. They are a **search index, not a source of quotation**. They mistranscribe names and acronyms and drop words - the 7 December 2023 meeting renders "opt-outs" as "ops out".

Use `s/search` to find the moment, then open the timestamped link, listen, and transcribe by hand before quoting anything anywhere.

## Licensing

- Scripts: AGPL-3.0-or-later.
- Prose, including the spec: CC-BY-SA-4.0.
- `nhs-board-transcripts/` is third-party content derived from NHS England's YouTube uploads and is **not** covered by either. Its licensing is an open question recorded in the spec, and must be resolved before this repo is made public.
