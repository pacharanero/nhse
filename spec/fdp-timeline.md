# Spec: FDP Timeline

## Purpose

A single, filterable, vertical timeline of the NHS Federated Data Platform, from the Palantir COVID-19 datastore contract through to the 2027 break clause, built from primary sources and linked quotes.

The timeline is a **research and accountability artefact**, not an argument. Each entry states what happened, on what date, with a link to the source. Interpretation belongs in the episode, the article, or a clearly-marked annotation - never in the entry itself.

## What this is not

- Not a campaign site. It does not tell the reader what to conclude.
- Not a Palantir dossier. FDP decisions made by NHS England, DHSC and ministers are as much in scope as anything the supplier did.
- Not a news aggregator. An item earns a place because it is a documented event, decision, statement, or disclosure - not because someone published an opinion about one.

## Status

The timeline is live (R12/R13) at <https://pacharanero.github.io/nhse/>, built from `fdp/entries/*.yaml` via `s/build-index` (R3). Data gathering continues alongside the published site - see the roadmap below for what's worked and what's open.

- NHS England board meeting captions, 2013-2026, in `nhs-board-transcripts/`. See `s/fetch-transcripts` and `s/search`.
- 45 entries in `fdp/entries/`, spanning March 2018 to February 2027 (future-dated: the break clause deadline). Every entry is checked against its linked, archived source before being added.

## Tags (the colour/filter dimension)

