Oilflows → warnotwar-site: Integration and Editorial Brief

1. What this project is

oilflows/ is a reproducible data pipeline for measuring disruption to Persian Gulf oil shipping and comparing that physical disruption with oil-market prices. It is not a single-source “barrels through Hormuz” feed. The core idea is triangulation:

PortWatch gives fast daily physical-activity signals from AIS-derived port/chokepoint data.

SOMO and JODI give slower but official monthly export totals.

Saudi and UAE bypass-port proxies show rerouting away from the Gulf/Hormuz route.

Brent spot and BNO show the market response.

The pipeline is designed to keep those concepts separate rather than forcing them into a fake single precision number.

2. Current repo/site structure

The repo is a simple static site, not a framework app:

warnotwar-site/
├── .git/
├── .github/
├── history.json
├── index.html
├── info.html
├── scripts/
└── oilflows/

There is no top-level package.json, Vite, Next, Astro, etc. The local coder should integrate this using the site's existing HTML/JS conventions.

The oil-flow pipeline currently publishes:

oilflows/data/published/oilflows_daily.csv
oilflows/data/published/oilflows_daily.json
oilflows/data/published/oilflows_meta.json

Recommended production arrangement: do not make the web page depend directly on the internal pipeline directory. Copy the final site-facing JSON/meta files into a small public data directory such as:

warnotwar-site/data/oilflows_daily.json
warnotwar-site/data/oilflows_meta.json

The warnotwar-site/data/ directory does not exist yet; the publish/copy step in §3B should create it (mkdir -p data) on first run.

The CSV can remain an optional download/debug artifact.

3. What the local coder should do

A. Wire the published data into the static site

Use oilflows_daily.json as the primary page data source and oilflows_meta.json for definitions/freshness.

A typical static-page load can be as simple as:

const [daily, meta] = await Promise.all([
  fetch('./data/oilflows_daily.json').then(r => r.json()),
  fetch('./data/oilflows_meta.json').then(r => r.json()),
]);

Treat date as a date-only field. Avoid browser-local timezone conversion that can shift a YYYY-MM-DD value back one day. Prefer UTC/date-only handling in the chart layer.

B. Add a publish/copy step

Create one site-level script that copies the generated files from:

oilflows/data/published/

into whatever directory the static site actually deploys.

The final data build is:

cd ~/warnotwar-site/oilflows
python -m oilflows.build_master
python -m oilflows.build_shock_timeline
python -m oilflows.build_publish

Minimal copy step, run from the repo root after the build above:

mkdir -p data
cp oilflows/data/published/oilflows_daily.json data/
cp oilflows/data/published/oilflows_meta.json data/

A full refresh also needs the upstream PortWatch, JODI, SOMO and market refreshes discussed below.

C. Keep missing data missing

Do not connect chart lines across null values and do not forward-fill physical-flow series. The different sources have different latest dates by design.

Only the market last close fields are intentionally carried forward over non-trading days.

D. Add freshness to the UI

The page should visibly show that different series end on different dates. Read the source-of-truth values from oilflows_meta.json:latest_observation_dates rather than hard-coding them in the page. The available keys are hormuz, known_gulf_official, core_official_exports, saudi_gulf_proxy, saudi_bypass_proxy, uae_gulf_proxy, uae_bypass_proxy, brent, bno.

Snapshot as of 2026-08-26 (for orientation only; do not hard-code these into UI copy):

Hormuz activity: through 2026-08-23

Saudi route proxies: through 2026-08-21

UAE route proxies: through 2026-08-21

Iraq/Kuwait/Saudi official series: through 2026-06-30

BNO: observed through 2026-08-26

Brent spot: observed through 2026-08-25

Important: the current oilflows_meta.json says Brent latest = 2026-08-26 because it derives freshness from the forward-filled brent_spot_last_usd. Fix this before launch. Freshness must be based on an actual observation (brent_spot_usd / brent_observed), not the carried-forward last value.

For the same reason, consider publishing brent_observed and bno_observed flags so tooltips can distinguish a true market observation from a carried-forward weekend/holiday value.

4. Current site-facing schema

oilflows_daily.json currently contains these fields:

