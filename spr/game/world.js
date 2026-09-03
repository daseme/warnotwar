/* SALT — the simulation. Pure model, no DOM. Years 1977–2036.
   Units: mb = million barrels, mb/d = million barrels a day, $bn = billions of dollars. */
'use strict';
(function (root) {
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const rnd = (() => { let seed = 1234567; const f = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }; f.reseed = s => { seed = s >>> 0; }; return f; })();
  const HEEL = 0.02;

  /* ---- the four domes. capacity is what each can hold when fully built out ---- */
  const DOMES = [
    { key: 'bm', name: 'Bryan Mound',    where: 'Freeport, Texas',   rate: 1.500, fill: 0.225, maxCav: 19, startCav: 4, startLeft: 2, opYear: 1986, x: 0.12 },
    { key: 'bh', name: 'Big Hill',       where: 'Winnie, Texas',     rate: 1.100, fill: 0.225, maxCav: 14, startCav: 0, startLeft: 5, opYear: 1991, x: 0.36 },
    { key: 'wh', name: 'West Hackberry', where: 'Lake Charles, La.', rate: 1.300, fill: 0.225, maxCav: 21, startCav: 5, startLeft: 2, opYear: 1988, x: 0.60 },
    { key: 'bc', name: 'Bayou Choctaw',  where: 'Baton Rouge, La.',  rate: 0.515, fill: 0.110, maxCav: 6,  startCav: 4, startLeft: 1, opYear: 1987, x: 0.82 },
  ];
  const CAV_MB = 10.5;                 // a new cavern
  const BUILD_YEARS = 3, BUILD_COST = 0.04;   // $bn per cavern (leaching, wells, brine line)
  const WORKOVER = 0.002;              // $bn per well workover
  const US_DEMAND = 19;                // mb/d, used to price pain
  const IEA_SHARE = 0.44;              // the U.S. share of an allied release

  /* ---- baseline price path, $ per barrel ---- */
  const PRICE = { 1977: 14, 1978: 14, 1979: 22, 1980: 37, 1981: 36, 1982: 33, 1983: 30, 1984: 29, 1985: 28, 1986: 14, 1987: 18, 1988: 15, 1989: 18, 1990: 20, 1991: 20, 1992: 19, 1993: 17, 1994: 16, 1995: 17, 1996: 21, 1997: 19, 1998: 13, 1999: 18, 2000: 28, 2001: 24, 2002: 25, 2003: 29, 2004: 38, 2005: 54, 2006: 65, 2007: 72, 2008: 97, 2009: 62, 2010: 80, 2011: 105, 2012: 112, 2013: 109, 2014: 99, 2015: 52, 2016: 44, 2017: 54, 2018: 71, 2019: 64, 2020: 42, 2021: 71, 2022: 96, 2023: 82, 2024: 80, 2025: 68, 2026: 76 };
  const basePrice = y => PRICE[y] ?? (PRICE[2026] + (y - 2026) * 1.5);

  /* ---- yearly appropriations, $bn, roughly the real pattern ---- */
  const budgetFor = y => y <= 1985 ? 2.2 : y <= 1991 ? 1.2 : y <= 1999 ? 0.05 : y <= 2008 ? 0.9 : y <= 2014 ? 0.25 : y <= 2022 ? 0.15 : y <= 2025 ? 1.2 : 0.5;

  /* ---- scripted history: crises and cards ---- */
  const SCRIPT = [
    { year: 1979, kind: 'crisis', name: 'The Iranian revolution', text: 'Iran’s output collapses. World supply is short about 2 million barrels a day and queues return to American filling stations. Your caverns hold what you have bought. Your pumps do not exist yet.', shortfall: 2.0, weeks: [30, 45], spikeK: 9 },
    { year: 1986, kind: 'card', name: 'The price collapse', text: 'Saudi Arabia opens the taps. Crude falls from $28 to $14. Oil has never been cheaper to buy for the reserve, and Congress has never been less interested in paying for it.', choices: [{ label: 'Ask Congress for an extra $2bn to buy at $14', mood: -8, grant: 2.0, odds: 0.6 }, { label: 'Buy what the budget allows', mood: 0 }] },
    { year: 1990, kind: 'crisis', name: 'Iraq invades Kuwait', text: 'Iraqi and Kuwaiti exports stop. The world loses 4.3 million barrels a day. The allies agree a collective release; your share is about 44 percent of whatever the group offers.', shortfall: 4.3, weeks: [24, 32], spikeK: 9, iea: true },
    { year: 1993, kind: 'card', name: 'Weeks Island', text: 'A sinkhole opens above the old salt mine at Weeks Island. Fresh water is seeping toward 72 million barrels of oil. Engineers say the mine must be emptied within five years.', choices: [{ label: 'Move the oil to new caverns ($0.1bn, lose 1.5 mb)', cost: 0.1, lose: 1.5, mood: 2 }, { label: 'Monitor and hope', risk: { p: 0.5, lose: 20, text: 'The mine floods. Twenty million barrels are lost to the water.' } }] },
    { year: 1996, kind: 'card', name: 'Deficit reduction', text: 'Congress wants 28 million barrels sold, not for an emergency but to close a budget gap. The money goes to the Treasury, not to you.', choices: [{ label: 'Comply: sell 28 mb', sell: 28, mood: 3 }, { label: 'Lobby against it (60 % odds)', odds: 0.6, mood: -6, fail: { sell: 28 } }] },
    { year: 2000, kind: 'card', name: 'Heating oil', text: 'Northeast distillate stocks are thin before winter and it is an election year. The White House wants a 30 million barrel loan: refiners take crude now and return more barrels later.', choices: [{ label: 'Lend 30 mb, get 31.5 back in two years', lend: 30, back: 31.5, mood: 4 }, { label: 'Refuse: this is not an emergency', mood: -5 }] },
    { year: 2005, kind: 'crisis', name: 'Katrina and Rita', text: 'Two hurricanes shut a quarter of Gulf production and a fifth of refining. Refiners that can still run are asking to borrow crude at once.', shortfall: 1.5, weeks: [6, 10], spikeK: 12, hurricane: true },
    { year: 2008, kind: 'card', name: 'Oil at $140', text: 'No barrel has been lost anywhere. Demand from China has pushed crude to $140 and gasoline over $4. Congress demands a release to bring the price down.', choices: [{ label: 'Release 30 mb to calm the market', sell: 30, mood: 6, priceNote: -4 }, { label: 'Refuse: the reserve is for supply shocks, not prices', mood: -8 }] },
    { year: 2011, kind: 'crisis', name: 'Libya', text: 'Civil war stops Libya’s 1.5 million barrels a day of light sweet crude. The allies propose a 60 million barrel collective release.', shortfall: 1.5, weeks: [28, 36], spikeK: 9, iea: true },
    { year: 2015, kind: 'card', name: 'The piggy bank', text: 'Congress has found the reserve. Eight laws over three years will order more than 350 million barrels sold to pay for highways, medical research and tax cuts.', choices: [{ label: 'Comply as ordered: sell 25 mb a year for six years', mandate: { mb: 25, years: 6 }, mood: 2 }, { label: 'Fight it in hearings (40 % odds)', odds: 0.4, mood: -8, fail: { mandate: { mb: 25, years: 6 } } }] },
    { year: 2017, kind: 'crisis', name: 'Harvey', text: 'Harvey drops fifty inches of rain on Houston. Refineries flood and pipelines stop. The shortfall is short and local, and your own staff are evacuated.', shortfall: 0.8, weeks: [3, 5], spikeK: 10, hurricane: true },
    { year: 2020, kind: 'card', name: 'Oil at $20', text: 'A pandemic empties the roads. Crude drops below $20 and producers are paying people to take it. You could fill every empty cavern for almost nothing. Congress declines the $3bn.', choices: [{ label: 'Lease empty caverns to companies for a fee in barrels (+20 mb)', gain: 20, mood: 3 }, { label: 'Ask Congress again for $3bn (25 % odds)', odds: 0.25, grant: 3.0, mood: -4 }] },
    { year: 2022, kind: 'crisis', name: 'Russia invades Ukraine', text: 'Sanctions and self-sanctioning take up to 2 million barrels a day of Russian crude off the western market. Brent passes $120. The White House wants a million barrels a day for six months.', shortfall: 2.0, weeks: [40, 52], spikeK: 9, iea: true },
    { year: 2026, kind: 'crisis', name: 'Hormuz', text: 'Strikes on Iran close the Strait of Hormuz. Twenty million barrels a day, a fifth of the world’s oil, stop moving. The allies agree the largest release in history. Nobody knows how long the strait stays shut.', shortfall: 8.0, weeks: [26, 60], spikeK: 9, iea: true, ongoing: true },
    { year: 2031, kind: 'crisis', name: 'The Caracas collapse', text: 'Venezuela’s government falls and its 1.2 million barrels a day of heavy crude stop. Gulf Coast refineries built for heavy oil are the ones hurt.', shortfall: 1.2, weeks: [20, 30], spikeK: 9 },
    { year: 2034, kind: 'crisis', name: 'The long season', text: 'Three hurricanes in five weeks track across the western Gulf. Production, refining and your own raw-water intakes are hit in turn.', shortfall: 1.8, weeks: [8, 12], spikeK: 11, hurricane: true },
  ];

  /* ---- world state ---- */
  function newWorld() {
    rnd.reseed(Date.now() & 0xffffffff);
    const w = {
      year: 1977, week: 0, phase: 'year',      // year | crisis | end
      budget: 1.0, spent: 0, treasury: 0, mood: 60,
      price: basePrice(1977), spike: 0,
      domes: DOMES.map(d => ({ ...d, cav: [], building: [] })),
      log: [], history: [], pain: 0, painAvoided: 0, releasedTotal: 0, boughtTotal: 0, spentTotal: 0,
      loans: [], mandates: [], crisis: null, done: {}, hurricane: null, flash: null,
      seen1979: false,
    };
    // the acquired brine caverns, bought in 1977, irregular and single-cycle
    w.domes.forEach(d => { for (let i = 0; i < d.startCav; i++) d.cav.push(newCavern(d, true, d.startLeft)); });
    w.domes[0].cav[0].oil = 7.5;  // the first oil: a trickle in 1977
    pushHistory(w);
    return w;
  }
  function newCavern(d, acquired, left) {
    return { cap: acquired ? 9 + rnd() * 6 : CAV_MB, oil: 0, left: left ?? 5, used: 0, health: acquired ? 0.7 : 1, age: acquired ? 30 : 0, offline: 0, retired: false, acquired, usedAt: 0 };
  }
  const domeOil = d => d.cav.reduce((a, c) => a + c.oil, 0);
  const domeCap = d => d.cav.reduce((a, c) => a + (c.retired ? 0 : c.cap), 0);
  const inv = w => w.domes.reduce((a, d) => a + domeOil(d), 0);
  const capacity = w => w.domes.reduce((a, d) => a + domeCap(d), 0);
  const cavCount = w => w.domes.reduce((a, d) => a + d.cav.filter(c => !c.retired).length, 0);
  const usable = c => !c.retired && c.offline <= 0 && c.oil > c.cap * HEEL + 1e-9;
  function domeRate(w, d) { if (w.year < d.opYear) return 0; const n = d.cav.filter(c => !c.retired).length; if (!n) return 0; return d.rate * (d.cav.filter(usable).length / Math.max(n, d.maxCav * 0.6)); }
  const drawCap = w => w.domes.reduce((a, d) => a + domeRate(w, d), 0) * (w.hurricane ? 0.5 : 1);
  const fillCap = w => w.domes.reduce((a, d) => a + (w.year >= d.opYear - 5 ? d.fill : 0.05), 0);  // mb/d
  const roomFor = w => w.domes.reduce((a, d) => a + d.cav.filter(c => !c.retired && c.offline <= 0).reduce((x, c) => x + Math.max(0, c.cap - c.oil), 0), 0);
  function pushHistory(w) { w.history.push({ year: w.year + (w.week / 52), inv: inv(w), cap: capacity(w), price: w.price }); }
  function log(w, text, cls) { w.log.unshift({ year: w.year, week: w.week, text, cls: cls || '' }); if (w.log.length > 400) w.log.pop(); }

  /* ---- moving oil ---- */
  function putOil(w, mb) {
    // fill the healthiest caverns with the most drawdowns left first, one at a time
    let left = mb;
    const cavs = w.domes.flatMap(d => d.cav).filter(c => !c.retired && c.offline <= 0).sort((a, b) => (b.left - a.left) || (b.health - a.health));
    for (const c of cavs) { if (left <= 1e-9) break; const room = Math.max(0, c.cap - c.oil); const t = Math.min(room, left); c.oil += t; left -= t; }
    return mb - left;
  }
  function takeOil(w, mb) {
    // drain the emptiest usable cavern first so wells drop out as caverns empty; leaching is booked per cavern
    let left = mb, got = 0; const retired = [];
    for (const d of w.domes) {
      if (left <= 1e-9) break;
      const share = domeRate(w, d) / Math.max(1e-9, w.domes.reduce((a, x) => a + domeRate(w, x), 0));
      let take = Math.min(left, mb * share * 1.0001);
      const cavs = d.cav.filter(usable).sort((a, b) => a.oil - b.oil);
      for (const c of cavs) {
        if (take <= 1e-9) break;
        const avail = Math.max(0, c.oil - c.cap * HEEL), t = Math.min(avail, take);
        c.oil -= t; take -= t; got += t; left -= t;
        c.used += t / (c.cap * (1 - HEEL));
        if (c.used >= c.left - 1e-9 && c.oil <= c.cap * HEEL + 1e-9 && !c.retired) { c.retired = true; retired.push(d.name); }
      }
    }
    // whatever a dome could not deliver, another may
    if (left > 1e-6) { for (const d of w.domes) { for (const c of d.cav.filter(usable).sort((a, b) => a.oil - b.oil)) { if (left <= 1e-9) break; const avail = Math.max(0, c.oil - c.cap * HEEL), t = Math.min(avail, left); c.oil -= t; left -= t; got += t; c.used += t / (c.cap * (1 - HEEL)); } } }
    return { got, retired };
  }

  /* ---- a year passes ---- */
  function yearDecisions(w, dec) {
    // dec: { buy (mb), build (caverns), maintain (0..1 share of wells worked over) }
    const out = { bought: 0, built: 0, spent: 0, notes: [] };
    const price = w.price;
    let buy = clamp(dec.buy || 0, 0, Math.min(roomFor(w), fillCap(w) * 365));
    let cost = buy * price / 1000;
    if (cost > w.budget - out.spent) { buy = Math.max(0, (w.budget - out.spent) * 1000 / price); cost = buy * price / 1000; out.notes.push('The budget did not stretch to the oil you asked for.'); }
    const put = putOil(w, buy); out.bought = put; out.spent += put * price / 1000; w.boughtTotal += put;
    const nBuild = clamp(Math.floor(dec.build || 0), 0, 8);
    for (let i = 0; i < nBuild; i++) {
      if (w.budget - out.spent < BUILD_COST) { out.notes.push('No money left to leach another cavern.'); break; }
      const d = w.domes.filter(x => x.cav.length + x.building.length < x.maxCav).sort((a, b) => (b.maxCav - b.cav.length - b.building.length) - (a.maxCav - a.cav.length - a.building.length))[0];
      if (!d) { out.notes.push('Every dome is built out.'); break; }
      d.building.push(BUILD_YEARS); out.spent += BUILD_COST; out.built++;
    }
    const share = clamp(dec.maintain || 0, 0, 1);
    const wells = w.domes.flatMap(d => d.cav).filter(c => !c.retired);
    const n = Math.round(wells.length * share); const mcost = n * WORKOVER;
    if (mcost <= w.budget - out.spent) { wells.sort((a, b) => a.health - b.health).slice(0, n).forEach(c => { c.health = Math.min(1, c.health + 0.35); c.offline = 0; }); out.spent += mcost; out.maintained = n; }
    else out.notes.push('Not enough left for the well work.');
    w.spentTotal += out.spent; w.budget -= out.spent;
    return out;
  }
  function advanceYear(w) {
    const events = [];
    // caverns under construction
    w.domes.forEach(d => { d.building = d.building.map(t => t - 1); const done = d.building.filter(t => t <= 0).length; d.building = d.building.filter(t => t > 0); for (let i = 0; i < done; i++) d.cav.push(newCavern(d, false, 5)); if (done) events.push({ text: `${done} new cavern${done > 1 ? 's' : ''} finished at ${d.name}.`, cls: 'good' }); });
    // ageing, creep, well failures
    w.domes.forEach(d => d.cav.forEach(c => {
      if (c.retired) return; c.age++; c.cap *= 0.997; c.health = Math.max(0, c.health - 0.02); if (c.offline > 0) c.offline--;
      const pFail = 0.004 * (1 + c.age / 25) * (1.6 - c.health) * (c.acquired ? 1.5 : 1);
      if (rnd() < pFail) { c.offline = 1; const lost = Math.min(c.oil, 0.4); c.oil -= lost; w.budget -= 0.03; events.push({ text: `A well fails at ${d.name}. ${lost > 0.005 ? `${Math.round(lost * 1000)} thousand barrels leak into the caprock; the` : 'The'} cavern is shut for a year of repairs ($30m).`, cls: 'bad' }); }
    }));
    // loans come home
    w.loans = w.loans.filter(l => { if (l.due <= w.year) { const put = putOil(w, l.back); events.push({ text: `${put.toFixed(1)} mb of borrowed oil comes back, premium included.`, cls: 'good' }); return false; } return true; });
    // mandated sales
    w.mandates = w.mandates.filter(m => { if (m.years > 0) { const r = takeOil(w, m.mb); w.treasury += r.got * w.price / 1000; m.years--; events.push({ text: `Congress’s mandated sale: ${r.got.toFixed(1)} mb sold at $${Math.round(w.price)}. The money goes to the Treasury.`, cls: 'bad' }); } return m.years > 0; });
    // year turns
    w.year++; w.week = 0;
    w.price = basePrice(w.year) * (0.94 + rnd() * 0.12); w.spike = 0;
    const carry = Math.max(0, w.budget) * 0.5;  // unspent money mostly goes back
    w.budget = budgetFor(w.year) * (0.8 + w.mood / 250) + carry;
    w.mood = clamp(w.mood + (w.mood < 50 ? 1 : -0.5), 5, 100);
    events.forEach(e => log(w, e.text, e.cls));
    pushHistory(w);
    // scripted?
    const s = SCRIPT.find(x => x.year === w.year && !w.done[x.year]);
    if (s) { w.done[s.year] = true; if (s.kind === 'crisis') return { events, crisis: s }; return { events, card: s }; }
    if (w.year > 2036) { w.phase = 'end'; return { events, end: true }; }
    return { events };
  }

  /* ---- cards ---- */
  function resolveCard(w, card, choice) {
    const out = [];
    const ok = choice.odds == null ? true : rnd() < choice.odds;
    const apply = (c) => {
      if (c.sell) { const r = takeOil(w, c.sell); w.treasury += r.got * w.price / 1000; out.push(`${r.got.toFixed(1)} mb sold at $${Math.round(w.price)}; $${(r.got * w.price / 1000).toFixed(1)}bn to the Treasury.`); }
      if (c.lend) { const r = takeOil(w, c.lend); w.loans.push({ back: c.back, due: w.year + 2 }); out.push(`${r.got.toFixed(1)} mb lent; ${c.back} due back in two years.`); }
      if (c.gain) { const put = putOil(w, c.gain); out.push(`${put.toFixed(1)} mb added.`); }
      if (c.grant) { w.budget += c.grant; out.push(`Congress grants $${c.grant}bn.`); }
      if (c.cost) { w.budget -= c.cost; }
      if (c.lose) { const r = takeOil(w, c.lose); out.push(`${r.got.toFixed(1)} mb lost in the move.`); }
      if (c.mandate) { w.mandates.push({ ...c.mandate }); out.push(`${c.mandate.mb} mb a year will be sold for ${c.mandate.years} years.`); }
      if (c.priceNote) { w.price += c.priceNote; }
    };
    if (ok) { apply(choice); w.mood = clamp(w.mood + (choice.mood || 0), 5, 100); }
    else { out.push('It did not work.'); w.mood = clamp(w.mood + (choice.mood || 0), 5, 100); if (choice.fail) apply(choice.fail); if (choice.grant) out.push('Congress says no.'); }
    if (choice.risk && rnd() < choice.risk.p) { const r = takeOil(w, choice.risk.lose); out.push(choice.risk.text); }
    out.forEach(t => log(w, `${card.name}: ${t}`));
    return out;
  }

  /* ---- crises: weekly ---- */
  function startCrisis(w, s) {
    const weeks = s.weeks[0] + Math.floor(rnd() * (s.weeks[1] - s.weeks[0] + 1));
    w.crisis = { ...s, weeksLeft: weeks, weeksTotal: weeks, week: 0, released: 0, noRelPain: 0, pain: 0, ceasefire: 0, closedAgain: false, revenue: 0, allies: s.iea ? 1 : 0 };
    w.phase = 'crisis'; w.week = 0;
    log(w, `${s.name}. ${s.text}`, 'head');
    if (drawCap(w) <= 0) log(w, 'You have no way to pump oil out. The reserve is a warehouse without a door.', 'bad');
  }
  function crisisWeek(w, releaseMbd) {
    const c = w.crisis; c.week++; w.week++;
    const cap = drawCap(w);
    let events = [];
    // weather and wells
    if (w.hurricane) { w.hurricane.weeks--; if (w.hurricane.weeks <= 0) { w.hurricane = null; events.push({ text: 'The storm has passed. Terminals reopen.', cls: 'good' }); } }
    else if ((c.hurricane && c.week === 1) || (rnd() < 0.05 && [6, 7, 8, 9, 10].includes(((w.year * 52 + c.week) % 52 / 4.33 | 0) + 1))) { w.hurricane = { weeks: 2, x: -0.1 }; events.push({ text: 'A hurricane enters the Gulf. Marine terminals close; half the takeaway is gone.', cls: 'bad' }); }
    if (rnd() < 0.04) { const d = w.domes[Math.floor(rnd() * 4)]; const cv = d.cav.find(usable); if (cv) { cv.offline = 1; const lost = Math.min(cv.oil, 0.4); cv.oil -= lost; events.push({ text: `A well casing fails at ${d.name}. The cavern is shut${lost > 0.005 ? `; ${Math.round(lost * 1000)} thousand barrels leak into the rock` : ''}.`, cls: 'bad' }); } }
    let sourCut = 1; if (rnd() < 0.06 && releaseMbd > 0.5) { sourCut = 0.8; events.push({ text: 'Refiners pass on part of the sour crude offered. A fifth of this week’s barrels find no taker.', cls: 'bad' }); }
    // the strait / the shortfall
    let sf = c.shortfall;
    if (c.ongoing) { if (c.ceasefire > 0) { c.ceasefire--; sf = 0; if (c.ceasefire === 0) { c.closedAgain = true; events.push({ text: 'The strait closes again.', cls: 'bad' }); } } else if (!c.closedAgain && c.week > 8 && rnd() < 0.08) { c.ceasefire = 3; sf = 0; events.push({ text: 'A ceasefire. Tankers move through Hormuz. The shortfall pauses.', cls: 'good' }); } }
    // pump
    const want = Math.min(releaseMbd, cap) * sourCut;
    const r = takeOil(w, want * 7); const got = r.got, perDay = got / 7;
    r.retired.forEach(n => events.push({ text: `${n}: a cavern spent its last drawdown and is retired. Its space is gone for good.`, cls: 'bad' }));
    c.released += got; w.releasedTotal += got;
    // allies cover their share; yours is what the U.S. is expected to add
    const usShare = sf * (c.allies ? IEA_SHARE : 0.7);
    const netNoRel = usShare, net = Math.max(0, usShare - perDay);
    const spikeNoRel = c.spikeK * netNoRel, spike = c.spikeK * net;
    w.spike = spike; w.price = basePrice(w.year) + spike;
    const weekPain = spike * US_DEMAND * 7 / 1000, weekPainNo = spikeNoRel * US_DEMAND * 7 / 1000;   // $bn
    c.pain += weekPain; w.pain += weekPain; c.noRelPain += weekPainNo; w.painAvoided += (weekPainNo - weekPain);
    const rev = got * w.price / 1000; c.revenue += rev; w.treasury += rev;
    // mood: relief when you help, anger when prices bite
    w.mood = clamp(w.mood + (perDay > 0.2 ? 0.6 : 0) - (spike > 15 ? 0.8 : spike > 5 ? 0.3 : 0), 5, 100);
    c.weeksLeft--;
    const over = c.weeksLeft <= 0;
    events.forEach(e => log(w, e.text, e.cls));
    log(w, `week ${c.week}: released ${got.toFixed(1)} mb (${Math.round(perDay * 1000)} kb/d)${want > perDay + 1e-6 ? `, wells could give ${Math.round(cap * 1000)}` : ''}. Crude $${Math.round(w.price)}${sf === 0 ? ' · no shortfall this week' : ''}.`, spike > 15 ? 'bad' : '');
    pushHistory(w);
    if (over) return endCrisis(w);
    return { over: false, got, perDay, cap, price: w.price, spike, events };
  }
  function endCrisis(w) {
    const c = w.crisis; w.phase = 'year'; w.hurricane = null;
    const summary = { name: c.name, weeks: c.week, released: c.released, pain: c.pain, avoided: c.noRelPain - c.pain, revenue: c.revenue, inv: inv(w) };
    log(w, `${c.name} is over after ${c.week} weeks. You released ${c.released.toFixed(1)} mb. Americans paid about $${c.pain.toFixed(0)}bn extra for fuel; without your releases it would have been $${c.noRelPain.toFixed(0)}bn.`, 'head');
    w.mood = clamp(w.mood + Math.min(15, summary.avoided / 8), 5, 100);
    w.crisis = null; w.spike = 0; w.price = basePrice(w.year);
    return { over: true, summary };
  }

  /* ---- the final report ---- */
  function report(w) {
    const i = inv(w), cap = capacity(w);
    const wells = w.domes.flatMap(d => d.cav).filter(c => !c.retired);
    const health = wells.length ? wells.reduce((a, c) => a + c.health, 0) / wells.length : 0;
    const leftAvg = wells.length ? wells.reduce((a, c) => a + Math.max(0, c.left - c.used), 0) / wells.length : 0;
    const score = Math.round(clamp(w.painAvoided * 0.6, 0, 500) + clamp(i / 5, 0, 150) + clamp(health * 100, 0, 100) + clamp(leftAvg * 20, 0, 100) - clamp(w.spentTotal * 3, 0, 150) + clamp(w.treasury * 2, 0, 100));
    const title = score > 700 ? 'Keeper of the Salt' : score > 550 ? 'Steward' : score > 400 ? 'Administrator' : score > 250 ? 'Caretaker' : 'Custodian of an Empty Vault';
    return { inv: i, cap, caverns: wells.length, health, leftAvg, pain: w.pain, avoided: w.painAvoided, spent: w.spentTotal, treasury: w.treasury, bought: w.boughtTotal, released: w.releasedTotal, mood: w.mood, score, title };
  }

  root.SALT = { newWorld, yearDecisions, advanceYear, resolveCard, startCrisis, crisisWeek, inv, capacity, cavCount, drawCap, fillCap, roomFor, report, basePrice, budgetFor, SCRIPT, DOMES, HEEL, CAV_MB, BUILD_COST, WORKOVER, domeOil, domeCap, domeRate, rnd };
})(typeof window !== 'undefined' ? window : globalThis);
