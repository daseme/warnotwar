# Parked idea: the grade (sweet vs sour) — 2026-09-15, not building yet

Kurt: "persist the idea but we won't build rn".

## The lesson
The reserve's question is not how many barrels it holds but whether they are the barrels the missing ones were.
"Not about quality, about compatibility." Gulf Coast refining is ~70 % complex (cokers, built for Venezuelan
heavy). Since shale (~2012) the US makes surplus light sweet and exports it; it imports medium/heavy sour to feed
the cokers. So after 2012 sweet in the reserve does little as insurance; sour is the barrel that matters.

## Where the game stands
One undifferentiated stock at one price. Grade is flavour only: Libya text says light sweet, Caracas 2031 says
heavy, and a random 6 % event has refiners pass on sour (world.js crisisWeek, sourCut). Parked-list item
"sour-crude choice in crisis" is the seed of this.

## The proposal (recalibrated after the Hormuz 2026 spread flip)
- One number: the reserve's sour share. Starts near the real 1977 mix (verify; DOE Quick Facts gives sweet/sour by site).
- Buy throttle gains an ignorable sour/sweet selector, default "usual mix". Sour buys a few $ cheaper in normal
  years (verify discount by era), so the same budget stores more barrels.
- Spread as a SECOND NEEDLE on the existing crude dial (sour vs sweet), not a new dial. Normal years: small sour
  discount. In a sour shock it swings to a sour premium (March 2026: Mars went ~+$1.50 → +$11 over WTI in a week,
  HLS above LLS, Urals above Brent, WCS discount collapsed from $15–20 to <$9). In a sweet shock it swings the other way.
- Every crisis gets a grade tag. Hormuz 2026 = big sour (Arab Heavy/Medium, Basrah, Kuwaiti heavy offline, ~7 mb/d);
  Russia 2022 = medium sour; Libya 2011 = sweet; Caracas 2031 = heavy (your medium sour only partly substitutes,
  say so); hurricanes grade-neutral.
- Release value follows the spread: matching grade dents the spike fully and sells at the premium; wrong grade
  dents less and sells at a discount. The existing "buyers and docks take Z" line names the grade. This replaces
  the random sourCut event with something explained.
- After 2012 sweet barrels do less for the spike. Two scripted moments say so: a 2015 export-ban card ("the
  country now sells its own light oil abroad; keep holding sweet?") and the 2023 sour-only refill (verify).
- End report: your sour share vs the real reserve's.

## Not building
- China (~1.3 bn bbl, ~90 days) vs India (~37 mb, ~9.5 days) reserve comparison: good end-report or
  on-the-record fact, not a mechanic.
- Venezuela reopening Jan 2026: at most a line in the Hormuz text.
- A full two-grade reserve (two fills per dome, two knobs): too much state.

## Risks
- Fourth price-like instrument on a dense console → hence second needle, not a new dial.
- The "permanent premium" thesis is the author's (DD Geopolitics, pro-Moscow polemic; market numbers attributed
  to Reuters/Argus look right for March 2026). Model the flip as a crisis effect that settles, not a new normal.
- Every figure on screen needs a source: 1977 mix, sour discount by era, 2023 sour-only refill, spread peaks.

## Sources read
- https://ddgeopolitics.substack.com/p/the-new-oil-order (Mar 18 2026) — the spread flip, refinery basics, Gulf Coast 70 % complex.
- https://satiricalplanet.substack.com/p/the-century-of-oil-a-comprehensive — US–Venezuela political history 1914–2026;
  almost nothing on grades. Useful only for a possible 2019 sanctions card and Caracas 2031 colour.

Est. ~1 day + verification. If "go": write SPEC-grade.md the way SPEC-chain.md was done, red-team, then build.

## Absorbed 2026-09-15: Makai Research, "Dos Amigos" (Jeff McGee, Feb 9 2026)
https://makaimarine.substack.com/p/dos-amigos — a refining/tanker analyst, sober; the counterweight to DD's "permanent premium".

What it corrects:
- **Scale.** PADD3 crude intake is now 80 % domestic; light tight oil displaced ~4 mb/d of imports. What remains is
  ~1.5 mb/d of imports, almost all heavy/sour, and it exists for one reason: vacuum resid (VR) to feed the cokers.
  So "the Gulf Coast needs heavy" is true of a slice (coker feed), not the whole system. A heavy shock hurts the
  coker margin, not every refinery. Temper the spike effect accordingly.
- **The SPR's sour is the middle child.** SPR sour is medium (~30–33° API), not heavy. VR yields: LTO 5–7 %,
  domestic average ~10 %, Merey-16 40 %, import slate heading to 35 %. Even Arabian Gulf MEDIUM grades became
  unwanted in PADD3 after LTO arrived; light/sweet imports were "annihilated"; light/sour is down to a Saudi
  minimum for lube base stock. So the reserve's sour is: the right barrel in a Gulf (medium-sour) shock, a weak
  substitute in a heavy (Venezuela/Maya/WCS) shock, and superfluous to PADD3 in peacetime.
  → Three crisis tags, not two: SWEET (Libya), MEDIUM SOUR (Hormuz: Arab Medium, Basrah; Russia 2022 Urals),
    HEAVY (Caracas 2031: Merey, Boscan at 10–14° API). Match factors, roughly: sweet shock → sweet 1.0 / sour 0.5;
    medium-sour shock → sour 1.0 / sweet 0.4; heavy shock → sour 0.5 / sweet 0.2. Say it on screen in 2031:
    "your sour is medium; the cokers want heavy. It helps, it does not fill the hole."
