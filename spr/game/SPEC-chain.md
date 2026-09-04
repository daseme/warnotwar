# SALT — the chain (spec, 2026-09-04). Status: phases A and B built; phase C open.

The drawdown path per dome becomes three links: **pumps → pipe → takeaway**. Flow is the smallest link. The scene shows barrels moving along the chain and the binding link glows red. Site cards let you build the next link. This is the Factorio loop on the real system: the wells were never the limit; the pipes and the docks were.

## The real system (sources)
- Three distribution systems: Seaway (Bryan Mound → Houston / Texas City), Texoma (Big Hill + West Hackberry → Beaumont, Port Arthur, Lake Charles), Capline (Bayou Choctaw → south-east Louisiana). DOE, Strategic Petroleum Reserve page.
- Marine terminals: Freeport 400 kb/d and Texas City 300 (Seaway); Nederland 1,190 and Beaumont 200 (Texoma); St. James 400, DOE-owned (Capline). Contracted commercial marine capacity 2.22 mb/d plus 0.4 DOE. DOE SPR page; LTSR 2016 gave 2.075.
- LTSR 2016: the reserve "can no longer bring oil to market without disturbing commercial oil flows"; dedicated marine terminals were recommended and never built. GAO Dec 2025: drawdown 2.7 of 4.415 mb/d; aggregate distribution 53 % of design.
- 2022: 1 mb/d for six months, a fifth of design, set by buyers and contracts. Harvey 2017 shut terminals.

## Model (world.js)
Per dome `d.chain = { pipe, dock, terminal }`:
- **pumps**: as now, `domeRate(w, d)`.
- **pipe**: capacity in mb/d. Starts at half the dome's design rate (the lines existed but were shared and small). Order "lay a bigger line": $150m, 2 years → full design rate.
- **takeaway** = refiners on the system + docks. Refiners on system (shared by domes on the same system, split by flow): Seaway 0.6, Texoma 1.0, Capline 0.35 mb/d, times sour acceptance (0.8 when refiners balk, as now). Docks: **contracted** (a standing yearly contract, $20m/yr per system: Seaway 0.7, Texoma 1.39, Capline 0 — St. James is DOE-owned, 0.4, ready 1981 at no cost) or **dedicated terminal** ($1.0bn, 3 years, per system, immune to congestion).
- Design check: 0.6+0.7 + 1.0+1.39 + 0.35+0.4 = 4.44 ≈ the 4.4 design rate when every link is built. The numbers per link are the model's split of DOE totals and are labelled as such.
- **Congestion** (the 2016 story): from 2012 a commercial-flow factor rises 0 → 0.5 by 2018 and stays. Pipe capacity and contracted docks are scaled by (1 − c). Dedicated terminals are not. Hurricanes close docks (takeaway × 0.5) as now.
- **Flow per dome** = min(pumps, pipe, share of takeaway). The system's takeaway is shared between Big Hill and West Hackberry in proportion to what each can push.
- Contracts lapse if the budget cannot pay them at year turn (a note in the receipt). In the nineties the grant cannot carry them: a full vault with no doors in 2005 unless you kept one.

## Crisis (main.js)
- Each dome in the crisis panel gets a three-segment bar: pumps | pipe | takeaway, in kb/d, the binding one red. One line under the knob: "wells could give 3.3, the pipes take 1.6, buyers and docks take 1.2".
- The release knob's ceiling is the delivered flow, not the well flow. The "wells mb/d" gauge gets a second needle "can deliver".
- Crisis log and summary record: delivered vs wanted, binding link and weeks bound.

## Year phase
- Site cards gain: "lay a bigger line" (once, per dome). System cards (three, below the sites, or folded into the first dome of each system) gain: "contract docks" (toggle, yearly cost shown), "build a terminal" (once).
- Impact lines follow the convention: cost, time, effect in mb/d delivered.
- Hold course: pipe and terminal are one-off orders; the dock contract is a standing setting and repeats.

## Scene (render.js)
- One line per dome from the dome top to the right edge (the refineries are already drawn there), with a dock glyph where docks exist. In a crisis, dots run along the line at a density set by flow; at the binding link the dots bunch up and the segment glows red. Outside a crisis the lines are faint.
- Preview convention holds: an ordered line or terminal draws dashed.

## Progressive unlock
- Pipe and dock controls stay hidden until the first crisis in which pipe or takeaway binds (1979 cannot bind: no pumps). At week 0 of that crisis a card "the bottleneck" explains the chain in three sentences, and the controls appear on the year panel afterwards. The intro card gains one line only.

## Blind window
- `seedWorld` sets the chain by era: pipes full from 1991; St. James ready; contracts held 1983–1994 and 2001–2011 (approximation of the record), lapsed otherwise; no dedicated terminals ever; congestion from 2012.

## Report and score
- End report gains "barrels that could not get out" and the year the chain first bound. Score term for delivered-over-wanted in crises (replaces nothing; sits beside painAvoided).

## Phasing
- A — DONE (commit 49942c9): model + crisis line + site orders + receipt rows.
- B — DONE: scene lines per dome, dots that pile up at the binding link, red choke glow, docks glyph, short red out-needle on the wells dial, the bottleneck card at week 0 of the first binding crisis, chain controls hidden until then (blind windows start with them shown).
- C — open: congestion era, dedicated terminal, blind seeding, bot orders, methodology note on the SPR page.
