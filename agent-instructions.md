# Agent instructions

## Project purpose

A research corpus and source material on NHS England digital programmes, currently focused on building a filterable timeline of the Federated Data Platform. It is an evidence base, not an argument: the arguments live in the Everything Digital Health episodes that draw on it.

It is not a campaign site, not a Palantir dossier, and not a news aggregator.

## Read first

1. [spec/fdp-timeline.md](spec/fdp-timeline.md) - purpose, categories, entry schema, source list, roadmap, open questions. Nothing else here makes sense without it.
2. [README.md](README.md)
3. House style: <https://github.com/pacharanero/house-style/blob/main/AGENTS.md>

## Core invariants

- **Captions are a search index, never a quotation source.** Files in `nhs-board-transcripts/` are YouTube auto-captions with known transcription errors. Any quote derived from them is `secondary` until a human has listened to the audio. Do not present caption text as a verbatim quote.
- **Every entry carries a date, a primary source URL, and an archive URL.** An entry without an archive link is incomplete; NHS England pages rot.
- **Denials travel with allegations.** Where a party disputes a claim, the dispute goes in the same entry. Reporting an allegation without its denial is a defect.
- **No speculation.** Documented facts, reported claims, and open questions are distinct. Do not assert motive, or anyone's future employment, however plausible.
- **No paywall circumvention.** Do not add scrapers or techniques for bypassing paywalls. Use the routes in the spec: own subscription, brief attributed quotation, metadata-only entries, institutional access, or - best - obtaining the underlying primary document.
- **Do not hand-edit generated files.** `nhs-board-transcripts/manifest.tsv` and the `.vtt` files are produced by `s/fetch-transcripts`.

## Local workflow

```sh
s/fetch-transcripts          # idempotent; fetches only missing captions
s/search '<extended-regex>'  # timestamped, clickable hits across all transcripts
```

Both scripts are bash, `set -euo pipefail`, and cd to the repo root. Check syntax with `bash -n` before committing.

## Before every commit

- `bash -n s/*` passes.
- New prose is not hard-wrapped; hyphens not emdashes; filenames slug-case-with-hyphens.
- No paywalled article bodies committed, and no credentials.

## Git workflow

New repo, one contributor: commit and push validated coherent parcels direct to `main`.

## External actions

Ask before: making this repository public, adding a remote, or running bulk fetches against any site other than the NHS England YouTube playlist already in `s/fetch-transcripts`.

Publication in particular is gated on the two unresolved licensing and naming questions in the spec.
