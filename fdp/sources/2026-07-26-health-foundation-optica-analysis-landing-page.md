# Health Foundation: "Analysis of the relationship between adoption of OPTICA and delayed discharge from hospital"

Retained because archive.org's `/save/` endpoint returns HTTP 520 against
health.org.uk on every attempt (confirmed twice), while the domain is not
otherwise known to be unreachable - this looks like the same kind of
targeted block against archive.org's crawler already seen with
WhatDoTheyKnow (see
`fdp/sources/2026-foi-nhse-weekly-trust-users-by-product.md`). Direct
`curl` fetches of this page and of the underlying PDF both return an
Akamai "Access Denied" page (`errors.edgesuite.net`), consistent with a
bot-protection rule rather than a login/subscription paywall. The content
below was retrieved via the Kagi Extract API on 13 October 2026, which
evidently uses different fetch infrastructure.

Source: <https://www.health.org.uk/media-office/news-about-the-Health-Foundation/analysis-of-the-relationship-between-adoption-of-optica-and-delayed-discharge-from-hospital>

Cited by:
`fdp/entries/2026-07-26-health-foundation-optica-no-improvement-found.yaml`.

The landing page links two PDFs, neither independently retrievable by this
project for the same reason (both also return the Akamai block):

- "Relationship between adoption of OPTICA and delayed discharge from
  hospital" (481.25 KB) -
  <https://www.health.org.uk/sites/default/files/2026-07/Results%20from%20a%20descriptive%20analysis%20of%20the%20relationship%20between%20adoption%20of%20OPTICA%20and%20delayed%20discharge%20from%20hospital.pdf>
- "Letter to Ed Humpherson (Director General, Office for Statistics
  Regulation) - 22 July 2026" (80.1 KB) -
  <https://www.health.org.uk/sites/default/files/2026-07/Letter%20to%20Ed%20Humpherson%20%E2%80%93%2022%20July%202026.pdf>
  (dated the same day as the OSR casework findings already in this repo as
  `2026-07-22-osr-finds-nhse-fdp-causality-claims-needed-caveat` - not yet
  established whether this letter is what triggered that casework, is a
  submission to it, or is a response to its publication; flagged as a
  "Leads to follow up" item in `spec/fdp-timeline.md`, not yet chased
  down further here.)

## Retrieved content

Published 26 July 2026

Today, the Health Foundation has published a descriptive analysis of the
relationship between adoption of OPTICA and delayed discharge from
hospital, alongside a letter to the Office for Statistics Regulation in
response to the findings from its review of claims made about the
Federated Data Platform.

For further information about the analysis, or for any media enquiries
relating to the analysis or accompanying letter, please contact the
Health Foundation media team.

### Downloads

- Relationship between adoption of OPTICA and delayed discharge from
  hospital (481.25 KB)
- Letter to Ed Humpherson (Director General, Office for Statistics
  Regulation) - 22 July 2026 (80.1 KB)

### Media contact

Billie Morgan, Billie.Morgan@health.org.uk, 020 7257 8001
