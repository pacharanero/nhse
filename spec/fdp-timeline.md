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
- [x] **R12 - Render the vertical timeline** with category colours and filter toggles. `index.html` + `css/app.css` + `js/app.js`, reads `fdp/index.json` and the entry YAML directly in the browser - no build step to *view* the site (see R18 for the CSS build step). Click a card to open a modal with full entry detail (quote, contested, sources, related). Quarter-precision date rendering is still a stub pending real quarter-precision entries.
- [x] **R13 - Decide publication and licensing.** Decided: the repo is public, and the timeline is live via GitHub Pages at <https://pacharanero.github.io/nhse/>. Open question 2 below (transcript licensing) was not separately resolved before this - it's now a live question about content that is actually public, not a hypothetical one, and should be revisited.
- [x] **R14 - Let readers propose entries without needing git/YAML.** The site footer and this repo's [issue template](../.github/ISSUE_TEMPLATE/new-entry.yml) (`Propose an entry`) let anyone open a GitHub Issue with just a link and a sentence or two - deliberately low-friction, nothing required beyond a title, so it shifts the write-up work to whoever actions the issue rather than asking a casual reader to learn the schema first. No longer gated on R13 - the repo is public.
- [x] **R15 - Tags, sort order, and shareable filtered views.** Replaced the single exclusive `category` field with a `tags` list (all 42 entries migrated; see "Tags" above and in `CONTRIBUTING.md`). Site now has: a sort toggle, newest-first by default (so a visitor doesn't land on 2018); a "today" marker line so past and future entries (the break clause, dated 2027) are visually distinguished regardless of sort direction; a tag filter that ANDs selections together, intended for surfacing overlaps rather than just narrowing by type; and a URL querystring convention (`?tags=...&q=...&sort=...`) that round-trips full filter state, documented in `CONTRIBUTING.md` as a pattern for future topic sites to reuse.
- [x] **R16 - Statistics watchdog strand: NHS England's efficacy claims.** Four entries: the November 2023 public explainer stating FDP benefit figures (theatre use, length-of-stay reductions) as plain fact with no causality caveat; the July 2026 BMJ report (FOI-sourced) that a third of "live" trusts hadn't logged into FDP apps in a year, contradicting officials' use of the "live trust" count as a success metric; the OSR's 22 July 2026 casework finding that NHS England's benefit claims needed an explicit "cannot draw conclusions about cause and effect" caveat, with the regulatory remedies it required; and the underlying FOI usage dataset itself, including a rough cost-per-login calculation (this repo's own arithmetic, clearly labelled as such, not an official figure).
- [x] **R17 - `fdp/sources/` fallback for archive.org-blocked pages.** The WhatDoTheyKnow FOI page behind R16's usage-data entry returned `HTTP 520` from archive.org's `/save/` endpoint on every attempt, from two different IPs, while other pages on the same domain (including a near-identical request) archived normally - a targeted block, not a transient failure. New convention, documented in `CONTRIBUTING.md`: retain the primary document (or a full text copy of the page) in `fdp/sources/`, and point `archive_url` at that file in this repo instead of a Wayback link, noting why in `contested`. First and so far only use: `fdp/sources/2026-foi-nhse-weekly-trust-users-by-product.{pdf,md}`.
- [x] **R18 - Adopt Tailwind CSS + daisyUI, with a light/dark theme toggle.** Replaced the hand-rolled `css/style.css` with a compiled `css/app.css` (Tailwind CSS v4 + daisyUI components: timeline, badge, modal, navbar). The hover-pinned card from R12 became a click-to-open `<dialog>` modal - more room, no off-screen overflow. Two themes enabled (`corporate` light default, `business` dark via `prefers-color-scheme` or a manual toggle persisted to `localStorage`). CSS is generated via `npm run build:css` (Tailwind CLI, dev-only dependency) and the compiled `css/app.css` is committed - viewing the site still needs no build step, only editing styles does. See "Styling" in `CONTRIBUTING.md`.
- [ ] **R19 - FDP product-by-product governance audit, and a Scope & Legal Basis thread.** Two linked strands, large enough to span many sessions - this entry exists so neither gets lost. Full spec below.

### R19 detail: FDP product-by-product governance audit