date
hormuz_tanker_count_7d
hormuz_tanker_count_index_7d
known_gulf_official_7d_mbd
known_gulf_official_index_7d
core_official_exports_7d_mbd
core_official_exports_index_7d
saudi_gulf_proxy_index_7d
saudi_bypass_proxy_index_7d
uae_gulf_proxy_index_7d
uae_bypass_proxy_index_7d
brent_spot_last_usd
bno_last_close_usd
shock_marker

Definitions

date
Calendar date as a YYYY-MM-DD string. Not a timestamp; do not feed it through timezone-aware date parsers, which can shift it back one day depending on locale.

hormuz_tanker_count_7d
Seven-day average of PortWatch tanker counts at the Strait of Hormuz chokepoint.

hormuz_tanker_count_index_7d
Same series normalized so 100 = average activity during 2025-07-01 through 2025-12-31.

known_gulf_official_7d_mbd
Official/calibrated Gulf crude exports from Iraq Basrah + Kuwait, seven-day average in million barrels/day.

known_gulf_official_index_7d
The same Iraq+Kuwait official Gulf series indexed to the Jul-Dec 2025 baseline = 100.

core_official_exports_7d_mbd
Iraq Basrah + Kuwait + Saudi national crude exports. This is useful as a core-producer export measure but must not be described as Hormuz flow, because Saudi national exports include the Red Sea/Yanbu bypass.

Saudi route indices

saudi_gulf_proxy_index_7d: Juaymah Gulf-side activity proxy.

saudi_bypass_proxy_index_7d: Yanbu Red Sea bypass activity proxy.

Both are PortWatch proxies indexed to Jul-Dec 2025 = 100. They are not national route shares.

UAE route indices

uae_gulf_proxy_index_7d: Ruways + Das Island Gulf activity proxy.

uae_bypass_proxy_index_7d: Fujairah bypass/mixed-port activity proxy.

Again: proxies, not official national export volumes or national route shares.

Market fields

brent_spot_last_usd: most recently observed Brent spot price on or before that calendar date.

bno_last_close_usd: most recently observed unadjusted BNO close on or before that calendar date.

shock_marker
Pipe-delimited generated event marker on days a threshold was crossed, e.g.:

hormuz_below_75pct
hormuz_below_10pct|hormuz_below_5pct
brent_peak
bno_peak

On all other days the field is JSON null (not an empty string). Verified against the current publish: 424 of 431 rows are null, 7 carry markers.

5. Data sources and exactly how they are used

IMF PortWatch / ArcGIS

PortWatch is the fast physical-activity layer.

For ports, export_tanker is an estimated metric-ton loading proxy derived from AIS/draft/capacity information. It is not a commodity-identified crude cargo database.

For Hormuz, we use tanker counts as the primary disruption signal. capacity_tanker is retained as a secondary size-weighted signal but is patchier.

Critical language rule: do not call PortWatch Hormuz tanker capacity “barrels through Hormuz.” It is a tanker-activity/capacity signal, not a direct crude-flow measurement.

SOMO — Iraq

SOMO is the official Iraq export anchor.

For Persian Gulf flow, we calibrate to Basrah crude barrels, not SOMO total exports. SOMO total includes non-Gulf routes such as Ceyhan/KRG and other northern exports.

The official 2025 monthly Basrah totals are available, plus 2026 Jan-Apr and a combined May-June release.

The May-June 2026 publication is deliberately retained as one 61-day official period. We do not invent separate May and June official Iraq totals.

Daily Iraq values are produced by allocating the official Basrah total according to the PortWatch Basrah loading shape. Therefore the raw daily series can be very lumpy; the 7-day average is the analytically preferred display.

June 2025 is deliberately not calibrated because the PortWatch history starts June 22; the pipeline refuses to stuff a full month's official total into nine days.

JODI — Kuwait and Saudi Arabia

JODI annual primary CSVs provide official monthly crude export rates.

A key discovery: JODI rows for UAE, Iraq, Iran and Qatar contain numeric CONVBBL conversion factors but the literal marker "-" for the actual export quantities in KBD/KBBL/KTONS/KL. A first-pass parser incorrectly treated "-" as nonblank. This was fixed conceptually: those countries simply do not provide usable export quantities in this JODI slice.

