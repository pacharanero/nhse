# Spec: NHS Tech Spending Timeline

## Purpose

A timeline of major, documented NHS technology spending decisions and their outcomes - contracts awarded, programmes abandoned, costs disclosed - built from primary sources, following the same discipline as the FDP timeline (`spec/fdp-timeline.md`).

The timeline exists to support the recurring editorial argument that the NHS functions as an unusually effective "public-private wealth transfer mechanism" for technology spending specifically: large sums committed against vague benefits, tenders and final costs only loosely related, and failure rarely resulting in consequences for the supplier or the officials who approved it. See Marcus Baw's ["The NHS as an unassailable Public-Private Wealth Transfer Mechanism"](https://bawmedical.co.uk/t/the-nhs-as-an-unassailable-public-private-wealth-transfer-mechanism/1077) (8 July 2020) for the original framing; entries here supply the dated, sourced evidence for that argument rather than arguing it themselves.

## What this is not

Same discipline as `fdp-timeline.md`: not a campaign site, not an argument, not a news aggregator. An entry earns its place because it is a documented spending decision, cost disclosure, or outcome - not because someone has an opinion about NHS IT.

## Scope

Any NHS or DHSC technology programme, contract, or disclosed cost figure, UK-wide, where the primary emphasis is the money - amount committed, amount actually spent, and the gap between the two. This deliberately overlaps with other topics in this repo at the edges:

- FDP-specific spending entries (the £480m procurement estimate, the £330m award) stay in `fdp/entries/` - they are both an FDP event and a spending event, and FDP already has its own well-developed timeline. Don't duplicate them here; cross-reference by `related` id across topics if useful, or just cite both topics together in whatever is drawing on this data.
- Genuinely NHS-tech-spending entries that aren't primarily FDP stories - NPfIT/Lorenzo, the NHSX AI Lab, the abandoned Covid-19 app, the 2026 Healthcare AI Solutions framework - belong here.

## Entry schema

Identical to the FDP timeline's schema (`spec/fdp-timeline.md` "Entry schema") - same required fields, same `archive_url` non-negotiable rule, same `CONTRIBUTING.md` mechanics. Stored as YAML under `spending/entries/`.

### Tags

No fixed kind-tag taxonomy yet (unlike FDP's seven kind tags) - too few entries so far to know what the natural categories are. Reuse FDP's kind tags where they genuinely fit (`contract`, `official`, `media`, `legal`, `civil`) as the first tag, then free tags for the specific programme (`npfit`, `lorenzo`, `covid`, `nhsx`, `ai`, `nhs-sbs`...). Revisit once there are enough entries to see real clustering - don't invent a taxonomy ahead of the data, per the FDP timeline's own lesson.

## Status

Started 2026-10-17, seeded with 5 entries while researching an EDH episode on NHS technology spending (`episodes/in-planning/nhse-profligate-tech-spending/` in the parent EDH workspace). Spans 2011 (NAO's NPfIT care-records update) to 2026 (the Healthcare AI Solutions framework). Built the same way as `fdp/`: `s/build-index spending` regenerates `spending/index.json` from `spending/entries/*.yaml`.

The bulk spending-data work is specified separately in `spec/spending-data.md`. `spending/entries/` remains a selected editorial timeline; transaction rows, audited controls and derived analytical releases do not use the timeline-entry schema.

`spending/index.html` now provides a source-linked landing page for headline financial figures and the detailed-data pipeline. A filterable renderer for the five editorial timeline entries remains open work; the YAML entries and generated index are already useful as research material without one.

## Open questions

- Should NPfIT get its own sub-topic, the way FDP has, given how large and long-running it was (2002-2013+)? For now it's a few entries within `spending/`; revisit if it grows past a handful.
- Where does care.data belong? It's a spending-adjacent scandal (abandoned 2016) but the available reporting didn't surface a clean headline cost figure in initial research - worth a dedicated search pass rather than guessing a number.
- NHS Test and Trace is overwhelmingly not "tech" (testing kits, call centre staff, logistics), so it's deliberately excluded from this topic despite being a huge and well-documented overspend story (NAO: ~£29.3bn actual spend against a budget commonly cited as £37bn). The one genuinely tech-shaped fragment of that story - the abandoned contact-tracing app - is in scope and already has an entry.
