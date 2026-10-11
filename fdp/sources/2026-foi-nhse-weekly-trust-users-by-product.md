# FOI correspondence: National usage statistics for Federated Data Platform

Retained because archive.org's capture (`web.archive.org/save/...`) has
repeatedly returned HTTP 520 against this specific WhatDoTheyKnow request
page, despite the domain generally being crawled and archived fine (other
whatdotheyknow.com pages, including the near-identical request to DHSC,
have recent Wayback captures) and despite `robots.txt` not disallowing
`/request/<slug>` itself. This looks like a targeted block against
archive.org's crawler rather than a transient failure - confirmed by a
manual attempt from a different IP, which hit the same wall. See
`fdp/entries/2026-07-15-bmj-third-trusts-not-using-fdp-apps.yaml` and the
pending usage-data/cost entry for where this is cited. The source document
(`NHS FDP Weekly Trust Users by Product.pdf`) is retained alongside this
file as `2026-foi-nhse-weekly-trust-users-by-product.pdf`.

Source: <https://www.whatdotheyknow.com/request/national_usage_statistics_for_fe_2>
Request by Nye Hudson to NHS England, part of a batch of 2 (the parallel
request to DHSC drew a response that DHSC does not hold this information).
Retrieved via direct fetch on 2026-10-11.

## Request (17 May 2026)

> Please can you supply me with the following information regarding the
> usage of the Federated Data Platform (FDP) across the UK in the last 12
> months. I have been informed by several different NHS analysts that this
> information should be accessible to local FDP administrators:
>
> 1. How many unique users have logged into/accessed each FDP product
>    deployed in each local instance per week for the last 12 months.
> 2. Please could you supply the above information in a way which
>    separates out log ins by NHS staff and people employed by Palantir or
>    any other company technical support for the FDP has been outsourced
>    to.
> 3. Please could you also supply me with any documents/assessments/
>    summaries held which have been generated in order to monitor and or
>    analyse the level of engagement with the FDP products in each local
>    instances across the UK.
> 4. Please could you share any data which would identify the number of
>    weekly logins to each FDP product in each local instance for the
>    purpose of analytics and dataset building, as opposed to the direct
>    provision of health care.
>
> If this is not possible, please could you supply monthly totals of
> logins or any other metric which is used to monitor engagement.

## Response (11 June 2026, ref FOI-2605-2328520)

> Decision
>
> NHS England holds some of this information. We will release the
> information we do hold in full.
>
> 1. NHS England holds this information. Please see the attached a
>    document that contains unique user log ins by NHS FDP product broken
>    down by local instance for the last 12 months. It should be noted
>    that NHS FDP products and Trusts are at different stages of roll
>    out, with many Trusts adopting products part way through the year.
>    The weekly log in total shows an average across actual weeks of use
>    to provide comparable figures.
> 2. NHS England does not hold this information. The dataset we have
>    available does not include user-level identifiers or employment
>    classification.
> 3. NHS England holds raw usage data used for monitoring NHS FDP
>    engagement. However, no separate formal documents, assessments, or
>    summary reports have been identified within the scope of this
>    request.
> 4. NHS England does not hold this information in the format requested.
>    The available datasets do not include a breakdown of login activity
>    by purpose (for example, distinguishing between direct patient care
>    and analytics or dataset development), either on a weekly or monthly
>    basis.

The attached document covered 85 NHS trusts and one Integrated Care
Board. A follow-up (14 July 2026) asking for the same breakdown for all
ICBs was declined (6 August 2026, ref FOI-2607-2347534): NHS England said
product-level data is not currently collected on an ICB basis, but that
organisational-level ICB usage data is expected to be published in
future.