For Kuwait, JODI supplies the official monthly level and Mina Al Ahmadi PortWatch supplies the daily shape where present. When JODI has a valid monthly level but PortWatch has no usable loading signal, the pipeline uses a flat official monthly daily value, explicitly labeled as a monthly-flat fallback. This preserves known level without inventing within-month timing.

For Saudi Arabia, JODI gives the official national export level, but PortWatch does not return Ras Tanura. Therefore the pipeline does not allocate the national total between Gulf and bypass routes. Instead it keeps:

JODI = official national Saudi crude exports.

Juaymah = Gulf-route activity proxy.

Yanbu = Red Sea bypass-route activity proxy.

This separation is intentional and important.

UAE

JODI does not provide usable UAE crude export quantities for this period, so no fake official daily UAE barrels are created.

The UAE layer is proxy-only:

Gulf: Jabal Az Zannah-Ruways + Das Island.

Bypass/mixed: Fujairah.

Fujairah is a mixed tanker/product port, so this should be described as route/loading activity, not crude-only export volume.

Iran and Qatar

They are intentionally excluded from the public composite for now.

Iran PortWatch coverage is far too sparse to support an absolute daily export series.

Qatar's key Halul Island coverage is missing/incomplete; Doha-Umm Said becomes stale and Ras Laffan does not provide a usable series.

Their absence from the dataset does not mean zero exports. It means the public data are not strong enough for a defensible comparable estimate.

Brent

Brent is the EIA daily spot-price series delivered through FRED. It is the cleanest market measure of the underlying crude price in this project.

BNO

BNO is the United States Brent Oil Fund ETF. We use its unadjusted close as an investable market proxy, with adjusted close retained internally.

BNO is not spot Brent. It holds/rolls Brent futures, so it can diverge from spot because of futures-curve structure, roll effects and fund mechanics.

The current BNO pull uses Yahoo's public chart endpoint. That endpoint is unofficial/brittle and public-site use should be checked for terms/licensing. Since the static site consumes a generated local artifact rather than calling Yahoo client-side, there is no runtime dependency, but the coder should still review whether BNO should remain in a public production dataset or be sourced elsewhere.

6. The baseline and why it matters

All normalized activity indices use:

2025-07-01 through 2025-12-31 = 100

This period was chosen because:

the PortWatch dataset is complete after the June 22 start,

it gives a substantial pre-2026 reference window,

it precedes the major 2026 disruption.

An index of 25 therefore means 25% of the series' own Jul-Dec 2025 average, not 25% of all Gulf oil exports.

7. Current empirical story in the data

The physical break is extremely sharp.

Hormuz tanker-activity thresholds

Using the 7-day tanker-count index and starting the shock search on Feb. 23, 2026:

Mar 2   <= 75% of baseline   actual index 71.6
Mar 4   <= 50%               actual index 38.6
Mar 6   <= 25%               actual index 13.6
Mar 7   <= 10% and <= 5%     actual index 2.8
Mar 12  <= 1%                actual index 0.93

This is the canonical shock timeline.

Market at those physical thresholds

Date       Hormuz index    Brent    BNO
Mar 2          71.6        77.24    37.34
Mar 4          38.6        81.56    38.90
Mar 6          13.6        95.74    43.95
Mar 7           2.8        95.74    43.95
Mar 12          0.93      102.38    48.25

The repeated Mar. 7 market values are expected: physical data are calendar-daily, while financial markets do not trade every calendar day, so the site uses the last observed market close.

Market peaks after the physical collapse

From a pre-anchor of Mar. 5 to the deepest <=1% Hormuz threshold on Mar. 12:

Brent: $88.59 -> $102.38, +15.6%.

BNO: $40.24 -> $48.25, +19.9%.

Subsequent peaks in the current dataset:

Brent peak: $138.21 on Apr. 7, +56.0% versus Mar. 5 and +35.0% versus Mar. 12.

BNO peak: $60.13 on May 4, +49.4% versus Mar. 5 and +24.6% versus Mar. 12.

The important lesson is that the market did not merely move at the instant of the physical bottom. It repriced during the developing disruption and continued to carry a large risk premium afterward.

Official Gulf exports

The defensible official Gulf composite is Iraq Basrah + Kuwait.

Its 7-day index was approximately:

Feb 23  111.9
Mar 2    80.4
Mar 9    49.6
Mar 16   19.4
Mar 23    3.7
Mar 30    0.0

