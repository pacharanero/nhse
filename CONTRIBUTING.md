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
| `contested` | no | Free text, rendered as "Caveats": limitations, sourcing caveats, what's unverified, or - when it genuinely applies - who disputes the claim and what they say. Denials live in the same entry as the claim they deny - never a separate one. Supports the same inline markdown links as `summary`. |

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

### Caveats and disputes

The `contested` field renders in the site as "Caveats," not "Contested" - most of what lives there isn't anyone disputing anything, it's an honest limitation: what wasn't independently verified, why a source is archived the way it is, what's still unknown. Reserve the word "contested" itself, in prose, for cases where a party has actually denied or disputed the claim with a specific, citable counter-statement. If a party does deny or dispute something in the entry, add it to the same entry's `contested` field - don't create a second entry for the denial and don't omit it.

### Inline source links

The goal is for this to be the densest, most easily-navigable resource on the FDP, not just a list of entries - so when `summary` names a specific claim or assertion (someone saying something, a figure, a characterisation), and that claim has its own citable source distinct from the entry's main `source_url`, link it inline rather than leaving the reader to go searching:

```yaml
summary: >-
  ... peer Tom Watson publicly defended the company, accusing critics of
  ["mob rule"](https://www.bbc.co.uk/sounds/play/m0032qly).
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

There's a second one, `fdp/watson-appearances.yaml` / `s/build-watson-index`, tracking Tom Watson's media appearances since his September 2026 Palantir appointment, and a third, `fdp/edh-appearances.yaml` / `s/build-edh-index`, tracking FDP-relevant episodes of Marcus Baw's own *Everything Digital Health* YouTube channel/podcast - every item there is `self: true` (it's the author's own channel), so that tracker isn't using the self/third-party distinction to mean anything, it exists purely to chart episode frequency without promoting every episode to a full entry. All three are driven by the same `TRACKERS` array at the top of `js/app.js` - to track a fourth frequent voice (or recurring show), add a `{ key, prefix, label, file, toggleId }` entry there, a matching `fdp/<name>-appearances.yaml`, an `s/build-<name>-index` script (copy `s/build-watson-index` or `s/build-edh-index`), and a toggle button in `fdp/index.html`, rather than bending an existing tracker to cover two subjects at once.

A single especially significant appearance (see `2026-04-13-tom-bartlett-leaves-nhse-launches-independent-voice.yaml` and `2026-04-30-computer-weekly-inside-fdp-column-bartlett.yaml`) can be *both* a full entry *and* a line in the appearances file - the dot and the card aren't mutually exclusive, and the cumulative count should include every appearance regardless of whether it also got the full treatment.

## Legal basis era indicator

The timeline carries a subtle background tint marking the date ranges during which NHS England was asserting the FDP/COVID Data Store was for "secondary use/planning" (national data opt-out applies) versus "direct care" (it doesn't) - see the "Scope & Legal Basis" thread in `spec/fdp-timeline.md`. It's driven by two small arrays at the top of `js/app.js`:

- `LEGAL_BASIS_ERAS` - date ranges and a low-opacity `bg-<colour>/10` tint class applied to each entry/tracker `<li>` whose date falls inside. Each zone is anchored to a specific entry that is itself evidence of that framing, not an editorial judgement call.
- `LEGAL_BASIS_ERA_MARKERS` - the three labelled divider rows at the zone boundaries, rendered with `legalEraMarkerLi()` (the same two-sided divider pattern as the existing `todayMarkerLi()`, parameterised by colour).

The roughly 21-month gap between the two confirmed zones (25 Nov 2021, NHS England's own COVID-19 Data Store DPIA last ticking "not direct care," to 1 Aug 2023, the DH briefing paper to Parliament asserting direct care "first and foremost") is left deliberately untinted rather than guessing where the actual pivot sits - only the two endpoints are confirmed. If a future entry narrows that gap, update both arrays' dates and the `spec/fdp-timeline.md` progress notes together; don't tint the gap without a specific anchor entry to point to.

Both arrays are read inside `render()`'s marker queue (see the comment there), not as a separate pass, so they interleave correctly with the existing today-marker and year-marker logic regardless of sort order. The divider markers' `.timeline-end` uses `min-w-[min(14rem,100%)]` rather than a bare `min-w-[14rem]` - the latter doesn't shrink on narrow viewports and overflows (confirmed to affect `todayMarkerLi()` too, fixed as part of this feature); keep divider labels short (under ~20 characters) regardless, since the column still sizes to its own content once the floor is removed.

## WCAG AA contrast

This timeline commits to WCAG 2.1 AA contrast (4.5:1 for normal text, 3:1 for large text and UI components) throughout, in both the `corporate` (light) and `business` (dark) themes. This was not true by default - daisyUI's stock theme colours, used directly as small text or as badge/link colours, fail AA in several specific combinations (see R21 in `spec/fdp-timeline.md` for the full incident: a user-reported illegible marker turned out to be one of many). Check any new UI element against this before shipping it, the same way a new entry gets its `archive_url` checked - "looks fine on my screen in one theme" is not a check.

**The governing pattern, established fixing R21's failures**: semantic colour (`primary`/`accent`/`success`/`info`/`error`/`warning`) is fine for *decorative* elements - a dot, a divider line, a border, a low-opacity background tint - none of which carry a 4.5:1 text requirement. Never apply a semantic colour directly as *small text* colour on `base-100` without checking it first; several fail in one theme or the other (`text-error`, `text-info`, `text-accent` all fail at some point). Prefer `text-base-content` (always safe, confirmed ≥10:1 in both themes) for anything that's actually prose or a label a reader needs to read, and let the colour do its job elsewhere in the same component (the era/today markers keep their coloured dot and divider line; only the label text itself moved to `text-base-content` - see `todayMarkerLi()`/`legalEraMarkerLi()` in `js/app.js`).

**Badge and link colours needed the underlying theme fixed, not just a class swapped** - `badge-X`'s content-on-colour pairing and `link-X`'s text-on-page pairing are daisyUI component defaults, not something this codebase chooses per use. Four colours (`primary`, `accent`, `success`, `info`) were too light in the `corporate` theme for their own (always-white) badge content text, and the identical issue affects `link-primary` there too - the same two colours swapped give the same ratio, so darkening the theme colour fixes both at once. In the `business` theme, `error` needed a small nudge for `badge-error`, but `primary` could **not** simply be lightened for `link-primary` (1.90:1 there) the same way, because `--color-primary` is shared with `badge-primary`, which already passed comfortably (6.04:1) at its *current* lightness - lightening it to fix the link broke the badge (6.04 -> 2.50). Where a single theme variable is pulled in two directions by two different component roles against the same page background, give the specific component its own override instead of moving the shared variable - see `[data-theme="business"] .link-primary` in `css/tailwind.css`, which leaves `--color-primary` (and therefore `badge-primary`) untouched. All overrides keep each colour's original hue and chroma, changing only lightness by the minimum amount needed to clear 4.5:1 with a small margin, so they stay recognisably the "same" colour, just readable.

**Audit method, if redoing this or checking something new**: don't trust contrast maths without checking it against the live page at least once. A WCAG contrast ratio needs each colour's *relative luminance*, computed from linear-light sRGB; `oklch()`/`oklab()` values have to be converted through OKLab -> linear sRGB first (standard matrices, see e.g. the CSS Color 4 spec or any OKLab reference implementation). The one mistake worth flagging explicitly: anything involving opacity (`text-base-content/60`, `bg-info/10`, an `alert-soft` background) is **not** safe to blend in linear-light space - browsers composite translucent colours in gamma-encoded sRGB at paint time (confirmed here by sampling real rendered pixels and finding they matched a gamma-space blend, not a linear-light one, which had been off by a factor of roughly 2x in relative luminance for the cases checked). Get the *actual* computed/rendered colour from the live page (`getComputedStyle`, or a screenshot pixel-sampled with ImageMagick - `magick file.png -crop 1x1+X+Y txt:-`) rather than assuming a component's formula, especially for anything using a daisyUI variant like `alert-soft` whose exact colour math isn't documented.

## Styling

The site uses [Tailwind CSS](https://tailwindcss.com/) and [daisyUI](https://daisyui.com/) for layout and components (timeline, badges, modal, theme switching). This has a build step, but only for people editing styles - the committed `css/app.css` is what ships, and viewing the site needs nothing beyond a static file server (see "Local preview" below).

If you're changing markup (adding a new daisyUI component class to `index.html` or `fdp/index.html`, say) or editing `css/tailwind.css` itself, install the dev dependencies once and rebuild:

```sh
npm install
npm run build:css
```

`npm run build:css` runs the Tailwind CLI, scans the HTML/JS for class names in use, and writes a minified `css/app.css`. Commit the regenerated `css/app.css` alongside whatever markup change prompted it - a stale `app.css` silently drops styles for classes added since the last build.

Two daisyUI themes are enabled: `corporate` (light, default) and `business` (dark, used when the visitor's OS prefers dark mode or they've toggled it). The theme toggle button (`[data-theme-toggle]` in `js/theme-toggle.js`) persists the choice to `localStorage` under the `nhse-theme` key, read by a small inline `<head>` script on each page to avoid a flash of the wrong theme. Keep the two theme names in sync between `css/tailwind.css`'s `@plugin "daisyui"` line and `js/theme-toggle.js`'s `LIGHT`/`DARK` constants if either changes.

`css/layout.css` is a second, separate stylesheet, hand-written and **not** run through the Tailwind CLI - it's committed as-is and needs no build step. It exists because this project's Tailwind v4 + daisyUI 5 build was found to silently drop certain responsive (`lg:*`) utility rules from the parsed stylesheet in the browser (present correctly in the compiled `css/app.css` text, but missing from the live CSSOM) - not yet root-caused upstream. The FDP timeline's responsive sidebar layout (`.fdp-layout`, `.fdp-sidebar`, `.fdp-footer`, and the `min-width: 64rem` breakpoint) lives there instead. If a future Tailwind/daisyUI utility class silently fails to apply the same way, add the equivalent plain CSS rule to `css/layout.css` rather than fighting the build.

Separately: `js/app.js` builds some class names dynamically (e.g. `` `btn-${color}` `` from `KIND_COLOR`). Tailwind's scanner only generates CSS for class names it can find as complete literal text in a source file - it can't see the result of string interpolation, so a dynamically-built class name silently produces no rule at all (this went unnoticed for some time; every per-kind colour rendered as plain grey until caught). `js/app.js`'s `TAILWIND_DYNAMIC_CLASS_SAFELIST` array exists solely to give the scanner that literal text; it's never read at runtime. If you add a new colour to `KIND_COLOR`, add its `btn-`/`badge-`/`bg-`/`border-l-` variants to that array too, or it won't render.

## Local preview

The site is static and reads `fdp/index.json` plus each entry's YAML directly in the browser - no build step needed just to view it (see "Styling" above for when a CSS rebuild is needed). The root `index.html` is a landing page linking to each utility (the FDP timeline lives at `/fdp/`); serve the repo root with any static file server, e.g.:

```sh
python3 -m http.server 8000
```

Then open `http://localhost:8000/fdp/` (or `http://localhost:8000/` for the landing page).

## URL querystring convention

The FDP site's filters, search, sort order, and currently open card all round-trip through the URL, so a filtered view - or a single card - is a shareable link. Any future topic site in this repo should use the same four parameters, so links behave consistently across the whole project:

| Param | Example | Notes |
|---|---|---|
| `tags` | `?tags=nhse,parliament` | Comma-separated, ANDed together (all must match, not any). Omit entirely when no filter is active. |
| `q` | `?q=opt-out` | Free-text search string. Omit when empty. |
| `sort` | `?sort=asc` | Only written when it differs from the site's default (`desc`, newest-first, on the FDP site) - keeps default-state URLs clean. |
| `entry` | `?entry=2023-11-21-fdp-contract-awarded` | An entry `id`. Opens that card's modal on load. Written while the card is open, removed when it's closed. Every open card shows its own "permalink" link pre-filled with this. |

Read once on load, written back with `history.replaceState` (not `pushState`) on every change, so adjusting filters - or opening/closing a card - doesn't spam the browser's back button. See `js/app.js`'s `readStateFromURL` / `writeStateToURL` for the reference implementation.

A card's `related` list (see the entry schema above) is rendered as clickable links to the other cards, using this same mechanism - so related entries are mutually navigable, not just mutually mentioned.

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
