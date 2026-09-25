# Spec: FDP Timeline

## Purpose

A single, filterable, vertical timeline of the NHS Federated Data Platform, from the Palantir COVID-19 datastore contract through to the 2027 break clause, built from primary sources and linked quotes.

The timeline is a **research and accountability artefact**, not an argument. Each entry states what happened, on what date, with a link to the source. Interpretation belongs in the episode, the article, or a clearly-marked annotation - never in the entry itself.

## What this is not

- Not a campaign site. It does not tell the reader what to conclude.
- Not a Palantir dossier. FDP decisions made by NHS England, DHSC and ministers are as much in scope as anything the supplier did.
- Not a news aggregator. An item earns a place because it is a documented event, decision, statement, or disclosure - not because someone published an opinion about one.

## Phase 1: data gathering (current phase)

The only goal right now is to accumulate sources and extract dated, quotable facts. Do not build the visualisation yet. An incomplete timeline rendered beautifully is worse than a complete corpus in a spreadsheet.

Done so far:

- NHS England board meeting captions, 2013-2026, in `nhs-board-transcripts/`. See `s/fetch-transcripts` and `s/search`.

## Categories (the colour/filter dimension)

Every entry carries exactly one category. These are the filter toggles in the final view.

| Key | Category | Covers |
|---|---|---|
| `scope` | Scope | What data is in and out: GP data, primary care, direct care vs secondary use, opt-out definition, use cases added or withdrawn. |
| `contract` | Contract & procurement | The COVID-19 datastore contracts, the £1 emergency award, extensions, the FDP tender, the award, contract value changes, the 2027 break clause. |
| `official` | Official communication | NHS England and DHSC blogs, board papers, ministerial statements, Tim Ferris and successor posts, FAQs, press releases. What was claimed, and when. |
| `media` | Media revelation | Investigative reporting that disclosed something not previously public. |
| `board` | Board meeting quote | Targeted quotes from NHS England board meetings, with video timestamp. |
| `legal` | Legal, regulatory & parliamentary | Judicial review, ICO, National Data Guardian, select committee sessions, Westminster Hall debates, petitions, FOI outcomes. |
| `civil` | Civil society | Campaign launches, petitions, open letters, professional body positions. |

Two categories were folded in deliberately rather than split out:

- Petitions sit under `civil` when launched and `legal` when they trigger a parliamentary response. Record the response as a separate entry.
- Blogs by named officials sit under `official`, not `media`, even when published on a personal site, because the point is what the institution was saying at the time.

## Entry schema

One record per event. Store as YAML or TSV in `data/`; the format decision is R3 below.

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Stable slug, e.g. `2023-11-21-fdp-contract-awarded`. Never reused or renumbered. |
| `date` | yes | ISO `YYYY-MM-DD`. See date precision below. |
| `date_precision` | yes | `day`, `month`, or `quarter`. Renders differently; prevents false precision. |
| `category` | yes | One of the keys above. |
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
- [ ] **R3 - Decide the entry storage format.** YAML per entry vs one TSV. Leaning YAML-per-entry for reviewable diffs and multi-line quotes; TSV is easier to sort and eyeball. Decide before 50 entries exist, not after.
- [ ] **R4 - Write the first 20 entries** covering the contract spine only (`contract` category, 2020 COVID datastore to the 2023 award). Proves the schema against real material before broadening.
- [ ] **R5 - Extract board-meeting quotes** for FDP, Palantir, opt-out, and data-sharing across all gathered transcripts, as `secondary` entries with timestamps.
- [ ] **R6 - Promote the highest-value board quotes to `audio`** by listening and transcribing properly.
- [ ] **R7 - Work openDemocracy and Foxglove** for the 2020-2021 COVID datastore period.
- [ ] **R8 - Work the petitions and Hansard** strand.
- [ ] **R9 - Add board papers** alongside each board-meeting entry.
- [ ] **R10 - Build the paywalled-source research queue**: for each, identify and pursue the underlying primary document.
- [ ] **R11 - Validation script** (`s/validate`): schema conformance, required fields, ISO dates, unique ids, archive_url present, quotes carry a verification level.
- [ ] **R12 - Render the vertical timeline** with category colours and filter toggles. Static site, no build step if avoidable.
- [ ] **R13 - Decide publication and licensing** before anything goes public. See open questions.

## Open questions

These need decisions, not guesses.

1. **Repo visibility.** Private while gathering is the safe default. Publication needs a deliberate decision, especially given entries that name living individuals.
2. **Transcript licensing.** The caption files are derived from NHS England's YouTube uploads. NHS England content is typically Open Government Licence, but the YouTube uploads are under YouTube's standard licence unless stated otherwise, and OGL coverage of auto-generated captions is untested. Resolve before publishing the transcript corpus. The timeline entries themselves - our own prose plus short quotations - are a much easier case than republishing 225 full transcripts.
3. **Naming individuals.** The timeline will name people in `official` and `board` entries. The discipline from the EDH episode briefs applies: documented facts only, denials carried inline, no speculation about motive or future employment. Worth writing down as an explicit editorial policy file before R12.
4. **Where the break clause sits.** The 2027 break clause is the timeline's endpoint and its reason for existing. Decide whether to render it as a fixed future marker.
5. **Relationship to the EDH episodes.** This repo is the evidence base; the episodes are the argument. Keep them separate, and link from episode planning files to timeline entry ids rather than duplicating research.

## Related work

- `~/marcusbaw@gmail.com/youtube+podcasts/everything-digital-health/episodes/in-planning/why-does-fdp-need-so-much-lobbying/` - the episode this evidence base primarily serves, including the FOI/national data guardian material and the December 2023 board clip.
- `.../2026.06.28-tom-bartlett-fdp-conflicts-and-media-rollout/` - conflict-of-interest research, with editorial cautions that apply here too.
