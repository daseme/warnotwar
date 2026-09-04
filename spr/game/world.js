/* SALT — the simulation. Pure model, no DOM. Years 1977–2036.
   Units: mb = million barrels, mb/d = million barrels a day, $bn = billions of dollars. */
'use strict';
(function (root) {
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const rnd = (() => { let seed = 1234567; const f = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }; f.reseed = s => { seed = s >>> 0; }; return f; })();
  const HEEL = 0.02;

  /* ---- the four domes. capacity is what each can hold when fully built out ---- */
  const DOMES = [
    { key: 'bm', name: 'Bryan Mound',    where: 'Freeport, Texas',   sys: 'seaway',  rate: 1.500, fill: 0.225, maxCav: 19, startCav: 4, startLeft: 2, opYear: 1986, x: 0.12 },
    { key: 'bh', name: 'Big Hill',       where: 'Winnie, Texas',     sys: 'texoma',  rate: 1.100, fill: 0.225, maxCav: 14, startCav: 0, startLeft: 5, opYear: 1991, x: 0.36 },
    { key: 'wh', name: 'West Hackberry', where: 'Lake Charles, La.', sys: 'texoma',  rate: 1.300, fill: 0.225, maxCav: 21, startCav: 5, startLeft: 2, opYear: 1988, x: 0.60 },
    { key: 'bc', name: 'Bayou Choctaw',  where: 'Baton Rouge, La.',  sys: 'capline', rate: 0.515, fill: 0.110, maxCav: 6,  startCav: 4, startLeft: 1, opYear: 1987, x: 0.82 },
  ];
  /* ---- the way out: three pipeline systems. a dome's flow is the smallest of its pumps, its line, and the buyers and docks at the end.
          totals from DOE (three contracted terminals 2.22 mb/d, St. James 0.4, design 4.4); the split by system is this model's ---- */
  const SYSTEMS = {
    seaway:  { name: 'Seaway',  where: 'Houston and Texas City',                 domes: ['bm'],       refiners: 0.60, dockCap: 0.70, dockNames: 'Freeport and Texas City' },
    texoma:  { name: 'Texoma',  where: 'Beaumont, Port Arthur and Lake Charles', domes: ['bh', 'wh'], refiners: 1.00, dockCap: 1.39, dockNames: 'Nederland and Beaumont' },
    capline: { name: 'Capline', where: 'south-east Louisiana',                   domes: ['bc'],       refiners: 0.35, dockCap: 0,    doe: 0.40, doeYear: 1981, dockNames: 'St. James' },
  };
  const PIPE_COST = 0.15, PIPE_YEARS = 2;                  // $bn: a bigger line from the dome to its system
  const DOCK_COST = 0.02;                                  // $bn a year: the standing contract for commercial dock space on a system
  const TERM_COST = 1.0, TERM_YEARS = 3, TERM_CAP = 1.0;   // a dedicated marine terminal: yours, immune to congestion
  const congestion = y => y < 2012 ? 0 : Math.min(0.5, (y - 2012) / 12);   // commercial oil filling the shared lines and docks
  const CAV_MB = 10.5;                 // a new cavern
  const BUILD_YEARS = 3, BUILD_COST = 0.04;   // $bn per cavern (leaching, wells, brine line)
  const PLANT_YEARS = 2, PLANT_COST = 0.35;   // $bn per dome: raw-water intake, injection pumps, heat exchangers, pipeline tie-in
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
    { year: 1979, kind: 'crisis', name: 'The Iranian revolution', blind: { name: 'A revolution', text: 'A revolution topples the government of one of the world’s biggest exporters and its output collapses. World supply is short about 2 million barrels a day and queues return to American filling stations. Your caverns hold what you have bought.' }, real: { released: 0, note: 'The real reserve held about 90 million barrels and had no way to pump them out. Nothing was released.' }, text: 'Iran’s output collapses. World supply is short about 2 million barrels a day and queues return to American filling stations. Your caverns hold what you have bought. Your pumps do not exist yet.', shortfall: 2.0, weeks: [30, 45], spikeK: 9 },
    { year: 1986, kind: 'card', name: 'The price collapse', blind: { name: 'The taps open', text: 'The world’s biggest exporter stops defending the price and opens the taps. Crude halves in a few months. Oil has never been cheaper to buy for the reserve, and Congress has never been less interested in paying for it.' }, text: 'Saudi Arabia opens the taps. Crude falls from $28 to $14. Oil has never been cheaper to buy for the reserve, and Congress has never been less interested in paying for it.', choices: [{ label: 'Ask Congress for an extra $2bn to buy at $14', mood: -8, grant: 2.0, odds: 0.6 }, { label: 'Buy what the budget allows', mood: 0 }] },
    { year: 1990, kind: 'crisis', name: 'Iraq invades Kuwait', blind: { name: 'An invasion in the Gulf', text: 'One Gulf producer invades its neighbour, and both countries’ exports stop. The world loses 4.3 million barrels a day. The allies agree a collective release; your share is about 44 percent of whatever the group offers.' }, real: { released: 17.3, note: 'The real reserve sold 17.3 million barrels in the first weeks of the war: its first emergency drawdown.' }, text: 'Iraqi and Kuwaiti exports stop. The world loses 4.3 million barrels a day. The allies agree a collective release; your share is about 44 percent of whatever the group offers.', shortfall: 4.3, weeks: [24, 32], spikeK: 9, iea: true },
    { year: 1993, kind: 'card', name: 'Weeks Island', blind: { name: 'A sinkhole', text: 'A sinkhole opens above an old salt mine the reserve uses for storage. Fresh water is seeping toward 72 million barrels of oil. Engineers say the mine must be emptied within five years.' }, text: 'A sinkhole opens above the old salt mine at Weeks Island. Fresh water is seeping toward 72 million barrels of oil. Engineers say the mine must be emptied within five years.', choices: [{ label: 'Move the oil to new caverns ($0.1bn, lose 1.5 mb)', cost: 0.1, lose: 1.5, mood: 2 }, { label: 'Monitor and hope', risk: { p: 0.5, lose: 20, text: 'The mine floods. Twenty million barrels are lost to the water.' } }] },
    { year: 1996, kind: 'card', name: 'Deficit reduction', blind: { name: 'A sale for the budget', text: 'Congress wants 28 million barrels sold, not for an emergency but to close a budget gap. The money goes to the Treasury, not to you.' }, text: 'Congress wants 28 million barrels sold, not for an emergency but to close a budget gap. The money goes to the Treasury, not to you.', choices: [{ label: 'Comply: sell 28 mb', sell: 28, mood: 3 }, { label: 'Lobby against it (60 % odds)', odds: 0.6, mood: -6, fail: { sell: 28 } }] },
    { year: 2000, kind: 'card', name: 'Heating oil', blind: { name: 'A winter loan', text: 'Heating-oil stocks in the cold states are thin before winter, and it is an election year. The White House wants a 30 million barrel loan: refiners take crude now and return more barrels later.' }, text: 'Northeast distillate stocks are thin before winter and it is an election year. The White House wants a 30 million barrel loan: refiners take crude now and return more barrels later.', choices: [{ label: 'Lend 30 mb, get 31.5 back in two years', lend: 30, back: 31.5, mood: 4 }, { label: 'Refuse: this is not an emergency', mood: -5 }] },
    { year: 2005, kind: 'crisis', name: 'Katrina and Rita', blind: { name: 'Two hurricanes', text: 'Two hurricanes in a month shut a quarter of Gulf production and a fifth of refining. Refiners that can still run are asking to borrow crude at once.' }, real: { released: 20.8, note: 'The real reserve sold 11 million barrels and lent another 9.8 to refiners whose supply had stopped.' }, text: 'Two hurricanes shut a quarter of Gulf production and a fifth of refining. Refiners that can still run are asking to borrow crude at once.', shortfall: 1.5, weeks: [6, 10], spikeK: 12, hurricane: true },
    { year: 2008, kind: 'card', name: 'Oil at $140', blind: { name: 'The price alone', text: 'No barrel has been lost anywhere. Demand from a fast-growing Asian economy has pushed crude to a record and gasoline past a mark it has never reached. Congress demands a release to bring the price down.' }, text: 'No barrel has been lost anywhere. Demand from China has pushed crude to $140 and gasoline over $4. Congress demands a release to bring the price down.', choices: [{ label: 'Release 30 mb to calm the market', sell: 30, mood: 6, priceNote: -4 }, { label: 'Refuse: the reserve is for supply shocks, not prices', mood: -8 }] },
    { year: 2011, kind: 'crisis', name: 'Libya', blind: { name: 'A civil war', text: 'Civil war stops a North African producer’s 1.5 million barrels a day of light sweet crude. The allies propose a 60 million barrel collective release.' }, real: { released: 30.6, note: 'The real reserve sold 30.6 million barrels, the American half of a 60 million barrel allied release.' }, text: 'Civil war stops Libya’s 1.5 million barrels a day of light sweet crude. The allies propose a 60 million barrel collective release.', shortfall: 1.5, weeks: [28, 36], spikeK: 9, iea: true },
    { year: 2015, kind: 'card', name: 'The piggy bank', blind: { name: 'The piggy bank', text: 'Congress has found the reserve. A run of laws over three years will order more than 350 million barrels sold to pay for roads, medical research and tax cuts.' }, text: 'Congress has found the reserve. Eight laws over three years will order more than 350 million barrels sold to pay for highways, medical research and tax cuts.', choices: [{ label: 'Comply as ordered: sell 25 mb a year for six years', mandate: { mb: 25, years: 6 }, mood: 2 }, { label: 'Fight it in hearings (40 % odds)', odds: 0.4, mood: -8, fail: { mandate: { mb: 25, years: 6 } } }] },
    { year: 2017, kind: 'crisis', name: 'Harvey', blind: { name: 'A flood', text: 'A hurricane drops fifty inches of rain on the biggest refining city on the coast. Refineries flood and pipelines stop. The shortfall is short and local, and your own staff are evacuated.' }, real: { released: 5.2, note: 'The real reserve lent 5.2 million barrels to refiners cut off by the flood.' }, text: 'Harvey drops fifty inches of rain on Houston. Refineries flood and pipelines stop. The shortfall is short and local, and your own staff are evacuated.', shortfall: 0.8, weeks: [3, 5], spikeK: 10, hurricane: true },
    { year: 2020, kind: 'card', name: 'Oil at $20', blind: { name: 'The roads empty', text: 'A pandemic empties the roads. Crude drops below $20 and producers are paying people to take it. You could fill every empty cavern for almost nothing. Congress declines the $3bn.' }, text: 'A pandemic empties the roads. Crude drops below $20 and producers are paying people to take it. You could fill every empty cavern for almost nothing. Congress declines the $3bn.', choices: [{ label: 'Lease empty caverns to companies for a fee in barrels (+20 mb)', gain: 20, mood: 3 }, { label: 'Ask Congress again for $3bn (25 % odds)', odds: 0.25, grant: 3.0, mood: -4 }] },
    { year: 2022, kind: 'crisis', name: 'Russia invades Ukraine', blind: { name: 'An invasion in Europe', text: 'A big exporter invades its neighbour. Sanctions and self-sanctioning take up to 2 million barrels a day of its crude off the western market. Crude passes $120. The White House wants a million barrels a day for six months.' }, real: { released: 180, note: 'The real reserve released about 180 million barrels over six months, the largest drawdown in its history.' }, text: 'Sanctions and self-sanctioning take up to 2 million barrels a day of Russian crude off the western market. Brent passes $120. The White House wants a million barrels a day for six months.', shortfall: 2.0, weeks: [40, 52], spikeK: 9, iea: true },
    { year: 2026, kind: 'crisis', name: 'Hormuz', blind: { name: 'The strait', text: 'Strikes close the strait that a fifth of the world’s oil passes through. Twenty million barrels a day stop moving. The allies agree the largest release in history. Nobody knows how long the strait stays shut.' }, real: { released: null, note: 'The real drawdown is still running.' }, text: 'Strikes on Iran close the Strait of Hormuz. Twenty million barrels a day, a fifth of the world’s oil, stop moving. The allies agree the largest release in history. Nobody knows how long the strait stays shut.', shortfall: 8.0, weeks: [26, 60], spikeK: 9, iea: true, ongoing: true },
    { year: 2031, kind: 'crisis', name: 'The Caracas collapse', blind: { name: 'A collapse', text: 'A government falls and its 1.2 million barrels a day of heavy crude stop. Gulf Coast refineries built for heavy oil are the ones hurt.' }, text: 'Venezuela’s government falls and its 1.2 million barrels a day of heavy crude stop. Gulf Coast refineries built for heavy oil are the ones hurt.', shortfall: 1.2, weeks: [20, 30], spikeK: 9 },
    { year: 2034, kind: 'crisis', name: 'The long season', blind: { name: 'The long season', text: 'Three hurricanes in five weeks track across the western Gulf. Production, refining and your own raw-water intakes are hit in turn.' }, text: 'Three hurricanes in five weeks track across the western Gulf. Production, refining and your own raw-water intakes are hit in turn.', shortfall: 1.8, weeks: [8, 12], spikeK: 11, hurricane: true },
  ];

  /* ---- world state ---- */
  function newWorld() {
    rnd.reseed(Date.now() & 0xffffffff);
    const w = {
      year: 1977, week: 0, phase: 'year',      // year | crisis | end
      budget: 1.0, spent: 0, treasury: 0, mood: 60,
      price: basePrice(1977), spike: 0,
      domes: DOMES.map(d => ({ ...d, cav: [], building: [], plant: 'none', pipe: 0.5, pipeWork: 0 })),   // plant: 'none' | years left (number) | 'ready'; pipe: share of the design rate the line carries
      chain: { seaway: { docks: false, terminal: 'none' }, texoma: { docks: false, terminal: 'none' }, capline: { docks: false, terminal: 'none' } },   // terminal: 'none' | years left | 'ready'
      stuck: 0, chainSeen: false,   // chainSeen: the first shock in which the way out, not the wells, set the pace has happened; the controls show from then
      log: [], history: [], pain: 0, painAvoided: 0, releasedTotal: 0, boughtTotal: 0, spentTotal: 0, oilSpend: 0, soldCash: 0, soldCashValue: 0,
      loans: [], mandates: [], crisis: null, done: {}, hurricane: null, flash: null, crisisLog: [], blind: null, pending: null,
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
  function domeRate(w, d) { if (d.plant !== 'ready') return 0; const n = d.cav.filter(c => !c.retired).length; if (!n) return 0; return d.rate * (d.cav.filter(usable).length / Math.max(n, d.maxCav * 0.6)); }
  const drawCap = w => w.domes.reduce((a, d) => a + domeRate(w, d), 0);   // what the wells can push
  const pipeRate = (w, d) => d.rate * d.pipe * (1 - congestion(w.year));
  function takeawayOf(w, k, sourCut) {
    const s = SYSTEMS[k], ch = w.chain[k], c = congestion(w.year);
    const t = s.refiners * (sourCut || 1) + (ch.docks ? s.dockCap * (1 - c) : 0) + (s.doe && w.year >= s.doeYear ? s.doe : 0) + (ch.terminal === 'ready' ? TERM_CAP : 0);
    return t * (w.hurricane ? 0.5 : 1);
  }
  function chainFlows(w, sourCut) {
    // per dome: pumps, line, its share of the system's takeaway, the flow that gets out, and the link that binds
    const out = {};
    for (const k of Object.keys(SYSTEMS)) {
      const ds = w.domes.filter(d => d.sys === k), take = takeawayOf(w, k, sourCut);
      const push = ds.map(d => Math.min(domeRate(w, d), pipeRate(w, d))), tot = push.reduce((a, b) => a + b, 0);
      ds.forEach((d, i) => {
        const pumps = domeRate(w, d), pipe = pipeRate(w, d), share = tot > 1e-9 ? take * push[i] / tot : take / ds.length, flow = Math.min(pumps, pipe, share);
        const bind = pumps <= pipe + 1e-9 && pumps <= share + 1e-9 ? 'pumps' : pipe <= share + 1e-9 ? 'pipe' : 'takeaway';
        out[d.key] = { pumps, pipe, take: share, flow, bind, sys: k };
      });
    }
    return out;
  }
  const deliverCap = (w, sourCut) => Object.values(chainFlows(w, sourCut)).reduce((a, f) => a + f.flow, 0);
  const linesCap = w => w.domes.reduce((a, d) => a + Math.min(domeRate(w, d), pipeRate(w, d)), 0);
  const fillCap = w => w.domes.reduce((a, d) => a + (d.plant === 'ready' ? d.fill : d.fill * 0.5), 0);  // mb/d: filling works with the basic plant, faster with the full one
  const maxSell = w => Math.min(100, drawCap(w) * 365 * 0.5, Math.max(0, inv(w) - 12));   // a calm-year sale: half the year's pumping, at most 100 mb, never the roof oil
  const avgBuy = w => w.boughtTotal > 0 ? w.oilSpend / w.boughtTotal : 0;
  const avgSell = w => w.soldCash > 0 ? w.soldCashValue / w.soldCash : 0;
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
  function drainDome(w, d, mb, retired) {
    let take = mb, got = 0;
    for (const c of d.cav.filter(usable).sort((a, b) => a.oil - b.oil)) {
      if (take <= 1e-9) break;
      const avail = Math.max(0, c.oil - c.cap * HEEL), t = Math.min(avail, take);
      c.oil -= t; take -= t; got += t; c.used += t / (c.cap * (1 - HEEL));
      if (c.used >= c.left - 1e-9 && c.oil <= c.cap * HEEL + 1e-9 && !c.retired) { c.retired = true; retired.push(d.name); }
    }
    return got;
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
    // selling for cash comes first, so the money can be used this same year
    const sellMax = maxSell(w);
    let sell = clamp(dec.sell || 0, 0, sellMax);
    if (sell > 0.05) { const r = takeOil(w, sell); out.sold = r.got; out.saleCash = r.got * price / 1000; w.budget += out.saleCash; w.soldCash += r.got; w.soldCashValue += r.got * price; w.releasedTotal += r.got; w.mood = clamp(w.mood + r.got / 40, 5, 100); out.retired = r.retired; }
    // dock contracts are paid every year they stand, before anything else; they lapse when the money is not there
    for (const k of Object.keys(SYSTEMS)) {
      if (SYSTEMS[k].dockCap <= 0) continue;
      const ch = w.chain[k], want = dec.docks ? !!dec.docks[k] : ch.docks;
      if (!want) { ch.docks = false; continue; }
      if (w.budget - out.spent >= DOCK_COST) { out.spent += DOCK_COST; ch.docks = true; out.docksPaid = (out.docksPaid || []).concat(SYSTEMS[k].name); }
      else { if (ch.docks) out.notes.push(`No money to renew the dock contract on ${SYSTEMS[k].name}. It lapsed.`); ch.docks = false; }
    }
    let buy = clamp(dec.buy || 0, 0, Math.min(roomFor(w), fillCap(w) * 365));
    let cost = buy * price / 1000;
    if (cost > w.budget - out.spent) { buy = Math.max(0, (w.budget - out.spent) * 1000 / price); cost = buy * price / 1000; out.notes.push('The budget did not stretch to the oil you asked for.'); }
    const put = putOil(w, buy); out.bought = put; out.spent += put * price / 1000; w.boughtTotal += put; w.oilSpend += put * price;
    // caverns: per dome if asked (dec.buildAt = {key: n}), else the dome with most free slots takes each one
    out.builtAt = {};
    const digAt = d => { if (w.budget - out.spent < BUILD_COST) { out.notes.push('No money left to leach another cavern.'); return false; } if (d.cav.length + d.building.length >= d.maxCav) return false; d.building.push(BUILD_YEARS); out.spent += BUILD_COST; out.built++; out.builtAt[d.key] = (out.builtAt[d.key] || 0) + 1; return true; };
    if (dec.buildAt) { for (const d of w.domes) { for (let i = 0; i < (dec.buildAt[d.key] || 0); i++) if (!digAt(d)) break; } }
    else { const nBuild = clamp(Math.floor(dec.build || 0), 0, 8); for (let i = 0; i < nBuild; i++) { const d = w.domes.filter(x => x.cav.length + x.building.length < x.maxCav).sort((a, b) => (b.maxCav - b.cav.length - b.building.length) - (a.maxCav - a.cav.length - a.building.length))[0]; if (!d) { out.notes.push('Every dome is built out.'); break; } if (!digAt(d)) break; } }
    // pumps: per dome if asked (dec.pumpsAt = [keys]), else biggest dome without a plant
    const plantAt = d => { if (w.budget - out.spent < PLANT_COST) { out.notes.push('No money left to build a pumping plant.'); return false; } if (d.plant !== 'none') return false; d.plant = PLANT_YEARS; out.spent += PLANT_COST; out.plants = (out.plants || 0) + 1; out.plantAt = (out.plantAt || []).concat(d.name); return true; };
    if (dec.pumpsAt) { for (const k of dec.pumpsAt) { const d = w.domes.find(x => x.key === k); if (d && !plantAt(d)) break; } }
    else { const nPlant = clamp(Math.floor(dec.pumps || 0), 0, 4); for (let i = 0; i < nPlant; i++) { const d = w.domes.filter(x => x.plant === 'none').sort((a, b) => (b.cav.length + b.building.length) - (a.cav.length + a.building.length))[0]; if (!d) { out.notes.push('Every dome already has its pumps, or is building them.'); break; } if (!plantAt(d)) break; } }
    // the way out: a bigger line per dome, a terminal per system, each built once
    for (const key of (dec.pipeAt || [])) { const d = w.domes.find(x => x.key === key); if (!d || d.pipe >= 1 || d.pipeWork > 0) continue; if (w.budget - out.spent < PIPE_COST) { out.notes.push('No money left for a bigger line.'); break; } d.pipeWork = PIPE_YEARS; out.spent += PIPE_COST; out.pipes = (out.pipes || 0) + 1; out.pipeAt = (out.pipeAt || []).concat(d.name); }
    for (const k of (dec.terminalAt || [])) { const ch = w.chain[k]; if (!ch || ch.terminal !== 'none') continue; if (w.budget - out.spent < TERM_COST) { out.notes.push('No money left for a marine terminal.'); break; } ch.terminal = TERM_YEARS; out.spent += TERM_COST; out.terminals = (out.terminals || 0) + 1; out.terminalAt = (out.terminalAt || []).concat(SYSTEMS[k].name); }
    // repairs: shut caverns first, then the weakest wells. dec.maintain is a share; dec.repairShut lists domes whose shut caverns get fixed regardless
    const share = clamp(dec.maintain || 0, 0, 1);
    const wells = w.domes.flatMap(d => d.cav.map(c => ({ c, d }))).filter(o => !o.c.retired);
    const forced = new Set(dec.repairShut || []);
    const order = wells.sort((a, b) => ((b.c.offline > 0) - (a.c.offline > 0)) || (a.c.health - b.c.health));
    let n = Math.round(wells.length * share);
    const picks = new Set(order.slice(0, n).map(o => o.c));
    order.forEach(o => { if (o.c.offline > 0 && forced.has(o.d.key)) picks.add(o.c); });
    n = picks.size; const mcost = n * WORKOVER;
    if (mcost <= w.budget - out.spent) { picks.forEach(c => { c.health = Math.min(1, c.health + 0.35); c.offline = 0; }); out.spent += mcost; out.maintained = n; }
    else out.notes.push('Not enough left for the well repairs.');
    w.spentTotal += out.spent; w.budget -= out.spent;
    return out;
  }
  function advanceYear(w) {
    const events = [];
    // caverns under construction
    w.domes.forEach(d => { d.building = d.building.map(t => t - 1); const done = d.building.filter(t => t <= 0).length; d.building = d.building.filter(t => t > 0); for (let i = 0; i < done; i++) d.cav.push(newCavern(d, false, 5)); if (done) events.push({ text: `${done} new cavern${done > 1 ? 's' : ''} finished at ${d.name}.`, cls: 'good' }); });
    // pumping plants under construction
    w.domes.forEach(d => { if (typeof d.plant === 'number') { d.plant--; if (d.plant <= 0) { d.plant = 'ready'; events.push({ text: `Pumps ready at ${d.name}. Oil can come out of this dome at up to ${Math.round(d.rate * 1000)} thousand barrels a day.`, cls: 'good' }); } } });
    // lines and terminals under construction
    w.domes.forEach(d => { if (d.pipeWork > 0) { d.pipeWork--; if (d.pipeWork <= 0) { d.pipe = 1; events.push({ text: `The bigger line at ${d.name} is in. It carries ${Math.round(d.rate * 1000)} thousand barrels a day.`, cls: 'good' }); } } });
    Object.keys(SYSTEMS).forEach(k => { const ch = w.chain[k]; if (typeof ch.terminal === 'number') { ch.terminal--; if (ch.terminal <= 0) { ch.terminal = 'ready'; events.push({ text: `Your marine terminal on ${SYSTEMS[k].name} opens: ${Math.round(TERM_CAP * 1000)} thousand barrels a day of dock that nobody else uses.`, cls: 'good' }); } } });
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
    if (w.year === SYSTEMS.capline.doeYear) events.push({ text: 'The St. James terminal opens on Capline: 400 thousand barrels a day of dock the reserve owns outright.', cls: 'good' });
    if (w.year === 2012) events.push({ text: 'Shale oil fills the Gulf pipelines. From here the shared lines and contracted docks carry a little less of yours each year. A terminal of your own would not.', cls: 'bad' });
    events.forEach(e => log(w, e.text, e.cls));
    pushHistory(w);
    // scripted?
    if (w.blind && w.year >= w.blind.end) { w.phase = 'end'; return { events, end: true }; }
    const s0 = SCRIPT.find(x => x.year === w.year && !w.done[x.year]);
    if (s0) { const s = blindify(w, s0); w.done[s.year] = true; if (s.kind === 'crisis') return { events, crisis: s }; return { events, card: s }; }
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
    else if (deliverCap(w) < drawCap(w) * 0.7) log(w, `Your wells can flow ${drawCap(w).toFixed(1)} mb/d but the way out takes only ${deliverCap(w).toFixed(1)}: the lines and the docks, not the pumps, set the pace.`, 'bad');
    w.crisis.stuck = 0; w.crisis.bound = { pumps: 0, pipe: 0, takeaway: 0 }; w.crisis.wanted = 0;
    if (!w.chainSeen && drawCap(w) > 0 && deliverCap(w) < drawCap(w) * 0.95) { w.chainSeen = true; w.crisis.bottleneck = true; }
  }
  function crisisWeek(w, releaseMbd) {
    const c = w.crisis; c.week++; w.week++;
    let events = [];
    // weather and wells
    if (w.hurricane) { w.hurricane.weeks--; if (w.hurricane.weeks <= 0) { w.hurricane = null; events.push({ text: 'The storm has passed. Terminals reopen.', cls: 'good' }); } }
    else if ((c.hurricane && c.week === 1) || (rnd() < 0.05 && [6, 7, 8, 9, 10].includes(((w.year * 52 + c.week) % 52 / 4.33 | 0) + 1))) { w.hurricane = { weeks: 2, x: -0.1 }; events.push({ text: 'A hurricane enters the Gulf. Marine terminals close; half the takeaway is gone.', cls: 'bad' }); }
    if (rnd() < 0.04) { const d = w.domes[Math.floor(rnd() * 4)]; const cv = d.cav.find(usable); if (cv) { cv.offline = 1; const lost = Math.min(cv.oil, 0.4); cv.oil -= lost; events.push({ text: `A well casing fails at ${d.name}. The cavern is shut${lost > 0.005 ? `; ${Math.round(lost * 1000)} thousand barrels leak into the rock` : ''}.`, cls: 'bad' }); } }
    let sourCut = 1; if (rnd() < 0.06 && releaseMbd > 0.5) { sourCut = 0.8; events.push({ text: 'Refiners pass on part of the sour crude offered. A fifth of this week’s barrels find no taker.', cls: 'bad' }); }
    // the strait / the shortfall
    let sf = c.shortfall;
    if (c.ongoing) { if (c.ceasefire > 0) { c.ceasefire--; sf = 0; if (c.ceasefire === 0) { c.closedAgain = true; events.push({ text: 'The strait closes again.', cls: 'bad' }); } } else if (!c.closedAgain && c.week > 8 && rnd() < 0.08) { c.ceasefire = 3; sf = 0; events.push({ text: 'A ceasefire. Tankers move through Hormuz. The shortfall pauses.', cls: 'good' }); } }
    // pump, through the chain: each dome delivers the smallest of its pumps, its line and its share of the docks and buyers
    const flows = chainFlows(w, sourCut), pumps = drawCap(w), lines = linesCap(w);
    const cap = Object.values(flows).reduce((a, f) => a + f.flow, 0);
    const want = Math.min(releaseMbd, cap), k = cap > 1e-9 ? want / cap : 0;
    const retired = []; let got = 0;
    w.domes.forEach(d => { got += drainDome(w, d, flows[d.key].flow * k * 7, retired); });
    const perDay = got / 7;
    retired.forEach(n => events.push({ text: `${n}: a cavern spent its last drawdown and is retired. Its space is gone for good.`, cls: 'bad' }));
    // what the knob asked for and the wells could give, but the way out could not carry
    // the knob's ceiling is what can get out, so 'stuck' is what the wells could have added had the way out not been the limit, counted while the knob is at the ceiling
    const atCeiling = releaseMbd >= cap - 1e-6;
    const stuck = atCeiling && pumps > cap + 1e-6 ? (pumps - cap) * 7 : 0; c.stuck += stuck; w.stuck += stuck; c.wanted += releaseMbd * 7;
    let bind = null;
    if (atCeiling && pumps > cap + 1e-6) { const gap = { pipe: 0, takeaway: 0 }; Object.values(flows).forEach(f => { if (f.bind !== 'pumps') gap[f.bind] += f.pumps - f.flow; }); bind = gap.pipe >= gap.takeaway ? 'pipe' : 'takeaway'; c.bound[bind]++; }
    else if (atCeiling && pumps > 1e-6) { bind = 'pumps'; c.bound.pumps++; }
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
    log(w, `week ${c.week}: released ${got.toFixed(1)} mb (${Math.round(perDay * 1000)} kb/d)${bind && bind !== 'pumps' ? `; wells could give ${pumps.toFixed(1)}, the lines carry ${lines.toFixed(1)}, buyers and docks take ${cap.toFixed(1)}` : bind === 'pumps' ? `; the wells could give no more than ${pumps.toFixed(1)}` : ''}. Crude $${Math.round(w.price)}${sf === 0 ? ' · no shortfall this week' : ''}.`, spike > 15 ? 'bad' : '');
    pushHistory(w);
    if (over) return endCrisis(w);
    return { over: false, got, perDay, cap, pumps, lines, flows, bind, price: w.price, spike, events, weekPain, weekPainNo, net, netNoRel };
  }
  function endCrisis(w) {
    const c = w.crisis; w.phase = 'year'; w.hurricane = null;
    const summary = { name: c.name, weeks: c.week, released: c.released, pain: c.pain, avoided: c.noRelPain - c.pain, revenue: c.revenue, inv: inv(w), stuck: c.stuck, bound: c.bound, wanted: c.wanted };
    log(w, `${c.name} is over after ${c.week} weeks. You released ${c.released.toFixed(1)} mb. Americans paid about $${c.pain.toFixed(0)}bn extra for fuel; without your releases it would have been $${c.noRelPain.toFixed(0)}bn.`, 'head');
    w.mood = clamp(w.mood + Math.min(15, summary.avoided / 8), 5, 100);
    w.crisisLog.push({ year: w.year, name: c.name, released: c.released, avoided: summary.avoided });
    w.crisis = null; w.spike = 0; w.price = basePrice(w.year);
    return { over: true, summary };
  }

  /* ---- the blind window: five years somewhere in the record, the reserve as it really stood ---- */
  const blindify = (w, s) => (w.blind && s.blind) ? { ...s, ...s.blind } : s;
  const WINDOWS = [1977, 1989, 1996, 2004, 2008, 2014, 2019, 2022];   // each holds at least one shock or decision; none reaches the invented years
  const LEACH = { bm: [1980, 1988], bh: [1986, 1991], wh: [1980, 1989], bc: [1980, 1986] };   // the years over which each dome’s new caverns were leached
  function seedWorld(start, realInv) {
    const w = newWorld();
    w.year = start; w.blind = { start, end: start + 5 };
    w.price = basePrice(start); w.budget = budgetFor(start) * (0.8 + w.mood / 250);
    w.domes.forEach(d => {
      const [a, b] = LEACH[d.key]; const frac = clamp((start - a) / (b - a), 0, 1);
      const n = Math.round((d.maxCav - d.startCav) * frac);
      for (let i = 0; i < n; i++) { const c = newCavern(d, false, 5); c.age = Math.max(0, Math.round(start - (a + (b - a) * (i + 0.5) / Math.max(1, n)))); c.health = Math.max(0.55, 1 - c.age * 0.012); d.cav.push(c); }
      if (frac > 0 && frac < 1) d.building = [1, 2, 3].slice(0, Math.max(0, Math.min(3, d.maxCav - d.cav.length)));
      d.plant = start >= d.opYear ? 'ready' : start > d.opYear - PLANT_YEARS ? d.opYear - start : 'none';
      d.pipe = start >= 1991 ? 1 : 0.5; d.pipeWork = 0;
    });
    // the way out as the record roughly had it: commercial dock contracts held through the fill years and the 2000s, lapsed otherwise; no terminal of its own, ever
    const held = (start >= 1983 && start <= 1994) || (start >= 2001 && start <= 2011);
    w.chain.seaway.docks = held; w.chain.texoma.docks = held; w.chainSeen = true;
    // the real inventory, spread across the caverns; stretch the caverns if the record held more than the model has room for
    const target = realInv == null ? 7.5 : realInv;
    let cap = capacity(w);
    if (target > cap * 0.98) { const k = target * 1.02 / cap; w.domes.forEach(d => d.cav.forEach(c => { c.cap *= k; })); cap = capacity(w); }
    w.domes.forEach(d => d.cav.forEach(c => { c.oil = c.cap * target / cap; }));
    // drawdowns the real reserve had already spent
    const past = SCRIPT.filter(x => x.kind === 'crisis' && x.year < start && x.real && x.real.released > 0).length;
    if (past) w.domes.forEach(d => d.cav.forEach(c => { if (!c.acquired) c.used = Math.min(c.left - 1, past * 0.4); }));
    if (start > 2015 && start <= 2022) w.mandates.push({ mb: 20, years: 2022 - start + 1 });   // the piggy-bank sales were running
    SCRIPT.forEach(x => { if (x.year < start) w.done[x.year] = true; });
    const s0 = SCRIPT.find(x => x.year === start);
    if (s0) { w.done[start] = true; w.pending = blindify(w, s0); }
    w.history = []; w.log = []; pushHistory(w);
    return w;
  }

  /* ---- what the country feels ---- */
  const gasPrice = (w) => w.price / 42 + 0.30 + (w.year - 1977) * 0.03;      // $/gal: crude plus a margin that grows with the years
  const hum = (w) => clamp(100 - w.spike * 1.8, 8, 100);                       // how much of the country runs normally

  /* ---- the final report ---- */
  function report(w) {
    const i = inv(w), cap = capacity(w);
    const wells = w.domes.flatMap(d => d.cav).filter(c => !c.retired);
    const health = wells.length ? wells.reduce((a, c) => a + c.health, 0) / wells.length : 0;
    const leftAvg = wells.length ? wells.reduce((a, c) => a + Math.max(0, c.left - c.used), 0) / wells.length : 0;
    // the way out: of what the wells could have given in crises, the share that actually got out (nothing released, nothing scored)
    const wayOut = w.releasedTotal + w.stuck > 0.5 ? 100 * (1 - w.stuck / (w.releasedTotal + w.stuck)) : 0;
    const score = Math.round(clamp(w.painAvoided * 0.6, 0, 500) + clamp(i / 5, 0, 150) + clamp(health * 100, 0, 100) + clamp(leftAvg * 20, 0, 100) - clamp(w.spentTotal * 3, 0, 150) + clamp(w.treasury * 2, 0, 100) + clamp(wayOut, 0, 100));
    const title = score > 750 ? 'Keeper of the Salt' : score > 590 ? 'Steward' : score > 430 ? 'Administrator' : score > 270 ? 'Caretaker' : 'Custodian of an Empty Vault';
    return { inv: i, cap, caverns: wells.length, health, leftAvg, pain: w.pain, avoided: w.painAvoided, spent: w.spentTotal, treasury: w.treasury, bought: w.boughtTotal, released: w.releasedTotal, stuck: w.stuck, wayOut, mood: w.mood, score, title };
  }

  root.SALT = { gasPrice, hum, seedWorld, WINDOWS, SYSTEMS, chainFlows, deliverCap, takeawayOf, pipeRate, linesCap, congestion, PIPE_COST, PIPE_YEARS, DOCK_COST, TERM_COST, TERM_YEARS, TERM_CAP, PLANT_COST, PLANT_YEARS, BUILD_YEARS, maxSell, avgBuy, avgSell, newWorld, yearDecisions, advanceYear, resolveCard, startCrisis, crisisWeek, inv, capacity, cavCount, drawCap, fillCap, roomFor, report, basePrice, budgetFor, SCRIPT, DOMES, HEEL, CAV_MB, BUILD_COST, WORKOVER, domeOil, domeCap, domeRate, rnd };
})(typeof window !== 'undefined' ? window : globalThis);