Originally this was a single exclusive `category` field (R3-era decision). Replaced by a `tags` list - every entry carries one or more tags, and can be filtered by any combination, ANDed together (see `CONTRIBUTING.md`'s "Tags" section for the mechanics). Two kinds of tag:

**Kind tags** - the original seven categories, now the first tag in an entry's list, still exclusive in practice (an entry has one) because they drive the entry's colour and which side of the timeline it renders on:

| Key | Kind | Covers |
|---|---|---|
| `scope` | Scope | What data is in and out: GP data, primary care, direct care vs secondary use, opt-out definition, use cases added or withdrawn. |
| `contract` | Contract & procurement | The COVID-19 datastore contracts, the £1 emergency award, extensions, the FDP tender, the award, contract value changes, the 2027 break clause. |
| `official` | Official communication | NHS England and DHSC blogs, board papers, ministerial statements, Tim Ferris and successor posts, FAQs, press releases. What was claimed, and when. |
| `media` | Media revelation | Investigative reporting that disclosed something not previously public. |
| `board` | Board meeting quote | Targeted quotes from NHS England board meetings, with video timestamp. |
| `legal` | Legal, regulatory & parliamentary | Judicial review, ICO, National Data Guardian, select committee sessions, Westminster Hall debates, petitions, FOI outcomes. |
| `civil` | Civil society | Campaign launches, petitions, open letters, professional body positions. |

Two kind tags were folded in deliberately rather than split out:

- Petitions carry `civil` when launched and `legal` when they trigger a parliamentary response. Record the response as a separate entry.
- Blogs by named officials carry `official`, not `media`, even when published on a personal site, because the point is what the institution was saying at the time.

**Free tags** - everything else an entry carries alongside its kind tag: organisations (`nhse`, `nhsx`, `nhsd`, `dhsc`...), named people, topics (`opt-out`, `break-clause`, `cost`...), source outlets. No fixed vocabulary - see what's already in use before inventing a near-duplicate. This is the dimension that makes cross-cutting queries possible ("show me every `parliament` entry that's also tagged `break-clause`"), which a single exclusive category never could.

## Entry schema

One record per event, stored as YAML under `fdp/entries/` (decided by R3 below).

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Stable slug, e.g. `2023-11-21-fdp-contract-awarded`. Never reused or renumbered. |
| `date` | yes | ISO `YYYY-MM-DD`. See date precision below. |
| `date_precision` | yes | `day`, `month`, or `quarter`. Renders differently; prevents false precision. |
| `tags` | yes | List, at least one. First tag should be a kind tag (table above); any further tags are free-form. |
| `title` | yes | Factual, under ~90 chars. No adjectives. |
| `summary` | yes | 1-3 sentences. What happened. Not why it matters. |
| `quote` | no | Verbatim, with speaker and role at the time. |
| `quote_verified` | if `quote` | `audio`, `document`, or `secondary`. See verification below. |
| `source_url` | yes | Primary source where possible. |
| `source_title` | yes | Publication or body, and headline. |
| `archive_url` | yes | Wayback or archive.today capture. Non-negotiable - see link rot below. |
| `paywalled` | no | Boolean. Drives the reader-facing note. |
| `video_id` / `t` | no | For `board` entries: YouTube ID and start seconds. |
| `related` | no | List of other entry `id`s. |
| `contested` | no | Free text noting a denial or dispute, so the entry carries it inline. |

### Date precision

Use the date the thing *happened*, not the date it was reported. Where a document is undated, use `month` or `quarter` precision rather than guessing a day. A timeline that silently invents day-precision dates is worse than one with visible fuzziness.

Board meeting entries have two dates: the meeting date (use this) and the YouTube upload date (usually a few days later). Transcript filenames use upload date because it is machine-reliable; the timeline must use the meeting date from the title.

### Verification levels

- `audio` - someone listened to the recording and transcribed it. Required for any board-meeting quote that will be broadcast or published.
- `document` - taken from a published document, paper, or transcript of record (Hansard).
- `secondary` - quoted by a journalist, not independently verified. Must be attributed as such in the rendered view: "as reported by the FT".

Auto-generated YouTube captions are **not** a verification level. They are a search index. The known failure modes are mistranscribed names, dropped words, and garbled acronyms - the 7 December 2023 meeting renders "opt-outs" as "ops out". Every caption-derived quote starts at `secondary` and is promoted to `audio` only after someone plays the video.

### Contested claims

Where a party denies something, the denial goes in the same entry, not a separate one. Microsoft's denial belongs next to the ICC email story; Epic's denial belongs next to the FTC report; NHS England's "no expectation that changes would be made" belongs next to the national data guardian FOI emails. An entry that reports an allegation without its denial is a defect, not an editorial choice.

## Sources to work through

Listed in rough order of expected yield. For each, the task is to extract dated entries, not to archive the whole site.

### Primary - documents and proceedings

- **NHS England board papers and minutes** - england.nhs.uk publishes papers alongside each meeting. These pair directly with the transcripts already gathered and are the highest-value unworked source.
- **Parliamentary petitions** - petition.parliament.uk. Capture launch date, signature count at close, government response date and text, and any Westminster Hall debate triggered.
- **Hansard** - the 16 April 2026 Westminster Hall debate and any committee sessions. Hansard is the citable record; the video is the illustration.
- **Contracts Finder / Find a Tender** - award notices, values, and variations. The authoritative record of the `contract` category.
- **FOI disclosures** - NHS England's disclosure log, plus FOI material obtained by others (the national data guardian emails obtained by the FT, the Engineering Board disclosure).
- **ICO and National Data Guardian** - published correspondence, statements, and the NDG's own blog posts. Archive both draft and published versions where a rewrite is alleged.
- **Office for Statistics Regulation (OSR)** - casework findings and correspondence on NHS England's and DHSC's statistical claims. The FDP benefits/methodology pages on england.nhs.uk are themselves primary sources worth re-checking periodically, since NHS England revises the stated methodology (baseline calculation, caveats) without necessarily flagging the change prominently - see R16.

### Campaign and civil society

- **Foxglove** - foxglove.org.uk. Litigation threats, judicial review, published correspondence, and their own document releases. Named by Ming Tang at the December 2023 board meeting as a driver of opt-outs, which makes their timeline directly relevant.
- **medConfidential** - long-running, meticulously dated, and often the earliest source on scope changes.
- **38 Degrees** - petition launches and signature milestones.
- **openDemocracy** - sustained investigative coverage of the COVID-19 datastore contracts, much of it obtained by FOI. Likely the strongest single source for the 2020-2021 period.
- **Professional bodies** - RCGP, BMA, Royal Colleges. Position statements and letters.

### Media

- **Guardian** - open access, well dated, good on the political and revolving-door strands.
- **Independent** - open access.
- **FT** - paywalled. See below.
- **HSJ** - paywalled, but the trade record is often the earliest.
- **Computer Weekly** - open access, and the venue for the five-part series noted in the Bartlett research.
- **Democracy for Sale / Byline Times** - lobbying and political finance angles.

### Paywalled sources - handling

The FT and HSJ carry material that exists nowhere else, and the timeline is weaker without it.

I am not going to build anything that circumvents a paywall, and the repo should not contain scrapers that do. Beyond the legal exposure, a public accountability project that is itself built on unauthorised access hands its critics the easiest possible rebuttal, and the whole value of this timeline is that it is unimpeachable on the facts.

What works instead, in order of preference:

1. **Read it on your own subscription and extract by hand.** The timeline needs a date, a headline, a URL and at most a short quotation - not the article body. This is the normal path and it is not onerous.
2. **Quote briefly with attribution.** Short quotation for reporting and criticism is ordinary journalistic practice. Keep quotes to what the point requires, always attributed, always linked.
3. **Archive the metadata, not the text.** Headline, byline, date, URL, and an archive link. `paywalled: true` tells the reader they will hit a wall.
4. **Follow the FT's own syndication and republication terms** where a longer excerpt is genuinely needed.
5. **Library and institutional access.** Many FT and HSJ articles are reachable through NHS Athens, university subscriptions, or public library services.
6. **Find the primary document.** FT and HSJ stories are frequently built on an FOI disclosure, a contract notice, or a board paper. The underlying document is usually obtainable directly, is better evidence, and is not paywalled. Where the FOI response is not published, request it.

Route 6 is the one worth institutionalising: for every paywalled story in the timeline, record what the underlying primary source is and whether it has been obtained. That turns the paywall from a blocker into a research queue.

### Link rot

Every entry gets an `archive_url` at the point of entry, not later. NHS England has restructured its site repeatedly, and several FDP-era pages already 404. Submit to the Wayback Machine at capture time. An entry without an archive link is incomplete.

## Roadmap

Legend: `[x]` done, `[~]` in progress, `[ ]` not started

- [x] **R1 - Gather NHS England board meeting captions** with an idempotent, resumable fetcher.
- [~] **R2 - Backfill the full 2013-2026 caption archive** and record which meetings have no usable caption track.
- [x] **R3 - Decide the entry storage format.** Decided: YAML per entry, one file per id, under `fdp/entries/`. `s/build-index` regenerates `fdp/index.json` (required fields, unique ids, ISO dates, archive_url present) - see `CONTRIBUTING.md`.
- [~] **R4 - Write the first 20 entries** covering the contract spine (`contract` category, 2020 COVID datastore to the 2023 award/award notice). 15 entries written and sourced so far, covering the full spine from the initial £1 COVID-19 Data Store contract to the December 2023 Contract Award Notice. Two further entries (`media` category) cover Thiel's and Karp's public statements as context on the FDP supplier. Reaching exactly 20 within `contract` category alone would mean either padding with weak near-duplicates (e.g. separate entries for each COVID-datastore supplier's contract with no distinguishing facts) or widening into `legal`/`media`/`civil` territory that belongs to R5-R8.
- [~] **R5 - Extract board-meeting quotes** for FDP, Palantir, opt-out, and data-sharing across all gathered transcripts, as `secondary` entries with timestamps. First pass done: searched `federated data platform`, `palantir`, `opt.?out`, `foxglove`, `thiel`, `consent` across all 217 fetched transcripts. Two entries added from the richest meeting found (7 December 2023 - the same meeting flagged in the caption-reliability note): the board being told of the award, and Ming Tang's answer on opt-out levels post-award. Most other FDP-related board mentions found were passing references with no new fact over what's already in `contract`/`legal` entries - not every hit is worth an entry. `data-sharing` and wider terms (`consent`, `care.data`) not yet systematically worked beyond what surfaced incidentally.
- [ ] **R6 - Promote the highest-value board quotes to `audio`** by listening and transcribing properly.
- [~] **R7 - Work openDemocracy and Foxglove** for the 2020-2021 COVID datastore period. The core thread is in: the Feb 2021 judicial review launch, the March 2021 government concession, and the September 2021 end of a separate Palantir adult social care deal. Foxglove's 2023 FDP-specific campaign and legal action are also in. Not yet covered: the fuller openDemocracy FOI material on the original COVID-19 datastore contracts, and Foxglove's post-2023 ongoing litigation.
- [~] **R8 - Work the petitions and Hansard** strand. The 16 April 2026 Westminster Hall debate is in, as the full-debate entry plus a separate scope entry for one specific claim raised in it (the unpublished s.254 Health and Social Care Act 2012 direction said to underpin the opt-out exemption). That Hansard page was unusually hard to archive - archive.org's crawler failed against the live page repeatedly (likely because it's heavily JS-rendered), and the entry ended up sourced to an older capture from before the page changed. Petitions (petition.parliament.uk) not yet touched.
- [ ] **R9 - Add board papers** alongside each board-meeting entry.
- [ ] **R10 - Build the paywalled-source research queue**: for each, identify and pursue the underlying primary document.
- [~] **R11 - Validation script.** `s/build-index` already checks required fields, ISO dates, unique ids, archive_url presence, and quote/quote_verified pairing as a side effect of regenerating the index. Not yet split into a standalone `s/validate`, and doesn't yet check `related` ids resolve or `contested` denials are present where expected.
- [x] **R12 - Render the vertical timeline** with category colours and filter toggles. `index.html` + `css/style.css` + `js/app.js`, static, no build step - reads `fdp/index.json` and the entry YAML directly in the browser. Hover/click cards show full entry detail (quote, contested, sources, related). Quarter-precision date rendering is still a stub pending real quarter-precision entries.
- [x] **R13 - Decide publication and licensing.** Decided: the repo is public, and the timeline is live via GitHub Pages at <https://pacharanero.github.io/nhse/>. Open question 2 below (transcript licensing) was not separately resolved before this - it's now a live question about content that is actually public, not a hypothetical one, and should be revisited.
- [x] **R14 - Let readers propose entries without needing git/YAML.** The site footer and this repo's [issue template](../.github/ISSUE_TEMPLATE/new-entry.yml) (`Propose an entry`) let anyone open a GitHub Issue with just a link and a sentence or two - deliberately low-friction, nothing required beyond a title, so it shifts the write-up work to whoever actions the issue rather than asking a casual reader to learn the schema first. No longer gated on R13 - the repo is public.
- [x] **R15 - Tags, sort order, and shareable filtered views.** Replaced the single exclusive `category` field with a `tags` list (all 42 entries migrated; see "Tags" above and in `CONTRIBUTING.md`). Site now has: a sort toggle, newest-first by default (so a visitor doesn't land on 2018); a "today" marker line so past and future entries (the break clause, dated 2027) are visually distinguished regardless of sort direction; a tag filter that ANDs selections together, intended for surfacing overlaps rather than just narrowing by type; and a URL querystring convention (`?tags=...&q=...&sort=...`) that round-trips full filter state, documented in `CONTRIBUTING.md` as a pattern for future topic sites to reuse.
- [~] **R16 - Statistics watchdog strand: NHS England's efficacy claims.** Three entries added: the November 2023 public explainer stating FDP benefit figures (theatre use, length-of-stay reductions) as plain fact with no causality caveat; the July 2026 BMJ report (FOI-sourced) that a third of "live" trusts hadn't logged into FDP apps in a year, contradicting officials' use of the "live trust" count as a success metric; and the OSR's 22 July 2026 casework finding that NHS England's benefit claims needed an explicit "cannot draw conclusions about cause and effect" caveat, with the regulatory remedies it required. The underlying WhatDoTheyKnow FOI request/response behind the BMJ piece could not be archived (archive.org returning HTTP 520 against whatdotheyknow.com, same failure mode as the Hansard page in R8) - still needs a manual capture before it can be added as its own entry.

## Open questions

These need decisions, not guesses.

1. ~~**Repo visibility.**~~ Resolved: the repo is public and the timeline is live on GitHub Pages.
2. **Transcript licensing - now live, not hypothetical.** The caption files in `nhs-board-transcripts/` are derived from NHS England's YouTube uploads and are publicly readable in this repo right now. NHS England content is typically Open Government Licence, but the YouTube uploads are under YouTube's standard licence unless stated otherwise, and OGL coverage of auto-generated captions is untested. This was flagged as "resolve before publishing the transcript corpus" - the repo going public happened without a separate decision on this. Worth a deliberate look rather than leaving it as an accidental default.
3. **Naming individuals.** The timeline will name people in `official` and `board` entries. The discipline from the EDH episode briefs applies: documented facts only, denials carried inline, no speculation about motive or future employment. Worth writing down as an explicit editorial policy file before R12.
4. ~~**Where the break clause sits.**~~ Resolved: `fdp/entries/2027-02-15-fdp-break-clause-deadline.yaml`, dated and sourced to the Science, Innovation and Technology Committee's report (which cites the Contracts Finder notice). Renders like any other entry, future-dated - no special "marker" treatment built. Still open: whether the government must act by that date or whether it marks contract-term expiry with some decision lead time before it; none of the sources found so far say which.
5. **Relationship to the EDH episodes.** This repo is the evidence base; the episodes are the argument. Keep them separate, and link from episode planning files to timeline entry ids rather than duplicating research.

## Related work

- `~/marcusbaw@gmail.com/youtube+podcasts/everything-digital-health/episodes/in-planning/why-does-fdp-need-so-much-lobbying/` - the episode this evidence base primarily serves, including the FOI/national data guardian material and the December 2023 board clip.
- `.../2026.06.28-tom-bartlett-fdp-conflicts-and-media-rollout/` - conflict-of-interest research, with editorial cautions that apply here too.
