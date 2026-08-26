Flow → Buffer → Price

Build Brief for warnotwar-site

Objective

Add a third analytical layer to the existing oil-flow project so a non-expert can understand not only whether Gulf oil is moving and how prices reacted, but also how much stored crude the United States has available as a shock absorber.

The site should tell one coherent story:

Flow → Buffer → Price

Flow: Is oil physically moving through and around the Persian Gulf?

Buffer: How much crude inventory does the United States have relative to current refinery use?

Price: How is the market pricing the physical disruption and the available cushion?

Do not combine these into a synthetic “crisis score.” They are separate measurements answering separate questions.

1. Existing oil-flow system

The current pipeline already produces:

Hormuz tanker activity, with a Jul–Dec 2025 baseline index of 100.

Official/calibrated Iraq Basrah + Kuwait Gulf crude exports.

Saudi national crude exports from JODI.

Saudi Gulf-route activity proxy at Juaymah.

Saudi bypass-route activity proxy at Yanbu.

UAE Gulf-route proxy from Ruways + Das Island.

UAE bypass/mixed proxy from Fujairah.

Brent spot.

BNO unadjusted daily close.

Shock markers for the March 2026 Hormuz collapse and subsequent Brent/BNO peaks.

Published artifacts currently live under:

oilflows/data/published/
    oilflows_daily.csv
    oilflows_daily.json
    oilflows_meta.json

The final site integration should continue to consume only published artifacts, not raw PortWatch/JODI/SOMO files.

2. New “Buffer” dataset

Add a new weekly U.S. inventory pipeline using public U.S. Energy Information Administration data.

The core metric should reproduce the idea behind the BofA chart the project is reacting to, but using first-party public data.

Required EIA series

A. U.S. crude oil stocks including SPR

EIA weekly series:

Crude Oil (Including SPR)
units: thousand barrels
history: 1982–present

Reference page:

https://www.eia.gov/dnav/pet/PET_STOC_WSTK_A_EPC0_SAE_MBBL_W.htm

B. U.S. commercial crude stocks excluding lease stock

EIA weekly series:

Commercial Crude Oil (Excl. Lease Stock)
units: thousand barrels
history: 1982–present

Reference page:

https://www.eia.gov/dnav/pet/pet_stoc_wstk_a_EPC0_SAX_mbbl_w.htm

C. Strategic Petroleum Reserve crude stocks

EIA weekly series:

SPR crude
units: thousand barrels
history: 1982–present

Reference page:

https://www.eia.gov/dnav/pet/pet_stoc_wstk_a_epc0_sas_mbbl_w.htm

This is useful both for validation and to explain how much of the total cushion is strategic rather than commercial.

D. U.S. refiner crude-oil inputs

EIA weekly series:

Refiner Crude Oil Inputs
units: thousand barrels per day
history: 1982–present

Reference page:

https://www.eia.gov/dnav/pet/pet_pnp_wiup_a_EPC0_YIY_mbblpd_w.htm

This is the denominator.

3. Calculations

Join all weekly inputs by EIA week-ending date.

Calculate:

days_supply_incl_spr
    = crude_stocks_incl_spr_mbbl
      / refinery_crude_inputs_mbd

Because both source units are “thousand barrels” and “thousand barrels/day,” the thousands cancel and the result is days.

Also calculate:

commercial_days_supply
    = commercial_crude_mbbl
      / refinery_crude_inputs_mbd

And:

spr_days_equivalent
    = spr_crude_mbbl
      / refinery_crude_inputs_mbd

The identity should approximately hold:

days_supply_incl_spr
≈ commercial_days_supply + spr_days_equivalent

Small differences are acceptable because EIA series can be independently rounded and historical definitions are not perfectly identical.

Do not call spr_days_equivalent “days until the SPR runs out.” It is only the SPR volume divided by that week's refinery input rate.

4. Historical-context calculations

Do not hardcode the BofA claim “40–50 year lows.”

Calculate our own historical context from the EIA series each time the pipeline runs.

For days_supply_incl_spr, publish:

historical_mean
historical_median
historical_min
historical_min_date
historical_percentile
52_week_min
52_week_max
prior_lower_date
years_since_prior_lower

Suggested percentile definition:

100 * count(history <= current) / count(history)

A low percentile means inventories are unusually thin relative to refinery use.

For editorial language, generate facts from these calculations, for example:

"At the Xth percentile of weekly observations since 1982."

or, if valid:

"Lowest reading since YYYY."

Do not write “lowest in 40 years” unless the data actually support it on that refresh.

5. New published artifact

Create:

oilflows/data/published/us_crude_buffer_weekly.csv
oilflows/data/published/us_crude_buffer_weekly.json
oilflows/data/published/us_crude_buffer_meta.json