This falls more slowly than the Hormuz traffic index because official monthly totals necessarily smear activity over a month, while PortWatch can see the break day by day.

That is not a contradiction. It is exactly why both layers are valuable:

PortWatch tells us when the disruption happened.

SOMO/JODI tell us how much official monthly export volume ultimately occurred.

Iraq

SOMO official Basrah crude exports were roughly:

Jan 2026   3.263 mb/d
Feb 2026   3.334 mb/d
Mar 2026   0.470 mb/d
Apr 2026   0.153 mb/d
May-Jun    0.332 mb/d average across the combined 61-day period

The PortWatch-weighted daily series goes to zero after the early-March loading window and recovers only sporadically. Raw daily allocated values are lumpy; use the 7-day series for public charts.

Kuwait

JODI official crude exports:

Feb 2026   1.213 mb/d
Mar 2026   0.500 mb/d
Apr 2026   0.041 mb/d
May 2026   0.024 mb/d
Jun 2026   1.060 mb/d

May and June have no usable Mina Al Ahmadi PortWatch loading signal, so those months are shown as the flat official monthly level, not as observed daily timing.

Saudi Arabia: national exports vs route shift

Saudi official national crude exports fell from:

Feb 2026   7.276 mb/d
Mar 2026   4.974 mb/d
Apr 2026   3.986 mb/d
May 2026   3.434 mb/d
Jun 2026   3.993 mb/d

The route proxies simultaneously show a major redistribution:

Juaymah Gulf-side activity goes to zero for long stretches from late March.

Yanbu/Red Sea bypass activity remains active and often runs far above its Jul-Dec 2025 baseline.

Examples of the Yanbu proxy index:

Mar 23   241.8
Apr 6    309.2
May 4    371.7
Jun 1    537.7

Those numbers mean Yanbu activity was multiples of its own 2025 baseline. They do not mean Yanbu handled 537.7% of Saudi exports.

Likewise, a displayed “100% bypass share” in the internal proxy calculation means 100% of the two observed proxy signals was at Yanbu when Juaymah was zero. It is not a national export-route share because Ras Tanura is missing.

UAE: Gulf disappearance, partial Fujairah recovery

The UAE Gulf proxy fell from 121.9% of baseline on Feb. 23 to 35.1% on Mar. 9 and 0 by Mar. 16.

Fujairah also collapsed initially, then partially recovered while the Gulf-side proxy remained mostly absent. Examples of Fujairah's baseline index:

Mar 16    2.0
Apr 6    29.6
Apr 27   76.6
Jul 20   78.3
Aug 17   58.9

This is evidence of route activity/rerouting, not an official UAE crude-volume series.

8. The non-expert explanation

A good public explanation is to present this as four different measuring instruments rather than one magic dataset.

1. The traffic sensor

PortWatch is like a traffic counter at the Strait and at export terminals. It is fast and shows when tanker activity suddenly disappears, but it does not tell us exactly how many barrels of crude were on every ship.

2. The official monthly tally

SOMO and JODI are more like the official books. They tell us how much crude a country says it exported over a month, but they arrive later and cannot pinpoint the exact day the flow stopped.

3. The detour counters

Saudi Arabia can send oil west to Yanbu on the Red Sea, bypassing Hormuz. The UAE can move oil toward Fujairah outside the Strait. Watching Gulf terminals and bypass terminals separately shows whether activity is being rerouted rather than simply disappearing.

4. The market price

Brent and BNO tell us how traders priced the disruption. Prices began reacting while the physical shutdown was developing and peaked after tanker activity had already collapsed.

Suggested plain-English core story

Tanker activity through Hormuz did not drift lower; it broke. In less than a week in early March 2026, the PortWatch tanker-activity index fell from roughly three-quarters of its late-2025 norm to less than 3%, and by March 12 it was below 1%. Official Iraqi and Kuwaiti export data later confirmed a huge loss of Gulf crude exports, while Saudi and UAE terminal data showed that some activity was being pushed toward bypass routes. Oil prices rose rapidly during the shutdown and continued higher after the physical bottleneck had already reached its worst point.

Avoid saying “99% of Gulf oil stopped” or “99% of barrels through Hormuz stopped.” What fell by ~99% is the PortWatch Hormuz tanker-count activity index.