The FDP is not one thing - it's a platform plus a catalogue of individual products ("apps"), each with its own rollout, its own clinical use case, and (in principle) its own governance paperwork. Treating the FDP as a single undifferentiated entity flattens an important distinction the Scope & Legal Basis thread below depends on: a cancer-pathway tracking tool and a strategic commissioning analytics tool do not obviously sit on the same legal basis, and NHS England's public statements about "direct care" have not always been clear about which product they're describing.

**The registry**, per NHS England's Solution Exchange product catalogue (<https://www.england.nhs.uk/digitaltechnology/nhs-federated-data-platform/solution-exchange-product-catalogue/>, checked 13 October 2026 - re-check periodically, this page changes):

Trust-level products:
- Referral to treatment validation (RTT)
- Inpatients (CCS)
- Outpatients (CCS)
- Discharge planning (OPTICA)
- Cancer 360
- Patient Led Validation (PLV)
- Crisis Response
- Clinic Management and Room Booking (CMRB)
- Shared Patient Tracking List (SPTL)

System-level products:
- System Co-ordination Centre
- Strategic Commissioning Tool (SCT)

Note: Democracy for Sale's 14 July 2026 investigation (`2026-07-14-democracy-for-sale-project-onion-investigation`) cites FOI-sourced trust usage data for "the FDP's eight apps," which doesn't cleanly match this 9+2 list - worth reconciling when that FOI data is next consulted (it may predate a product launch or use a different grouping).

**Per-product entry, this is an event, not a stub.** Each gets a full `fdp/entries/*.yaml` entry (not an appearance-tracker dot - the user's instruction is explicit on this), kind-tagged `scope` (per the existing table: "what data is in and out ... direct care vs secondary use"), plus a dedicated free tag for the product (e.g. `cancer-360`, `optica`, `sptl` - lowercase-hyphenated, matching the product's own abbreviation where it has one). For each product, establish and cite:

1. **What it does and who uses it** - the product catalogue page itself, plus any NHS England "long read" rollout/case-study pages.
2. **DPIA (Data Protection Impact Assessment).** NHS England publishes per-product DPIAs under the FDP Information Governance Framework (confirmed to exist for at least Cancer 360 - `https://www.england.nhs.uk/publication/nhs-fdp-product-data-protection-impact-assessment-cancer-360/` - so don't assume absence without checking each product individually). Record: publication date, date of the DPIA itself (often different), and what legal basis / lawful basis it states for the processing. If no DPIA is found after checking the Information Governance Framework pages and a direct search, say so explicitly in the entry and record exactly what was checked - an unevidenced "not published" claim is as much a defect as a wrong fact.
3. **Clinical safety case.** DCB0129 (manufacturer) / DCB0160 (deploying organisation) clinical safety documentation is a statutory requirement for clinical software in the NHS. Check NHS England's FDP pages and, where a specific trust is named as an early adopter, that trust's own board papers (trusts sometimes publish clinical safety case summaries as board attachments even when NHS England doesn't centrally). Flag absence explicitly, same discipline as DPIAs.
4. **SRO, CSO, and responsible team.** Senior Responsible Owner and Chief Clinical Information Officer / Chief Safety Officer accountable for each product, and the team (often named in board papers, FDP Check and Challenge Group minutes, or the product page itself). The FDP Check and Challenge Group publishes minutes (`https://www.england.nhs.uk/publication/federated-data-platform-check-and-challenge-group-minutes-and-action-notes/`) which name specific products by product name - a likely source for this and for rollout detail.
5. **Rollout evidence.** Pilot trust(s), national rollout date(s), trust adoption count over time where stated. Cross-reference against the FOI usage data already in the repo (`2026-06-11-foi-fdp-weekly-usage-data-cost-per-login`) and the BMJ/Democracy for Sale low-adoption findings, which are about apps, not the platform as a whole - this audit should make clear which specific products those low-usage figures refer to.

**Start with Cancer 360** (explicitly requested) - a DPIA is already confirmed to exist for it, which makes it a good first test of the full checklist before applying the same discipline to the other ten products.

### R19 detail: Scope & Legal Basis thread

NHS England's public position on *why* the FDP's processing is lawful has not stayed constant, and the specific claim matters: a "direct care" classification removes the National Data Opt-Out entirely (already documented: `2026-06-04-national-data-opt-out-does-not-apply-to-fdp`), while a s251/s259 Health and Social Care Act 2012 exemption, a common-law duty to deliver a legally mandated service, a research purpose, or direct consent are each a different legal footing with different patient-facing consequences and different things a patient can be told.

The task: build a chronological cross-reference of every public statement that asserts or implies a specific legal basis, across every comms channel (official blogs, board minutes, the DPIAs surfaced by the R19 product audit above, parliamentary answers, FAQs), and note explicitly which legal basis each one claims - or, as has often been the pattern so far, how vague or how silently each one avoids naming one. This is not a new entry type - it's a lens applied when writing or reviewing entries already in scope (`scope`, `official`, `board`, `legal`), by adding the claimed legal basis to the entry's `summary` and tagging it `legal-basis-direct-care` / `legal-basis-s251` / `legal-basis-common-law` / `legal-basis-research` / `legal-basis-consent` / `legal-basis-unstated` as appropriate (new free tags - add the one that applies, don't retrofit tags onto entries where the legal basis genuinely wasn't addressed).

**The specific thing being tested for:** whether a direct-care-only classification (which legally forecloses opt-out) was being used internally or in product documentation *before* NHS England's public messaging caught up - i.e. whether Ming Tang's 7 December 2023 board answer that opt-out remains technically possible, just discouraged (`2023-12-07-board-opt-out-levels-not-materialised`, already corrected with the fuller quote) was given *after* a direct-care-only use case had already been established for the specific product(s) under discussion, which would make the "they technically still can" framing actively misleading at the time it was said, not just subsequently overtaken by events in June 2026. This requires establishing: (a) which product(s) the board discussion concerned, (b) what that product's own DPIA or scope documentation said about legal basis as of December 2023 specifically, not just the current version of the page. Wayback Machine captures of the relevant DPIA/scope pages from before and around December 2023 are the way to establish (b); if a product didn't exist yet in December 2023, that's a relevant finding too, not a dead end - it would mean the inconsistency is between the 2023 framing and a later product launch rather than within 2023 itself.

Output of this thread is not necessarily new entries on its own - it's corrections and enrichments to existing and new `scope`/`official`/`board` entries (adding the legal-basis tag and a sentence to the summary), plus, if the smoking-gun pattern above is actually confirmed, a dedicated new entry stating the finding with both sources dated and quoted side by side.

## Open questions

These need decisions, not guesses.

1. ~~**Repo visibility.**~~ Resolved: the repo is public and the timeline is live on GitHub Pages.
2. **Transcript licensing - now live, not hypothetical.** The caption files in `nhs-board-transcripts/` are derived from NHS England's YouTube uploads and are publicly readable in this repo right now. NHS England content is typically Open Government Licence, but the YouTube uploads are under YouTube's standard licence unless stated otherwise, and OGL coverage of auto-generated captions is untested. This was flagged as "resolve before publishing the transcript corpus" - the repo going public happened without a separate decision on this. Worth a deliberate look rather than leaving it as an accidental default. 

> I'd say it is unlikely to be important for the overall utility of the timeline. Standard YouTube licensing applies, and the captions are auto-generated, so the risk is minimal.

3. **Naming individuals.** The timeline will name people in `official` and `board` entries. The discipline from the EDH episode briefs applies: documented facts only, denials carried inline, no speculation about motive or future employment. Worth writing down as an explicit editorial policy file before R12.

> I think risk is low, but we should present only facts.

4. ~~**Where the break clause sits.**~~ Resolved: `fdp/entries/2027-02-15-fdp-break-clause-deadline.yaml`, dated and sourced to the Science, Innovation and Technology Committee's report (which cites the Contracts Finder notice). Renders like any other entry, future-dated - no special "marker" treatment built. Still open: whether the government must act by that date or whether it marks contract-term expiry with some decision lead time before it; none of the sources found so far say which.

> done

5. **Relationship to the EDH episodes.** This repo is the evidence base; the episodes are the argument. Keep them separate, and link from episode planning files to timeline entry ids rather than duplicating research.

> yes. separate

## Related work

- `~/marcusbaw@gmail.com/youtube+podcasts/everything-digital-health/episodes/in-planning/why-does-fdp-need-so-much-lobbying/` - the episode this evidence base primarily serves, including the FOI/national data guardian material and the December 2023 board clip.
- `.../2026.06.28-tom-bartlett-fdp-conflicts-and-media-rollout/` - conflict-of-interest research, with editorial cautions that apply here too.
