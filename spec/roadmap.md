# Repo roadmap: beyond the FDP timeline

The FDP timeline (`spec/fdp-timeline.md`) is the first topic this repo tackles, not the only one it's for. This file is where the wider ambition for `nhse` gets written down before it's scoped into anything concrete - notes, not commitments. See `CONTRIBUTING.md` for how a new topic gets its own folder and spec once it's ready to build.

## The idea: an atlas of vendor capture

Individual facts about who influences NHS procurement and policy are mostly already public. Registers of interests. Registers of ministers' and officials' meetings with external organisations. Business appointment rules clearances. Companies House filings. None of this is secret. What's missing is a place that joins it up.

Each of these registers is published separately, by a different body, usually as a quarterly PDF or an HTML table with no stable identifiers, no cross-references, and no way to ask "show me everyone who sat on a board that dealt with Vendor X while also having a declared interest in Vendor X, or who left an NHS role and joined Vendor X within a year, or whose meetings register shows them meeting Vendor X's lobbyists the quarter before a contract was awarded." Spotting that pattern today means manually reading years of separate documents and holding the cross-references in your head. That difficulty is probably not deliberate obstruction in the way the UKGWA search cap turned out to be (see `s/fetch-blog-index`), but the effect is similar: the data exists, and almost nobody can practically use it.

The atlas is the project of turning "technically public" into "actually queryable" - entity-resolving people and organisations across registers, and surfacing timeline-shaped patterns (meetings, appointments, declarations, departures, contract awards) rather than requiring a reader to assemble them by hand.

### Candidate source registers

Not yet assessed for what's actually scrapeable or how far back each goes. A first pass, roughly in order of likely yield. Check each off once it's been assessed for scrapeability; remove the line once it's actually been worked into entries (the detail belongs in the topic's own spec by then, not here).

- [ ] **DHSC and NHS England ministerial/official meetings with external organisations** - published quarterly as transparency returns (gov.uk "transparency data"). Lists date, attendees, organisation, and a one-line purpose. The purpose line is usually too vague to be useful alone, but the date and organisation pairing is the raw material for timeline cross-referencing.
- [ ] **Registers of interests** - NHS England board, ICB boards, and equivalent DHSC registers. Declared shareholdings, directorships, and other interests, refreshed periodically. The register entry itself is usually just a name and an organisation, no date range - so "when did this interest start" often isn't recorded, only "that it currently exists."
- [ ] **Pre-appointment employment** - usually only reconstructable from CVs, LinkedIn, press coverage of the appointment, or Digital Health / HSJ profile pieces, not from a single register. `people/` role-timeline entries now carry `organisation_type` and `supplier_match_name` on each role for exactly this (see "Adding or extending a person entry" in `CONTRIBUTING.md`); what's still missing is actually populating pre-appointment roles for anyone beyond Ming Tang, and most of NHS England's senior leadership has no `people/` entry at all yet.
- [ ] **Post-departure employment and ACOBA** - the Advisory Committee on Business Appointments publishes its advice on senior civil servants' and some NHS officials' new roles after leaving public service, including the employer and any conditions attached. This is the cleanest single source for "revolving door" moves, where it covers the person at all - ACOBA's remit has gaps (NHS England board members' coverage, for instance, needs checking).
- [ ] **Companies House** - directorships, persons with significant control, and incorporation dates for vendors and the companies people move to/from. Good for confirming a departure-to-directorship link with a precise date.
- [ ] **Lobbying registers** - the Office of the Registrar of Consultant Lobbyists covers consultant lobbyists only, which excludes most in-house corporate affairs teams; worth checking what it actually captures for FDP-relevant vendors before relying on it.
- [ ] **FOI disclosures** - already a source for the FDP timeline (see "Sources to work through" in `spec/fdp-timeline.md`); likely to surface meeting records, internal emails about a vendor relationship, or declarations not otherwise published. Specifically: NHS England, NHSX, and NHS Digital each ran (or run) their own FOI disclosure log - publicly published request-and-response pairs. NHSX and NHS Digital no longer exist as separate bodies (merged into NHS England), but their disclosure logs are historical record and worth pulling in full, not just searching for FDP-relevant hits - the whole corpus is useful raw material for this topic and for the vendor-capture atlas, and nobody else has pulled it into one place with archive links.
- [ ] **Office for Statistics Regulation casework** - OSR's casework/correspondence archive covers any public body's statistical claims, not just NHS England's. Worth a periodic check for new NHS-related findings (see `spec/fdp-timeline.md` R16 for the first one, on FDP benefit claims).