9. Recommended public presentation

For a non-expert, do not put every series on one chart.

Panel 1 — The physical break

Primary chart:

Hormuz tanker activity, 7-day average
Index: Jul-Dec 2025 = 100

Annotate the generated threshold dates:

Mar 2: below 75%

Mar 4: below 50%

Mar 6: below 25%

Mar 7: below 10%

Mar 12: below 1%

This should be the visual entry point.

Panel 2 — Official confirmation

Show Iraq Basrah + Kuwait official/calibrated exports in actual mb/d.

This is the strongest “real barrels” companion chart. Explain that monthly official totals are slower and therefore smoother than the traffic sensor.

If core_official_exports is shown, label it something like Core producer official crude exports and clearly note that Saudi is national and includes bypass exports. Do not label that series “Hormuz exports.”

Panel 3 — Rerouting

Use two small multiples:

Saudi: Juaymah Gulf proxy vs Yanbu bypass proxy, both indexed to 100.

UAE: Gulf proxy vs Fujairah bypass/mixed proxy, both indexed to 100.

This makes the detour story visually obvious without pretending we know national route shares.

Panel 4 — Market response

Brent should be the primary price chart. BNO can be secondary or optional.

Prefer separate aligned panels over a misleading dual-axis chart. If both are shown in one comparative chart, normalize both to an event-date index rather than plotting dollar values on unrelated scales.

Annotate:

<=1% Hormuz: Mar 12

Brent peak: Apr 7, $138.21

BNO peak: May 4, $60.13

Panel 5 — “How we know”

A short methodology/explainer section should explicitly distinguish:

daily proxy data,

official monthly totals,

bypass-route proxies,

market prices.

This is essential to make the project educational rather than merely dramatic.

10. Language guardrails for editors/UI copy

Safe language

“Hormuz tanker activity fell to less than 1% of its Jul-Dec 2025 baseline.”

“Official Iraq Basrah and Kuwait crude exports later fell close to zero.”

“Saudi PortWatch activity shifted sharply from the observed Gulf proxy toward Yanbu.”

“UAE Gulf-terminal activity disappeared while Fujairah later partially recovered.”

“Brent continued rising after the physical traffic collapse.”

Language to avoid

“99% of oil through Hormuz stopped.”

“PortWatch shows exact crude barrels.”

“100% of Saudi exports went through Yanbu.”

“Fujairah data are UAE crude exports.”

“Iran/Qatar had zero exports.”

“BNO is Brent spot.”

“A zero PortWatch port observation always proves zero physical exports.”

11. Known quirks and pitfalls

PortWatch is a proxy, not customs data

The port signal depends on AIS/draft/capacity estimates and terminal coverage. Some ports are absent or incomplete.

Ras Tanura is missing

This is the major Saudi limitation. Do not infer national Saudi Gulf/bypass shares from Juaymah vs Yanbu.

Qatar coverage is incomplete

Halul Island is missing; Doha-Umm Said becomes stale; Ras Laffan is unusable for this purpose.

Iran coverage is sparse

Kharg/Lavan activity exists but is far too sparse to use as an absolute national daily series.

Fujairah is mixed

It is useful for bypass activity but not a pure crude-only gauge.

Official monthly data lag

JODI/SOMO are not real-time. The public page must distinguish “latest physical proxy” from “latest official month.”

Official values can be monthly-flat

Kuwait May/June is the clearest example. A flat daily line means “official monthly average with no reliable within-month timing,” not smooth real-world exports.

Allocated daily Iraq/Kuwait values can be lumpy

Tanker loadings happen in chunks. Display 7-day averages to prevent users from interpreting a single loading day as a sustainable daily production/export rate.

Market weekends/holidays

*_last_* price fields are carried forward. A physical shock marker on Saturday can therefore show Friday's last price. Tooltips should say “last market close” or publish an observed flag.

BNO is a futures ETF

It can diverge materially from spot Brent because of futures-curve/roll mechanics.

Yahoo is brittle

The BNO source should not be treated as a guaranteed permanent API. No clean public alternative has been identified yet; the current recommendation is to cache the generated artifact and monitor for endpoint changes. A licensed data source is worth revisiting before any production public launch.

JODI uses the literal "-" character as a missing marker

