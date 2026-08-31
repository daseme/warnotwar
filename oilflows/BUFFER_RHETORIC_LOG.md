# Buffer rhetoric log (internal)

Official statements about the U.S. crude buffer — the SPR and commercial
stocks — logged here until the site has a clean surface for them. The
statements archive (`data/curated/us_oil_flow_claims.csv`) is deliberately
Hormuz-only; this log holds buffer-side statements in the same discipline
(dated, sourced, one neutral verb, no adjudication) so they can be promoted
into a schema later without rework.

Why this feed matters: buffer is one of the three feeds (flow, buffer,
rhetoric) behind the price we ultimately care about (BNO). Buffer
statements are unusually checkable — the referee is the EIA weekly series
we already ingest, published about five days after each week ends.

Entry format: date · speaker · channel · what was said · source · referee
and reading at time of entry · status (unverified / consistent_with_data /
not_yet_borne_out — lifecycle states, never verdicts).

---

## BUF-20260830-01

- **Date:** 2026-08-30
- **Speaker:** Donald Trump
- **Channel:** Truth Social post
- **Said:** Said Venezuelan oil would be used to "fill up the Strategic
  National Reserves," and that the "'topping out' process will begin very
  shortly."
- **Kind:** forward statement (PLANNED — not a completed action)
- **Source:** [UPI, Aug 30 2026](https://www.upi.com/Top_News/US/2026/08/30/Trumps-says-Venezuelan-oil-will-fill-up-US-petroleum-reserve/5321788131123/);
  also [World Oil](https://www.worldoil.com/news/2026/8/30/trump-says-venezuelan-oil-will-be-used-to-refill-u-s-strategic-petroleum-reserve/)
- **Referee:** EIA weekly SPR stocks (`spr_crude_mbbl` in
  `data/published/us_crude_buffer_weekly.json`), refreshed by the Thursday
  Action. A refill shows as the weekly change turning positive.
- **Instrument reading at entry:** SPR 289.7M bbl (week ending
  Aug 21 2026), weekly change averaging −4.5M bbl/week over the last 8
  weeks — the instrument currently reads *drawing*, not filling.
- **Caveats:** "very shortly" carries no date, so consistency has no
  deadline; much Venezuelan crude is extra-heavy and may not meet SPR
  specifications (raised in press coverage, e.g.
  [Yahoo Finance/24-7 Wall St.](https://finance.yahoo.com/energy/articles/trump-says-venezuelan-oil-refill-162145599.html)),
  which bears on how fast refill barrels could physically enter.
- **Status:** unverified (forward statement; awaiting weekly readings)
- **Related, not logged:** same-day claims about a joint venture over 65
  billion barrels of Venezuelan proven reserves (55% of output, at cost) —
  in-ground reserves are not flows and none of our instruments can check
  them.

---

Promotion path when a surface exists: either a `.live-record`-style dated
mark on the oilflows SPR block, or a buffer scope added to the statements
archive schema (deliberate enum extension, red-teamed first).