### Why this is hard, honestly

- **No stable identifiers.** The same person appears under slightly different name spellings, with or without titles, across registers published by different bodies in different formats. Entity resolution is most of the work.
- **No date ranges on most declarations.** A register of interests tells you an interest exists at the time of publication, not when it started or ended. Treat declared-interest entries as `quarter` or even wider precision unless a clearer date is independently available.
- **Scale.** This is not "read ten PDFs." It's potentially hundreds of organisations' worth of registers, repeated quarterly, over years. Any approach that depends on reading everything by hand doesn't scale - this will need scripted extraction per source, same as `s/fetch-blog-index` and `s/fetch-transcripts`, before any pattern-spotting is possible.
- **The pattern, not the fact, is the finding.** A single declared interest or a single meeting is not a story. The timeline-worthy fact is the *co-occurrence* - meeting date near contract-award date, departure date near appointment-to-vendor date. That means this topic's entries will often need to *link* two otherwise-unremarkable facts from two different registers, which is a different shape of entry from the FDP timeline's "one dated event, one source."

### How this would fit the existing repo shape

Likely structure, not yet built:

- `vendor-capture/` (name TBC) as a new top-level topic folder, following the `<topic>/entries/*.yaml` + `<topic>/index.json` pattern from `CONTRIBUTING.md`.
- Heavy reliance on `people/` - probably needs new fields (`previous_employer`, `declared_interests`, `recorded_meetings`) rather than a parallel person schema.
- A new entry category or schema shape for "linked pair" findings, since the FDP timeline's one-event-one-source entry schema doesn't naturally fit "X met Y in March, Z was awarded the contract in June."
- Scripted fetchers per register, named `s/fetch-<register>`, following the pattern already established.

### Open questions

- [ ] **Scope.** Every NHS vendor, or start with Palantir/FDP-adjacent vendors and expand once the method is proven? Starting narrow and proven seems safer than starting broad and stalling.
- [ ] **Editorial discipline.** The FDP timeline's "facts not arguments" discipline gets harder here, because the whole point is spotting a pattern a reader is meant to find suspicious. Need an explicit equivalent of the "contested" field and the "no speculation about motive" rule from `spec/fdp-timeline.md`, adapted for linked-fact entries - report the co-occurrence, not the inference.
- [ ] **Where this starts.** Not scoped into FDP timeline roadmap items. Needs its own spec once someone's ready to build it, written the way `spec/fdp-timeline.md` was: purpose, schema, source list, roadmap, open questions.

## Operating principle: every fetcher is idempotent and re-runnable

This applies across the whole repo, not just the vendor-capture idea - it's how `s/fetch-transcripts` and `s/fetch-blog-index` already work, and every future source fetcher should follow the same shape.

For any ongoing source - FOI disclosure logs, board papers, board-meeting transcripts, registers of interest, meeting transparency returns, whatever comes next - the fetcher script should be:

- **Deterministic.** Same inputs, same outputs. No fetcher should depend on being run in a particular order relative to another, or on state that isn't either in the repo or in the source itself.
- **Idempotent.** Running it again when nothing's changed upstream should be a no-op (or close to one) - it checks what's already present, fetches only what's missing or changed, and doesn't duplicate or corrupt existing data. `s/fetch-transcripts` dedupes by video ID already on disk; `s/fetch-blog-index` checkpoints and resumes. New fetchers should do the equivalent for their source.
- **Safe to schedule unattended.** The point of the above two properties is that a fetcher can be run on a cadence - monthly is the default assumption - without a human needing to watch it or clean up afterwards if it's interrupted or re-run.

Two ways to actually run these on a schedule, neither built yet:

- [ ] **GitHub Actions**, on a cron schedule, committing any new data straight back to the repo (or opening a PR for review, if a source is judged to need a human check before merging). The natural long-term home for this once a fetcher is stable and trusted.
- [ ] **An overnight agent run** - the same scripts, run by an agent session rather than a workflow, useful before a source is stable enough to trust unattended in CI, or where a source genuinely needs judgement calls (e.g. deciding whether a cross-register match is worth a vendor-capture entry) that a plain script shouldn't make on its own.

Either way, the fetcher itself should not care which one is calling it - it is a dumb, idempotent, scriptable layer, and the judgement calls (what's worth an entry, how to phrase it, whether a `contested` field is needed) happen afterwards, by a human or an agent working from what the fetcher gathered. Keep that separation. Don't let a fetcher script start making editorial decisions.
