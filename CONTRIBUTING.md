# Contributing

Don't want to touch git or YAML? Open an
[issue using the entry template](https://github.com/pacharanero/nhse/issues/new?template=new-entry.yml) -
a link and a sentence or two is enough, nothing is required, and someone
will turn it into an entry using the schema below.
Everything from here down is for contributing directly via a pull request.

## Repo structure

This repo covers more than the FDP timeline over time. Each research topic
gets its own top-level folder:

- `fdp/` - the Federated Data Platform timeline (`spec/fdp-timeline.md`). The
  only topic so far.
- `people/` - biographical role timelines (appointment and departure dates,
  with sources) for individuals who recur across topics, e.g. NHS England
  executives. One YAML file per person. Referenced by topic entries, not
  itself rendered as a timeline.
- `nhs-board-transcripts/` - the shared board-meeting caption corpus, not
  specific to any one topic.
- `nhs-england-blogs/` - index of every NHS England blog post found (via
  `s/fetch-blog-index`), with a Wayback Machine link and, where found, a UK
  Government Web Archive (UKGWA) link for each. This is raw source
  material, like the transcripts - extracting dated facts from a specific
  post into a topic's `entries/` is a separate step, done by hand.

When a new topic starts, give it its own top-level folder and its own spec
file under `spec/`, following the `fdp/` pattern: `<topic>/entries/*.yaml`
plus a `<topic>/index.json` built the same way as `s/build-index`.

This is a research corpus, not a wiki. The bar for adding an entry is: is this a documented event, decision, statement, or disclosure, with a date and a primary source? If yes, it belongs here. If it's an opinion about one of those things, it doesn't - see `spec/fdp-timeline.md` for the full editorial policy, especially "What this is not" and "Contested claims". Read that spec first; this file is the mechanics of adding to it.

## Adding an entry

One entry is one YAML file in `fdp/entries/`, named `<id>.yaml`.

Copy an existing entry as a starting point (any file in `fdp/entries/` will do) rather than writing one from scratch, so you don't miss a field.

### Fields

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Stable slug, same as the filename minus `.yaml`. Format: `YYYY-MM-DD-short-description`, or `YYYY-MM-short-description` for month precision. Never reused or renumbered once merged. |
| `date` | yes | ISO `YYYY-MM-DD`. For `month` or `quarter` precision, use the first day (`2022-04-01` for April 2022) - `date_precision` tells the renderer not to trust the day. |
| `date_precision` | yes | `day`, `month`, or `quarter`. |
| `category` | yes | One of: `scope`, `contract`, `official`, `media`, `board`, `legal`, `civil`. See the table in the spec. |
| `title` | yes | Factual, under ~90 characters, no adjectives. |
| `summary` | yes | 1-3 sentences. What happened, not why it matters. |
| `quote` | no | Verbatim, with speaker and role at the time. |
| `quote_verified` | if `quote` is set | `audio`, `document`, or `secondary`. Board-meeting captions start at `secondary` until someone has listened to the audio - see the spec's "Caption reliability" section. |
| `source_url` | yes | Primary source where possible. |
| `source_title` | yes | Publication or body, and headline. |
| `archive_url` | yes | A Wayback Machine (or archive.today) capture of `source_url`, taken at the point of entry. Non-negotiable - see below. |
| `paywalled` | no | Boolean. Set `true` if `source_url` sits behind a paywall - see "Paywalled sources" in the spec. |
| `video_id` | board entries only | YouTube video ID. |
| `t` | board entries only | Start time in seconds. |
| `related` | no | List of other entry `id`s. |
| `contested` | no | Free text: who disputes this, and what they say. Denials live in the same entry as the claim they deny - never a separate one. |

### Getting the archive_url

Before you write the entry, archive the source:

```sh
curl -sI "https://web.archive.org/save/<source_url>" | grep -i location
```

If a capture already exists and is recent enough, you can check first:

```sh
curl -s "https://archive.org/wayback/available?url=<url-encoded-source_url>"
```

Use the returned `web.archive.org/web/...` URL as `archive_url`. An entry without one is incomplete and will fail `s/build-index`.

### Dates

Use the date the thing *happened*, not the date it was reported. If a document is undated, use `month` or `quarter` precision rather than guessing a day - a timeline that silently invents day-precision dates is worse than one with visible fuzziness.

### Categories are exclusive

Every entry carries exactly one `category`. If an event spans two - say, a petition (`civil`) that triggers a government response (`legal`) - record it as two linked entries via `related`, not one entry with two categories.

### Quotes

Don't quote from `nhs-board-transcripts/*.vtt` directly. Those are YouTube auto-captions: a search index, not a transcription. Use `s/search` to find the moment, open the timestamped link, listen, and transcribe by hand. Anything taken from a caption without listening to the audio is `quote_verified: secondary` at best, and should be phrased as "NHS England's auto-generated captions record [name] as saying..." rather than presented as verbatim.

### Contested claims

If a party denies or disputes something in the entry, add it to the same entry's `contested` field. Don't create a second entry for the denial and don't omit it.

## After adding or editing entries

Rebuild the index the site reads from:

```sh
s/build-index
```

This regenerates `fdp/index.json` from everything in `fdp/entries/` and checks required fields, unique ids, ISO dates, and that `archive_url` is present. Commit the updated `index.json` alongside your entry.

## Local preview

The site is static and reads `fdp/index.json` plus each entry's YAML directly in the browser - no build step. Serve the repo root with any static file server, e.g.:

```sh
python3 -m http.server 8000
```

Then open `http://localhost:8000/`.

## Style

- No hard-wrapped prose; hyphens, not em dashes.
- Filenames: slug-case-with-hyphens.
- `bash -n s/*` passes before committing anything under `s/`.
- No paywalled article bodies committed, no credentials, ever.

## What not to do

- Don't hand-edit `fdp/index.json` - it's generated.
- Don't hand-edit `nhs-board-transcripts/*.vtt` or `manifest.tsv` - those come from `s/fetch-transcripts`.
- Don't add a scraper or technique for bypassing a paywall. See "Paywalled sources - handling" in the spec.
- Don't invent day-precision dates to fill in a gap.
- Don't editorialise in `title` or `summary`. Save opinion for entries that are themselves about someone's stated opinion (e.g. a `civil` entry about a position statement) - and even then, report that it was said, don't endorse it.
