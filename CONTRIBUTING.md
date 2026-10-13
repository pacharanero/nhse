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
  only topic so far. Its viewer is `fdp/index.html`, served at `/fdp/`;
  it shares `css/app.css` and `js/theme-toggle.js` with the root landing
  page rather than keeping its own copies.
- `index.html` (repo root) - the landing page linking out to each topic's
  viewer, e.g. `fdp/`. When a new topic gets its own viewer, add a card
  for it here.
- `css/app.css` - the compiled Tailwind CSS + daisyUI stylesheet every
  page loads. **Generated, do not hand-edit** - see "Styling" below.
  `css/tailwind.css` is the source file that generates it.
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
- `fdp/sources/` - raw primary documents retained alongside the entries
  that cite them, for cases where the source isn't a stable URL (an FOI
  response attachment, for example) or where archive.org has proved
  unable to capture the page itself. Named `<id-prefix>-<short
  description>.<ext>`. This supplements, not replaces, `archive_url` -
  an entry still needs one.

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
| `tags` | yes | List of lowercase-hyphenated tags, at least one. Lowercase a-z0-9 and hyphens only (`s/build-index` enforces this). See "Tags" below. |
| `title` | yes | Factual, under ~90 characters, no adjectives. |
| `summary` | yes | 1-3 sentences. What happened, not why it matters. Supports inline markdown links - see "Inline source links" below. |
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

**If archive.org genuinely can't capture the page** - repeated `HTTP 520` from `/save/`, confirmed from more than one IP, while other pages on the same domain archive fine (so it's not a general Wayback outage) - that's a targeted block, not a retry-later problem. In that case: retain the primary document or a full text copy of the page in `fdp/sources/` (see "Repo structure" above), and point `archive_url` at that file's URL in this repo instead of a Wayback link. Note why in the entry's `contested` field so a reader isn't left wondering why the link goes to GitHub rather than web.archive.org. Try archive.today first if you haven't - it sometimes succeeds where archive.org fails, and is the preferred fallback when it works.

### Dates

Use the date the thing *happened*, not the date it was reported. If a document is undated, use `month` or `quarter` precision rather than guessing a day - a timeline that silently invents day-precision dates is worse than one with visible fuzziness.

### Tags

Every entry carries a `tags` list - at least one, usually several. Two kinds of tag, mixed freely in the same list:

- **Kind tags** - the old fixed categories, still exactly seven: `scope`, `contract`, `official`, `media`, `board`, `legal`, `civil`. See the table in the spec for what each means. Put one of these first in the list where it clearly applies - the site uses whichever kind tag appears first to pick the entry's colour and which side of the timeline it renders on. An entry can only usefully have one kind tag; if an event genuinely spans two (a petition that triggers a government response), record it as two linked entries via `related`, not one entry wearing both kinds.
- **Free tags** - anything else: organisations (`nhse`, `nhsx`, `nhsd`, `dhsc`, `foxglove`, `dauk`...), people (`thiel`, `karp`, `ming-tang`...), topics (`opt-out`, `break-clause`, `cost`, `gdpr`...), source outlets (`guardian`, `bmj`, `the-register`...). Add as many as genuinely apply - this is what makes cross-cutting filtering possible (e.g. every `parliament` entry that also touches `break-clause`). No fixed vocabulary; just keep tags lowercase-hyphenated and reuse an existing tag rather than inventing a near-duplicate (check `fdp/index.json` or the site's filter list for what's already in use before adding a new one).

The site's tag filter ANDs whatever you select - picking `nhse` and `parliament` together shows only entries with both, which is the point: it's how coincidences and overlaps surface.

### Quotes

Don't quote from `nhs-board-transcripts/*.vtt` directly. Those are YouTube auto-captions: a search index, not a transcription. Use `s/search` to find the moment, open the timestamped link, listen, and transcribe by hand. Anything taken from a caption without listening to the audio is `quote_verified: secondary` at best, and should be phrased as "NHS England's auto-generated captions record [name] as saying..." rather than presented as verbatim.

### Contested claims

If a party denies or disputes something in the entry, add it to the same entry's `contested` field. Don't create a second entry for the denial and don't omit it.

### Inline source links

The goal is for this to be the densest, most easily-navigable resource on the FDP, not just a list of entries - so when `summary` names a specific claim or assertion (someone saying something, a figure, a characterisation), and that claim has its own citable source distinct from the entry's main `source_url`, link it inline rather than leaving the reader to go searching:

```yaml
summary: >-
  ... peer Tom Watson publicly defended the company, accusing critics of
  [\"mob rule\"](https://www.bbc.co.uk/sounds/play/m0032qly).
```

Plain markdown link syntax, `[text](https://...)` - only `http(s)://` URLs are linkified; anything else is left as literal text, and `s/build-index` rejects a malformed one rather than silently dropping it. Prefer the same archived-copy discipline as `archive_url` where practical, but a live link is better than no link - a streaming-audio source like BBC Sounds often can't be archived at all (see `contested` for recording why, same pattern as the `fdp/sources/` fallback above).

If the claim is substantial enough to want its own date, full quote, and independent sourcing - not just a passing mention - give it its own entry instead (or as well), linked back via `related`. Inline links are for citing a claim in passing; a full entry is for claims that are events in their own right.

## After adding or editing entries

Rebuild the index the site reads from:

```sh
s/build-index
```

This regenerates `fdp/index.json` from everything in `fdp/entries/` and checks required fields, unique ids, ISO dates, and that `archive_url` is present. Commit the updated `index.json` alongside your entry.

## Appearance trackers

