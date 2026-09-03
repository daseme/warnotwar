/* the reserve — "run the reserve" game
   Week-by-week. You set the release rate. The reserve is four sites of caverns; each cavern keeps a roof-oil heel.
   Rate cap per site = design rate × (caverns still holding usable oil ÷ caverns) × availability. */
'use strict';
(function () {
  const E = window.SPRengine; const { fmt0, fmt1, clamp, el, txt } = E;

  // DOE Quick Facts, Aug 20 2026 site inventories; GAO-26-106918 design rates and availability (Big Hill in LE2 outage)
  const SITES = [
    { key: 'bm', name: 'Bryan Mound',    caverns: 19, capacity: 247.1, rate: 1.500, fill: 0.225, now: 142.5, avail: 1 },
    { key: 'bh', name: 'Big Hill',       caverns: 14, capacity: 170.0, rate: 1.100, fill: 0.225, now: 89.1,  avail: 0 },
    { key: 'wh', name: 'West Hackberry', caverns: 21, capacity: 220.4, rate: 1.300, fill: 0.110, now: 30.5,  avail: 1 },
    { key: 'bc', name: 'Bayou Choctaw',  caverns: 6,  capacity: 76.0,  rate: 0.515, fill: 0.105, now: 32.0,  avail: 1 },
  ];
  const HEEL = 0.02;   // roof oil + brine allowance, Sandia: about 1 % each
  // drawdowns left per cavern (Sandia 2021 baseline, by site): most DOE-built caverns have 5; the old brine caverns 1 or 2
  const BUDGET = {
    bm: [1, 2, 2, 2, 2, 2, 3, 3, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
    bh: [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
    wh: [1, 2, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
    bc: [1, 1, 1, 5, 5, 5],
  };
  const FLOORS = [
    { mb: 300, label: 'Hochstein: nobody goes below 300' },
    { mb: 252.4, label: 'statutory floor for limited draws' },
    { mb: 170, label: 'Rapidan: soft floor' },
    { mb: 70, label: 'DOE: physical minimum' },
  ];

  const SCENARIOS = {
    today:  { label: 'Today, Aug 2026', desc: 'Where the reserve actually stands. Big Hill still in construction.', inv: null, bigHill: 0, shortfall: 1.2, weeksMin: 16, weeksMax: 40 },
    march:  { label: 'March 2026, 415 mb', desc: 'Hormuz closes. You hold what the reserve held on March 11.', inv: 415.4, bigHill: 0, shortfall: 1.6, weeksMin: 20, weeksMax: 44 },
    full:   { label: 'Full reserve, 714 mb', desc: 'The design case. Every site available, all caverns full.', inv: 713.5, bigHill: 1, shortfall: 2.0, weeksMin: 20, weeksMax: 44 },
    y2021:  { label: 'Late 2021, 600 mb', desc: 'Before the 2022 release. Big Hill available.', inv: 600, bigHill: 1, shortfall: 1.6, weeksMin: 20, weeksMax: 44 },
  };

  function makeState(scn) {
    const sites = SITES.map(s => {
      const st = { ...s, cavCap: s.capacity / s.caverns, cav: [], left: BUDGET[s.key].slice(), used: new Array(s.caverns).fill(0), retired: new Array(s.caverns).fill(false) };
      st.avail = s.key === 'bh' ? scn.bigHill : 1;
      let inv = scn.inv == null ? s.now : scn.inv * (s.capacity / 713.5);
      // oil is held cavern by cavern: full caverns first, one partial, the rest at the heel
      st.cav = new Array(s.caverns).fill(0);
      const order = st.left.map((v, i) => i).sort((a, b) => st.left[b] - st.left[a]);
      for (const i of order) { const put = clamp(inv, 0, st.cavCap); st.cav[i] = put; inv -= put; }
      return st;
    });
    return { sites, week: 0, drawn: 0, delivered: 0, unmet: 0, shortfallTotal: 0, log: [], over: false, orderedAt: null, leachMb: 0,
      weeks: scn.weeksMin + Math.floor(Math.random() * (scn.weeksMax - scn.weeksMin + 1)), shortfall: scn.shortfall, events: [], hurricaneUntil: -1, ceasefireUntil: -1, closedAgain: false };
  }
  const inv = st => st.sites.reduce((a, s) => a + s.cav.reduce((x, y) => x + y, 0), 0);
  const usableCav = s => s.cav.filter(v => v > s.cavCap * HEEL + 1e-9).length;
  function cap(st) {
    // per-site cap: design rate × share of caverns with oil above the heel × availability; hurricane halves marine/pipeline takeaway
    let c = 0;
    st.sites.forEach(s => { c += s.rate * (usableCav(s) / s.caverns) * s.avail; });
    if (st.week <= st.hurricaneUntil) c *= 0.5;
    return c;
  }
  function draw(st, mbPerDay) {
    // take from the fullest caverns first, site by site in proportion to each site's cap
    let want = mbPerDay * 7; const c = cap(st); if (c <= 0 || want <= 0) return 0;
    let got = 0;
    st.sites.forEach(s => {
      const siteCap = s.rate * (usableCav(s) / s.caverns) * s.avail * (st.week <= st.hurricaneUntil ? 0.5 : 1);
      let take = want * (siteCap / c);
      // finish the emptiest cavern first: the reserve is drawn cavern by cavern, so wells drop out as caverns reach the heel
      const order = s.cav.map((v, i) => i).filter(i => s.cav[i] > s.cavCap * HEEL + 1e-9).sort((a, b) => s.cav[a] - s.cav[b]);
      for (const i of order) {
        if (take <= 0) break;
        const avail = Math.max(0, s.cav[i] - s.cavCap * HEEL); const t = Math.min(avail, take);
        s.cav[i] -= t; take -= t; got += t;
        s.used[i] += t / (s.cavCap * (1 - HEEL));               // fraction of one drawdown: emptying a cavern to its heel = one spent
        if (s.used[i] >= s.left[i] - 1e-9 && s.cav[i] <= s.cavCap * HEEL + 1e-9 && !s.retired[i]) { s.retired[i] = true; st.events.push([st.week, `${s.name}: a cavern has spent its last drawdown and is being retired. ${fmt1(s.cavCap)} million barrels of space are gone for good.`, 'bad']); }
      }
    });
    st.leachMb += got * 0.15;  // Sandia: raw water dissolves salt equal to ~15 % of the oil displaced
    return got;
  }
  function step(st, rate) {
    st.week++;
    // what happens this week, decided before the pumps run
    const r = Math.random(); let sourCut = 1;
    if (r < 0.06 && st.week > st.hurricaneUntil + 3) { st.hurricaneUntil = st.week + 2; st.events.push([st.week, 'A Gulf hurricane closes the marine terminals. Half the takeaway is gone for two weeks.', 'bad']); }
    else if (r < 0.10) { const s = st.sites[Math.floor(Math.random() * 4)]; if (s.avail) { const i = s.cav.findIndex((v, k) => v > s.cavCap * HEEL && !s.retired[k]); if (i >= 0) { const lost = Math.min(0.4, s.cav[i] - s.cavCap * HEEL); s.cav[i] -= lost; st.events.push([st.week, `A well casing fails at ${s.name}. About ${fmt0(lost * 1000)} thousand barrels leak into the rock and the cavern is shut for repair.`, 'bad']); } } }
    else if (r < 0.14 && !st.closedAgain && st.week > 6 && st.ceasefireUntil < 0) { st.ceasefireUntil = st.week + 3; st.events.push([st.week, 'A ceasefire. Tankers move through Hormuz again. The shortfall pauses.', 'good']); }
    else if (st.week === st.ceasefireUntil + 1 && !st.closedAgain && st.ceasefireUntil > 0) { st.closedAgain = true; st.events.push([st.week, 'The strait closes again.', 'bad']); }
    if (r > 0.94 && rate > 0.6) { sourCut = 0.8; st.events.push([st.week, 'Refiners pass on part of the sour crude offered. A fifth of this week\'s barrels find no taker.', 'bad']); }
    const c = cap(st); rate = Math.min(rate, c) * sourCut;
    const got = draw(st, rate);
    const perDay = got / 7;
    let sf = st.shortfall;
    if (st.week <= st.ceasefireUntil) sf = 0;
    st.shortfallTotal += sf * 7; st.delivered += got;
    const unmet = Math.max(0, sf - perDay) * 7; st.unmet += unmet;
    if (st.week >= st.weeks) st.over = true;
    return { rate, got, perDay, sf, unmet, cap: c, sourCut };
  }
  const retiredCount = st => st.sites.reduce((a, s) => a + s.retired.filter(Boolean).length, 0);
  const retiredMb = st => st.sites.reduce((a, s) => a + s.retired.filter(Boolean).length * s.cavCap, 0);
  const drawdownsSpent = st => st.sites.reduce((a, s) => a + s.used.reduce((x, y) => x + y, 0), 0);

  window.SPRgame = { SITES, SCENARIOS, makeState, step, cap, inv, HEEL, FLOORS, BUDGET, retiredCount, retiredMb, drawdownsSpent };
  if (typeof document === 'undefined' || !document.getElementById('g-scn')) return;

  /* ---------- UI ---------- */
  const $ = id => document.getElementById(id);
  const scnSel = $('g-scn'), startBtn = $('g-start'), rateIn = $('g-rate'), rateOut = $('g-rate-out'), weekBtn = $('g-week'), runBtn = $('g-run'), logEl = $('g-log'), strip = $('g-strip'), verdict = $('g-verdict');
  let st = null, scn = null, autorun = null;
  Object.entries(SCENARIOS).forEach(([k, v]) => { const o = document.createElement('option'); o.value = k; o.textContent = v.label; scnSel.appendChild(o); });
  scnSel.onchange = () => { $('g-scn-desc').textContent = SCENARIOS[scnSel.value].desc; };
  $('g-scn-desc').textContent = SCENARIOS.today.desc;

  function renderStrip() {
    strip.innerHTML = '';
    st.sites.forEach(s => {
      const card = document.createElement('div'); card.className = 'site';
      const siteInv = s.cav.reduce((a, b) => a + b, 0);
      const siteCap = s.rate * (usableCav(s) / s.caverns) * s.avail;
      card.innerHTML = `<h3>${s.name}</h3><div class="where">${s.avail ? `${usableCav(s)} of ${s.caverns} caverns hold oil` : 'offline · construction'}</div>`;
      const cols = Math.min(s.caverns, 11), rows = Math.ceil(s.caverns / cols);
      const W = 220, cw = W / cols, ch = 46, H = rows * (ch + 8) + 4;
      const svg = el('svg', { viewBox: `0 0 ${W} ${H}` }, card);
      s.cav.forEach((v, i) => {
        const cx = (i % cols) * cw + cw / 2, top = 4 + Math.floor(i / cols) * (ch + 8), w = cw * 0.52;
        el('rect', { x: cx - w / 2, y: top, width: w, height: ch, rx: w / 2, fill: 'var(--brine)', opacity: s.avail ? 0.55 : 0.25 }, svg);
        const f = clamp(v / s.cavCap, 0, 1), oh = ch * f;
        el('rect', { x: cx - w / 2, y: top, width: w, height: oh, rx: Math.min(w / 2, oh / 2), fill: 'var(--oil)', opacity: s.avail ? 1 : 0.5 }, svg);
        el('rect', { x: cx - w / 2, y: top, width: w, height: ch, rx: w / 2, fill: 'none', stroke: 'var(--ink-30)' }, svg);
      });
      const dl = document.createElement('dl');
      dl.innerHTML = `<dt>oil</dt><dd>${fmt1(siteInv)} mb</dd><dt>can flow</dt><dd>${fmt1(siteCap * 1000)} kb/d</dd>`;
      card.appendChild(dl); strip.appendChild(card);
    });
  }
  function renderReadouts(last) {
    const i = inv(st), c = cap(st);
    $('g-inv').textContent = fmt1(i); $('g-cap').textContent = fmt1(c); $('g-week-n').textContent = st.week;
    $('g-deliv').textContent = fmt1(st.delivered); $('g-unmet').textContent = fmt1(st.unmet);
    const covered = st.shortfallTotal > 0 ? 100 * (1 - st.unmet / st.shortfallTotal) : 100;
    $('g-cover').textContent = fmt0(covered) + '%';
    const m = $('g-meter'); m.style.width = (100 * i / 713.5).toFixed(1) + '%'; m.className = i < 170 ? 'bad' : i < 300 ? 'warn' : '';
    rateIn.max = Math.max(0.1, c).toFixed(2); if (+rateIn.value > c) rateIn.value = c.toFixed(2); rateOut.textContent = fmt1(+rateIn.value * 1000) + ' kb/d';
    $('g-leach').textContent = fmt1(st.leachMb);
    $('g-floor').textContent = FLOORS.filter(f => i < f.mb).map(f => f.label).join(' · ') || 'above every floor anyone has named';
  }
  function log(week, text, cls) { const d = document.createElement('div'); d.textContent = `wk ${week} · ${text}`; if (cls) d.className = cls; logEl.prepend(d); }

  function start() {
    scn = SCENARIOS[scnSel.value]; st = makeState(scn);
    logEl.innerHTML = ''; verdict.hidden = true; weekBtn.disabled = false; runBtn.disabled = false; startBtn.textContent = 'restart';
    log(0, `${scn.label}. ${fmt1(inv(st))} million barrels in the ground. The strait is shut. U.S. refiners are short about ${fmt1(scn.shortfall * 1000)} thousand barrels a day. Nobody knows for how long.`);
    log(0, 'Your first barrels reach the market about two weeks after you order them, so set a rate now.');
    renderStrip(); renderReadouts();
  }
  function week() {
    if (!st || st.over) return;
    const rate = +rateIn.value;
    const r = step(st, rate);
    let line = `released ${fmt1(r.got)} mb (${fmt1(r.perDay * 1000)} kb/d)`;
    if (r.cap < rate - 1e-6) line += ` · asked ${fmt1(rate * 1000)}, the wells could only give ${fmt1(r.cap * 1000)}`;
    if (r.sf === 0) line += ' · ceasefire, no shortfall'; else if (r.unmet > 0) line += ` · short ${fmt1(r.unmet)} mb`; else line += ' · shortfall covered';
    log(st.week, line, r.unmet > 0 && r.sf > 0 ? 'bad' : (r.sf > 0 ? 'good' : ''));
    while (st.events.length) { const [w, t, c] = st.events.shift(); log(w, t, c); }
    renderStrip(); renderReadouts(r);
    if (st.over) finish();
  }
  function finish() {
    weekBtn.disabled = true; runBtn.disabled = true; if (autorun) { clearInterval(autorun); autorun = null; runBtn.textContent = 'run to the end'; }
    const i = inv(st), covered = st.shortfallTotal > 0 ? 100 * (1 - st.unmet / st.shortfallTotal) : 100;
    const refillDays = Math.max(0, (scn.inv == null ? 415.4 : scn.inv) - i) / 0.44;
    const spent = drawdownsSpent(st), nRet = retiredCount(st), mbRet = retiredMb(st);
    let v = `The crisis ran ${st.week} weeks. You released ${fmt1(st.delivered)} million barrels and covered ${fmt0(covered)} percent of the shortfall. ${fmt1(i)} million barrels are left. `;
    if (i < 70) v += 'You went under what DOE calls the physical minimum. The last oil sits as a blanket on cavern roofs and cannot come out without leaching the roof. ';
    else if (i < 170) v += 'You are below the level Rapidan calls a soft floor. Few caverns still hold oil, so the reserve could not respond fast to a second shock. ';
    else if (i < 252.4) v += 'You are under the 252.4 million barrel line Congress set for limited draws. Only an emergency finding could authorise the next release. ';
    else if (i < 300) v += 'You stayed above the statutory line but below 300, the level a former White House energy adviser said no one believes the reserve should cross. ';
    else v += 'You kept the reserve above every floor anyone has named. ';
    v += `Refilling to where you started would take about ${fmt0(refillDays / 30)} months at today's effective fill rate of 440 thousand barrels a day, if the money and the oil were there. `;
    v += `The water you pumped in dissolved about ${fmt1(st.leachMb)} million barrels of salt, growing the caverns it ran through. Sandia counts that as ${fmt0(spent)} drawdowns spent, about one for each cavern you emptied, out of five for a new cavern and one or two for the old brine caverns. `;
    v += nRet ? `${nRet} cavern${nRet > 1 ? 's' : ''} spent the last one and will be retired: ${fmt1(mbRet)} million barrels of space gone for good.` : 'No cavern spent its last one; the wear shows up decades from now, not this year.';
    verdict.textContent = v; verdict.hidden = false;
  }
  startBtn.onclick = start;
  weekBtn.onclick = week;
  runBtn.onclick = () => { if (autorun) { clearInterval(autorun); autorun = null; runBtn.textContent = 'run to the end'; return; } runBtn.textContent = 'pause'; autorun = setInterval(() => { week(); if (!st || st.over) { clearInterval(autorun); autorun = null; runBtn.textContent = 'run to the end'; } }, 450); };
  rateIn.oninput = () => { rateOut.textContent = fmt1(+rateIn.value * 1000) + ' kb/d'; };
  weekBtn.disabled = true; runBtn.disabled = true;

})();