Suggested weekly schema:

week_end
crude_stocks_incl_spr_mbbl
commercial_crude_mbbl
spr_crude_mbbl
refinery_crude_inputs_mbd
days_supply_incl_spr
commercial_days_supply
spr_days_equivalent
days_supply_incl_spr_percentile

Metadata should include:

{
  "schema_version": 1,
  "frequency": "weekly",
  "source": "U.S. Energy Information Administration",
  "first_week": "...",
  "last_week": "...",
  "latest_release_date": "...",
  "historical_mean_days_supply_incl_spr": null,
  "historical_median_days_supply_incl_spr": null,
  "historical_min_days_supply_incl_spr": null,
  "historical_min_date": null,
  "current_percentile": null,
  "prior_lower_date": null,
  "years_since_prior_lower": null
}

Use actual calculated values at build time.

6. Pipeline implementation

Add modules along the same pattern as the existing oil-flow package, for example:

oilflows/
    eia_inventory.py
    pull_eia_inventory.py
    build_buffer.py

Tests should cover:

Units and days-of-supply calculation.

Joining only matching week-ending dates.

Missing input behavior.

No division by zero.

Historical percentile calculation.

Prior-lower-date calculation.

Exact separation of observed weekly values from display interpolation.

Metadata latest-observation date.

Published JSON contains JSON null, not NaN.

Prefer an official EIA downloadable/API endpoint if practical. Preserve the raw EIA responses under data/raw/.

The pipeline must be reproducible without Bloomberg or BofA data.

7. Site architecture: Flow → Buffer → Price

The three concepts should be visually and editorially linked but not mathematically blended.

FLOW

Existing primary chart:

Hormuz tanker activity
100 = Jul–Dec 2025 baseline

Supporting views:

Iraq + Kuwait official Gulf crude exports
Saudi Gulf proxy vs Yanbu bypass proxy
UAE Gulf proxy vs Fujairah bypass proxy

Core explanatory question:

Is the oil physically moving?

The canonical March 2026 Hormuz sequence currently is:

Mar 2   71.6% of baseline
Mar 4   38.6%
Mar 6   13.6%
Mar 7    2.8%
Mar 12   0.93%

Keep the existing shock markers.

BUFFER

New primary chart:

U.S. crude oil days of supply including SPR
1982–present
weekly

Recommended design:

Main line: days_supply_incl_spr.

Secondary line: commercial_days_supply.

Long historical time span, ideally 1982–present.

Clearly mark the current reading.

Optional horizontal line for historical average.

Label the March 2026 Hormuz shock on the historical chart.

Do not mechanically reproduce BofA styling or labels.

A second compact display can show:

TOTAL CRUDE CUSHION      XX.X days
COMMERCIAL ONLY          XX.X days
SPR EQUIVALENT           XX.X days
HISTORICAL PERCENTILE    Xth percentile

Core explanatory question:

How much stored crude is available to cushion a prolonged disruption?

PRICE

Existing market view:

Brent spot
BNO

Core explanatory question:

What price is the market putting on the disruption?

Useful existing chronology:

Feb 23   Brent $71.90
Mar 02   Brent $77.24
Mar 09   Brent $94.35
Mar 12   Brent $102.38
Apr 07   Brent peak $138.21

BNO remains useful as an investable-market companion but Brent should be the primary oil-price series.

8. Recommended combined presentation

The strongest page structure is three vertically aligned panels sharing the same recent-event timeline:

             FLOW
 Hormuz / Gulf physical activity
             ↓
            BUFFER
 U.S. crude days of supply
             ↓
             PRICE
 Brent market response

Do not imply strict causality merely from visual alignment.

The intended teaching sequence is:

A disruption matters first because physical supply is impaired.
The economic danger depends partly on the inventories available to bridge that impairment.
Markets then price both the lost flow and expectations about how long the system can absorb it.

For the recent 2026 view, inventory data are weekly while flow and market data are daily.

Do not fabricate daily inventory observations.

Options:

Show weekly dots/steps on the same date axis.

Or keep Buffer as a separate weekly chart immediately between Flow and Price.

The second option is cleaner.

9. Plain-English explanation for the site

Suggested editorial foundation:

Oil shocks have three parts: flow, buffer and price.

First we measure whether crude is actually moving through the Persian Gulf. Tanker activity gives us a fast daily signal; official export data arrive later and tell us how much crude ultimately moved.

Next comes the buffer. The United States holds crude in commercial inventories and in the Strategic Petroleum Reserve. Dividing those stocks by the amount U.S. refineries are currently processing gives a useful measure of the size of that cushion in “days of refinery use.”

Finally comes price. Brent shows how the market values the disruption, the available detours, the inventory cushion and expectations about what happens next.