Not everything worth charting is worth a full entry. `fdp/bartlett-appearances.yaml` is a lightweight, hand-maintained list for tracking the pace of one person's or organisation's public output (Tom Bartlett's blog posts, Computer Weekly columns, and media quotes, so far) as small numbered dots on the timeline, rather than as full cards with quotes and archive copies. Each item needs `date`, `title`, `url`, `outlet` (shown as the dot's label prefix, e.g. "Computer Weekly" or "Bartlett Data Blog"), and `self` - a boolean distinguishing a channel the subject fully controls (their own blog, their own LinkedIn - `self: true`) from third-party press/media coverage (a trade press column, a newspaper quote - `self: false`). The distinction matters for exactly the question this tracker exists to help answer: how much of someone's apparent prominence is self-published versus access they'd need some kind of help to get. Dots are colour-coded accordingly, with a legend under the controls bar.

```sh
s/build-bartlett-index
```

regenerates `fdp/bartlett-appearances.json` from the YAML, sorts by date, and assigns each item a cumulative `n` - that's the "TB#7" in the dot's label. The dots aren't tag-filtered or searched like entries; a single toggle button (`Bartlett` in the controls bar, `?bartlett=0` in the URL) is the only way to hide them. `js/app.js`'s `mergedTimelineItems` is where they're interleaved into the main entry sequence.

There's a second one, `fdp/watson-appearances.yaml` / `s/build-watson-index`, tracking Tom Watson's media appearances since his September 2026 Palantir appointment. Both are driven by the same `TRACKERS` array at the top of `js/app.js` - to track a third frequent voice, add a `{ key, prefix, label, file, toggleId }` entry there, a matching `fdp/<name>-appearances.yaml`, an `s/build-<name>-index` script (copy `s/build-watson-index`), and a toggle button in `fdp/index.html`, rather than bending an existing tracker to cover two people at once.

A single especially significant appearance (see `2026-04-13-tom-bartlett-leaves-nhse-launches-independent-voice.yaml` and `2026-04-30-computer-weekly-inside-fdp-column-bartlett.yaml`) can be *both* a full entry *and* a line in the appearances file - the dot and the card aren't mutually exclusive, and the cumulative count should include every appearance regardless of whether it also got the full treatment.

## Styling

The site uses [Tailwind CSS](https://tailwindcss.com/) and [daisyUI](https://daisyui.com/) for layout and components (timeline, badges, modal, theme switching). This has a build step, but only for people editing styles - the committed `css/app.css` is what ships, and viewing the site needs nothing beyond a static file server (see "Local preview" below).

If you're changing markup (adding a new daisyUI component class to `index.html` or `fdp/index.html`, say) or editing `css/tailwind.css` itself, install the dev dependencies once and rebuild:

```sh
npm install
npm run build:css
```

`npm run build:css` runs the Tailwind CLI, scans the HTML/JS for class names in use, and writes a minified `css/app.css`. Commit the regenerated `css/app.css` alongside whatever markup change prompted it - a stale `app.css` silently drops styles for classes added since the last build.

Two daisyUI themes are enabled: `corporate` (light, default) and `business` (dark, used when the visitor's OS prefers dark mode or they've toggled it). The theme toggle button (`[data-theme-toggle]` in `js/theme-toggle.js`) persists the choice to `localStorage` under the `nhse-theme` key, read by a small inline `<head>` script on each page to avoid a flash of the wrong theme. Keep the two theme names in sync between `css/tailwind.css`'s `@plugin "daisyui"` line and `js/theme-toggle.js`'s `LIGHT`/`DARK` constants if either changes.

## Local preview

The site is static and reads `fdp/index.json` plus each entry's YAML directly in the browser - no build step needed just to view it (see "Styling" above for when a CSS rebuild is needed). The root `index.html` is a landing page linking to each utility (the FDP timeline lives at `/fdp/`); serve the repo root with any static file server, e.g.:

```sh
python3 -m http.server 8000
```

Then open `http://localhost:8000/fdp/` (or `http://localhost:8000/` for the landing page).

## URL querystring convention

The FDP site's filters, search, and sort order all round-trip through the URL, so a filtered view is a shareable link. Any future topic site in this repo should use the same three parameters, so links behave consistently across the whole project:

| Param | Example | Notes |
|---|---|---|
| `tags` | `?tags=nhse,parliament` | Comma-separated, ANDed together (all must match, not any). Omit entirely when no filter is active. |
| `q` | `?q=opt-out` | Free-text search string. Omit when empty. |
| `sort` | `?sort=asc` | Only written when it differs from the site's default (`desc`, newest-first, on the FDP site) - keeps default-state URLs clean. |

Read once on load, written back with `history.replaceState` (not `pushState`) on every change, so adjusting filters doesn't spam the browser's back button. See `js/app.js`'s `readStateFromURL` / `writeStateToURL` for the reference implementation.

## Style

- No hard-wrapped prose; hyphens, not em dashes.
- Filenames: slug-case-with-hyphens.
- `bash -n s/*` passes before committing anything under `s/`.
- No paywalled article bodies committed, no credentials, ever.

## What not to do

- Don't hand-edit `fdp/index.json` - it's generated.
- Don't hand-edit `css/app.css` - it's generated from `css/tailwind.css` by `npm run build:css`.
- Don't hand-edit `nhs-board-transcripts/*.vtt` or `manifest.tsv` - those come from `s/fetch-transcripts`.
- Don't add a scraper or technique for bypassing a paywall. See "Paywalled sources - handling" in the spec.
- Don't invent day-precision dates to fill in a gap.
- Don't editorialise in `title` or `summary`. Save opinion for entries that are themselves about someone's stated opinion (e.g. a `civil` entry about a position statement) - and even then, report that it was said, don't endorse it.