- **Peacetime takers.** The reason the shale-era reserve leans on docks and exports (the chain) is that PADD3 does
  not want medium sour in normal years. This is why "refiners pass on sour" happens at all. The grade idea and the
  chain are the same story from two ends; the takers term should fall for sour after ~2012 outside a crisis.

New colour / numbers worth keeping:
- Venezuelan imports to PADD3 once approached 1.2 mb/d (matches the game's 2031 shortfall), avg 18° API; recent
  cargoes ~14°. Return under US marketing supports ~450 kb/d, capped by coker appetite.
- Mexico's crude output falling ~6 %/yr 2024–25; IEA has Mexico a net crude importer by ~2030. ~150 kb/d Maya
  and ~165 kb/d Isthmus leave the world slate through 2030. For the 2031 text: by then Maya is gone, so Venezuela
  and Canada are the only heavy feed → a Caracas collapse bites harder than 1.2 mb/d suggests.
- PADD3 coker utilisation averaged 78 % in 2025, below earlier levels, because the slate lightened (intake API
  30° → 34°). LyondellBasell Houston (263 kb/d, 106 kb/d coker) closed 1q25; ~450 kb/d of Louisiana CDU capacity
  lost 2021–22. → chain tweak, separate from grade: the refiner-appetite constants (Seaway 0.6, Texoma 1.0,
  Capline 0.35) should decay in the 2020s.
- Venezuela holds 30–50 mb of stored crude to be distributed in 2026.

## Absorbed 2026-09-15: The Blind Spot, Discord linkfest of Jan 4 2026 ("day of" view)
https://mindtheblindspot.substack.com/p/the-blind-spots-daily-discord-linkfest-40d — the community's link dump the day
after the US took Maduro (Jan 3 2026). Its own caveat: "loosely quality-controlled… not everything has been
rigorously fact-checked, and not all sources are necessarily credible." That caveat IS the lesson.

### What the day-of desk actually sees
A flood of contradictory takes, a handful right, most beside the point, and no number that agrees with another:
- "Gulf heavy refineries were built for Venezuelan crude; Keystone was designed to bring Canadian heavy once
  Venezuelan imports were blocked; now they can go back." (a Twitter account; broadly right, see Makai)
- "Canada just lost all leverage; the US doesn't need Canadian oil." (viral, 220K views; wrong)
- Rory Johnston's correction: Canada exports >4× Venezuela's shipments; most Canadian crude goes to the MIDWEST,
  not the Gulf, and is 100 % of Midwest/Mountain imports because no other pipeline comes in. (right)
- Heather Exner-Pirot: mildly bullish for Canada short-term because Venezuela SHUT IN heavy production amid the
  chaos. (right: the day-of effect of the "supply add" was a loss)
- Energy blogger: even 2.5 mb/d (2015 level) is a challenge in the short term. (right)
- Deripaska: US control of Venezuela + Guyana → over half of world reserves, could hold price near $50. (3.6M views; a take)
- A new Polymarket account bet $30k on Maduro's exit hours before; up $400k.
- Dallas Fed energy survey: "lingering pessimism and uncertainty."
- Everything else: bitcoin below $90k "on the airstrikes", LNG records, ballroom marble, Netflix After Dark.

### The two lessons for the game
1. **Day one is noise.** The shortfall is unknown; takes diverge by an order of magnitude; the loudest are wrong.
   The game already hides duration ("the shortfall lasts as long as it lasts; you will not be told"). It could
   also hide SIZE and GRADE on day one and let the player infer them from a wire of takes. This is the same
   mechanism as the blind window (names removed) applied within a crisis: a short scrolling "wire" on the crisis
   desk at week 0–2, five or six one-line takes of mixed quality, some sourced (Rory-style corrections), some
   viral nonsense. The pumps|line|docks bar then shows the truth as the weeks pass. Ties to parked idea #3 THE
   PHONE (calls from offices) — the wire is the cheaper, no-timer version of the same thing.
2. **The shock everyone watches is not the one that bites.** In Jan 2026 the whole feed was Venezuela, which
   turned out to be a supply ADD for the Gulf cokers; the sour shock that actually mattered (Hormuz) came eight
   weeks later. A day-one wire can carry red herrings: takes about a shock that is not the one on the desk.
   In the blind window this is doubly useful: the player cannot tell from the feed which year it is or which
   barrel just went missing.

### Concrete asset if built
`wire.js`: per crisis (and per blind text) 5–8 lines `{ text, kind: 'right'|'wrong'|'noise', src? }` shown
as a ticker on the crisis card and in weeks 0–2; the end-of-crisis summary reveals which were right. No new
model state; the wire is presentation over the crisis's existing shortfall/grade/weeks. Half a day plus writing.
Writing rule: takes are paraphrased and unattributed unless verbatim + sourced (statements.js standard).
