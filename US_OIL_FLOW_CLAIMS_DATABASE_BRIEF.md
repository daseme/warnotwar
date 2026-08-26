# U.S. Oil-Flow Claims Ledger

## Purpose

A durable, auditable database of reported U.S. government statements about oil and vessel movement through the Strait of Hormuz and Gulf bypass routes.

This seed contains **31 normalized claim records** from March 10 through August 21, 2026.

The database does **not** decide which claims are correct. It records exactly what was claimed, normalizes what each number measures, and preserves corrections and revisions.

## Files

- `us_oil_flow_claims_seed.csv`
- `us_oil_flow_claims.sqlite`

## Core normalization

Every claim should answer:

1. **What?** oil, oil/products, tankers, all ships
2. **Where?** Hormuz, Persian Gulf, regional including bypass, bypass only
3. **Direction?** outbound, inbound+outbound, unspecified
4. **When?** one night, one day, 7-day average, cumulative, current
5. **Who?** named official, anonymous official, institutional statement
6. **Status?** active, corrected, retracted, denied
7. **Source?** exact provenance

One statement may create several database rows. Wright's Aug. 11 post, for example, contains distinct claims for Hormuz flow, bypass flow, regional total, and a single-day regional volume.

## Critical rule: never overwrite history

The March 10 deleted Wright tanker-escort claim remains in the database and is linked to the White House's same-day denial.

Likewise Wright's Aug. 11 almost-9 mb/d 7-day average and Aug. 21 about-8 mb/d update remain separate historical claims.

## SQLite views

### `comparable_hormuz_flow_claims`

Only directly comparable outbound Hormuz oil-flow-rate claims in million barrels/day.

```sql
SELECT *
FROM comparable_hormuz_flow_claims
ORDER BY statement_date;
```

### `quantitative_claims`

All claims with a numeric value.

## Collection protocol

Absolute completeness cannot be guaranteed because statements can occur in television interviews, press gaggles, deleted social posts, anonymous briefings, and unindexed remarks. The way to get close is to make coverage systematic and auditable.

### Tier 1: direct U.S. sources

Sweep:
- White House briefings and transcripts
- Department of Energy / Secretary Wright
- CENTCOM releases and transcripts
- Department of Defense
- President Trump Truth Social
- official X accounts

Keywords:
`Hormuz`, `Persian Gulf`, `oil`, `tanker`, `barrels`, `ships`, `Project Freedom`, `escort`, `flow`, `transit`.

### Tier 2: wire services

Reuters and AP catch:
- press gaggles
- TV remarks
- deleted posts
- anonymous officials
- corrections

### Tier 3: specialist/scoop reporting

Axios, WSJ, Bloomberg, S&P Global, USNI, E&E/Politico, Lloyd's List and similar sources catch operational claims and anonymous briefings.

## Recommended next tables

The production database should eventually use:

```text
claims
sources
claim_sources
collection_runs
verification_snapshots
```

`collection_runs` should record which source families were searched and through what date, so “complete through Aug. 26” has an auditable meaning.

`verification_snapshots` should keep independent estimates separate from the claim itself:

```text
as_of_date
claim_id
tracker
estimate_min_mbd
estimate_max_mbd
estimate_point_mbd
method
coverage_notes
source_url
```

Then calculate:

```text
verification_gap_mbd
verified_fraction
claim_to_observed_ratio
```

## Known remaining sweep work

Before calling the ledger comprehensive:
- exhaustive White House transcript search from Feb. 28 onward
- exhaustive Wright X/interview archive
- Pentagon/CENTCOM press-gaggle sweep
- Trump Truth Social keyword sweep
- anonymous-official reports not well indexed by search engines
- exact timestamps and reference-period dates where recoverable

This seed is a strong starting ledger, not a claim of mathematical completeness.