Do not treat "-" as a numeric zero or a valid nonblank observation. CONVBBL alone is a conversion factor and does not mean a country reported export volume.

Do not connect nulls across source cutoffs

Physical series ending Aug. 21/23 must not be visually carried to Aug. 26 just because BNO continues.

12. Refresh/orchestration work still worth doing

The current pipeline pieces work, but a single fully automated refresh command should be added.

Note: the repo already has one GitHub Action, .github/workflows/update-price.yml, that runs scripts/update_price.py weekdays at 21:30 UTC to fetch a BNO close from Finnhub and commit it into history.json. That Action is independent of the oilflows publish pipeline. When adding oilflows automation, decide whether to leave it in place, subsume it into a broader Action, or retire it in favor of the oilflows market-data step.

Recommended dependency order:

1. Refresh PortWatch selected-port + Hormuz raw data
2. Build Hormuz processed series
3. Pull JODI
4. Refresh SOMO workbooks
5. Build SOMO official Iraq periods
6. Build Iraq daily calibration
7. Build Kuwait daily calibration
8. Build Saudi national + route proxy series
9. Build UAE route proxy series
10. Pull Brent/BNO market data
11. Build master
12. Build shock timeline
13. Build publish files
14. Copy site-facing JSON/meta into public data directory
15. Run tests

SOMO automation is the main remaining ingestion gap

The current SOMO workbooks were downloaded from SOMO's annual-summary page and parsed successfully, but the final codebase should get a pull_somo step that:

fetches the SOMO annual-summary page,

discovers current .xlsx links,

downloads them into data/raw/somo/,

preserves source filenames/vintage,

then runs the existing parser.

SOMO workbook layout can change; fail loudly if the expected English sheet/headers cannot be found.

Add a data-vintage timestamp

Add generated_at_utc (and ideally source-specific pull timestamps) to oilflows_meta.json. Official sources can revise history, so the site should know which data vintage generated a screenshot or story.

13. Testing and reproducibility

The pipeline has accumulated unit tests for:

Hormuz date continuity/duplicates/rolling measures,

JODI selection,

SOMO parsing,

Iraq allocation/reconciliation,

Kuwait allocation/fallback behavior,

Saudi route proxy separation,

UAE proxy construction,

master composites,

market parsing/calendar behavior,

shock thresholds/market peaks,

publish schema/markers/metadata.

Before integration/deployment, run:

cd ~/warnotwar-site/oilflows
python -m pytest

Then rebuild the published artifacts and confirm row/date/freshness output.

14. Suggested git/deployment policy

Prefer:

Commit code, tests, the terminal registry (oilflows/oilflows/terminal_registry.py — the curated PortWatch terminal → country/role/include-group mapping), methodology docs, and the small site-facing published JSON/meta.

Do not deploy or commit large reproducible raw/processed datasets unless there is a specific archival reason.

Keep oilflows/.venv, caches, raw downloads and processed intermediates ignored.

If the public site is deployed from repo root, copy only the final published files into the site public data directory.

15. Definition of done for the local coder

Integration is complete when:

The static page loads the compact JSON and metadata from a stable public path.

Charts do not connect across missing data or silently forward-fill physical series.

Market tooltips distinguish actual observations from carried-forward last closes.

Brent freshness metadata is corrected to use the actual observed date.

The primary public chart is the Hormuz 7-day tanker-activity index with the shock thresholds annotated.

The official Iraq+Kuwait Gulf series is shown separately from Saudi national exports.

Saudi/UAE bypass charts are labeled as proxies, not national route shares.

info.html (or equivalent) contains the plain-English “traffic sensor / official tally / detour counter / market price” methodology.

The current source freshness dates are visible.

A repeatable refresh/publish command or script exists.

SOMO refresh is either automated or clearly documented as the remaining manual step.

The page language obeys the guardrails above.

One-sentence summary of the result

The strongest defensible conclusion from this work is: PortWatch shows an extraordinarily rapid collapse in Hormuz tanker activity in early March 2026; official Iraqi and Kuwaiti export data confirm a major physical loss of Gulf crude exports; Saudi and UAE terminal signals show substantial bypass/rerouting behavior; and Brent/BNO repriced sharply during the shutdown and peaked only after the physical choke had already reached its worst point.