Keep this factual. Avoid claims that inventories alone “explain” the Brent move.

10. The most important wording guardrail

Never say:

"The U.S. has only 42 days of oil left."

Instead say:

"Stored U.S. crude, including the Strategic Petroleum Reserve,
is equivalent to about 42 days of current refinery crude inputs."

Or shorter:

"Current stored crude equals about 42 days of refinery use."

Why:

U.S. domestic production continues.

Imports from Canada and elsewhere continue.

Refinery runs can change.

Demand can change.

SPR withdrawals are policy decisions.

Physical drawdown rates and logistics matter.

“Days of supply” is a ratio, not a countdown clock.

11. Other methodological pitfalls

Refinery inputs are seasonal

The denominator moves.

If refineries increase throughput, days of supply can fall even with little change in crude stocks. During refinery maintenance, days of supply can rise.

Show or disclose the denominator in the methodology.

SPR is not the same as commercial inventory

The SPR is a government-controlled emergency reserve.

Including it is reasonable for measuring total national stored crude, but users should be able to see the commercial-only number as well.

Long historical series have definition changes

EIA's historical petroleum-stock methodology has changed over time. In particular, treatment of lease stocks changes in the historical documentation.

That does not make the long-run series unusable, but it means:

describe the historical ranking as approximate context;

preserve EIA source notes;

avoid fake precision when claiming multi-decade records.

Weekly release lag

Inventory figures represent a week ending on a specific date and are released later.

Keep:

week_end

and, if available:

release_date

separate.

Do not present the release date as the inventory observation date.

No forward-fill in underlying data

For analytical/public data:

Friday observation = Friday observation
Saturday–Thursday = no new inventory observation

The UI may visually carry the latest value as a step chart, but the data should retain the actual observation date.

12. Suggested tooltip language

For days_supply_incl_spr:

Total U.S. crude stocks, including the Strategic Petroleum Reserve, divided by that week's U.S. refinery crude inputs. This is a measure of the inventory cushion, not a countdown until the country runs out of oil.

For commercial_days_supply:

Commercial U.S. crude stocks divided by refinery crude inputs. This excludes the Strategic Petroleum Reserve.

For the SPR:

Government-controlled emergency crude inventory. It can supplement commercial stocks, but releases depend on policy decisions and physical distribution capacity.

13. Optional second-stage work — not required for v1

Do not put these into the first release unless the first chart creates a clear need.

Gulf Coast / PADD 3 buffer

EIA publishes PADD 3 commercial crude stocks and refinery inputs.

This could answer a more specific question:

How exposed is the U.S. Gulf Coast refining system?

It may be more economically relevant to a Persian Gulf disruption than a national inventory figure, but is less intuitive for a general reader.

Imports

U.S. crude import data could help show why “42 days” is not a depletion countdown.

Domestic production

Likewise, U.S. crude production can contextualize the size of ongoing domestic supply.

Gasoline/distillate inventories

Do not add these simply because they exist. They answer downstream product questions rather than the crude-supply question.

14. Refresh orchestration

The local pipeline should eventually expose one top-level refresh command.

Conceptually:

refresh PortWatch
refresh Hormuz
refresh JODI
refresh SOMO
refresh market
refresh EIA inventories
rebuild country layers
rebuild master
rebuild shock timeline
build published oilflow artifacts
build published buffer artifacts
copy/update static-site data

A failure in a slower official source should not silently erase the last valid published observation.

Prefer:

preserve last successful public artifact;

surface source freshness in metadata;

fail loudly on malformed source schemas;

do not manufacture current values.

15. Acceptance criteria

The Buffer feature is ready when all of the following are true:

The complete EIA history can be fetched reproducibly without Bloomberg/BofA.

days_supply_incl_spr reproduces the contemporary low-40-day magnitude seen in outside research when using matching EIA weeks.

Commercial-only and SPR components are visible separately.

Historical percentile/ranking is calculated from our own data.

No “X days until America runs out” language appears.

Weekly observation date and data freshness are explicit.

The page presents Flow, Buffer and Price as three different concepts.

Inventory data are never treated as daily observations.

Existing March 2026 flow shock markers remain intact.

All published data files are small enough to load directly in the static site.

Tests cover calculations, missing data, schema drift and metadata.

info.html explains the metric in plain English.

16. Editorial north star

The feature should enable a reader with no oil-market background to leave understanding this:

A shipping disruption is not the whole oil story.

We need to know how much oil is still moving, how much stored crude exists to absorb the loss, and what price the market is assigning to the resulting scarcity and uncertainty.

Flow tells us what is happening physically.
Buffer tells us how much breathing room exists.
Price tells us how the market is reacting.

That is the product.