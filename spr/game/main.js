/* SALT — the interface */
'use strict';
(function () {
  const S = window.SALT; const $ = id => document.getElementById(id);
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const f0 = n => Math.round(n).toLocaleString('en-US'), f1 = n => (Math.round(n * 10) / 10).toFixed(1), bn = n => `$${(Math.round(n * 100) / 100).toFixed(n < 10 ? 2 : 1)}bn`;
  const params = new URLSearchParams(location.search);
  let w = S.newWorld();
  const scene = new window.SALTScene($('scene'), w);
  scene.onFocus = i => { $('focus-note').textContent = i == null ? 'click a dome to zoom · four salt domes, sixty caverns' : `${w.domes[i].name} · click again to zoom out · numbers under each cavern: barrels, drawdowns left`; };
  let real = null; fetch('../data/spr_stocks.json').then(r => r.json()).then(d => { real = d; }).catch(() => {});
  let autorun = null, pendingCrisis = null;

  /* ---------- instruments ---------- */
  const I = window.Instruments;
  const gPrice = new I.Gauge($('g-price'), { min: 0, max: 200, ticks: 4, minor: 5, label: 'crude $/bbl', zones: [{ from: 100, to: 200, color: '#c0392b' }] });
  const gGas = new I.Gauge($('g-gas'), { min: 0, max: 8, ticks: 4, minor: 4, label: 'pump · $/gal', zones: [{ from: 4, to: 8, color: '#c0392b' }], fmt: v => `$${v}` });
  const gFuel = new I.Gauge($('g-fuel'), { min: 0, max: 1, ticks: 4, minor: 2, label: 'reserve', labels: ['E', '¼', '½', '¾', 'F'], zones: [{ from: 0, to: 0.25, color: '#c0392b' }] });
  const gFlow = new I.Gauge($('g-flow'), { min: 0, max: 5, ticks: 5, minor: 4, label: 'wells · mb/day', zones: [{ from: 4.4, to: 5, color: '#c0392b' }, { from: 0, to: 1, color: '#7a6a2a' }] });
  const gMood = new I.Gauge($('g-mood'), { min: 0, max: 100, ticks: 4, minor: 5, label: 'congress', zones: [{ from: 0, to: 30, color: '#c0392b' }, { from: 70, to: 100, color: '#2e8b6e' }] });
  const oInv = new I.Counter($('o-inv'), { digits: 3 }), oCap = new I.Counter($('o-cap'), { digits: 3 }), oBudget = new I.Counter($('o-budget'), { digits: 2, decimals: 2, prefix: '$' }), oTreas = new I.Counter($('o-treasury'), { digits: 3, decimals: 1, prefix: '$' }), oYear = new I.Counter($('o-year'), { digits: 4 });
  const lStorm = new I.Lamp($('l-storm'), { color: 'amber', label: 'storm' }), lWell = new I.Lamp($('l-well'), { color: 'red', label: 'well fail' }), lPumps = new I.Lamp($('l-pumps'), { color: 'green', label: 'pumps' }), lEmerg = new I.Lamp($('l-emerg'), { color: 'red', label: 'emergency' });
  let lastWellFail = -99;

  /* ---------- HUD ---------- */
  function hud() {
    oYear.set(w.year); $('h-phase').textContent = w.phase === 'crisis' ? w.crisis.name : 'the year';
    gPrice.set(w.price, `$${f0(w.price)}`); gGas.set(S.gasPrice(w), `$${S.gasPrice(w).toFixed(2)}`);
    const i = S.inv(w), cap = S.capacity(w);
    oInv.set(i); oCap.set(Math.max(0, cap - i)); gFuel.set(cap > 0 ? i / cap : 0, `${f0(i)} / ${f0(cap)}`);
    gFlow.set(S.drawCap(w), `${f1(S.drawCap(w))}`);
    oBudget.set(Math.max(0, w.budget)); oTreas.set(w.treasury);
    gMood.set(w.mood, `${f0(w.mood)}`);
    const wellDown = w.domes.some(d => d.cav.some(c => c.offline > 0));
    if (wellDown) lastWellFail = w.year;
    lStorm.set(!!w.hurricane, !!w.hurricane); lWell.set(wellDown, w.phase === 'crisis' && wellDown); lPumps.set(S.drawCap(w) > 0); lEmerg.set(w.phase === 'crisis', w.phase === 'crisis' && w.spike > 15);
    $('r-count').textContent = `${w.log.length} entries`;
  }
  function renderLog() { const L = $('log'); L.innerHTML = w.log.slice(0, 120).map(e => `<div class="${e.cls}"><span>${e.year}${e.week ? ` w${e.week}` : ''}</span>${e.text}</div>`).join(''); }

  /* ---------- year panel: throttle, repairs switch, site cards ---------- */
  const yo = $('y-oil'), ym = $('y-maint');
  const REPAIR = [{ name: 'off', share: 0, note: 'nothing repaired; failures likelier each year' }, { name: 'routine', share: 0.25, note: 'a quarter of wells, shut caverns first' }, { name: 'full', share: 0.6, note: 'six in ten wells; failures rare' }];
  const kMaint = new I.Knob($('k-maint'), ym, { label: '', detents: 2, fmt: v => REPAIR[Math.round(v)].name });
  const plan = { build: {}, pumps: new Set(), repairShut: new Set() };
  const resetPlan = () => { plan.build = {}; plan.pumps.clear(); plan.repairShut.clear(); yo.value = 0; ym.value = 0; kMaint.refresh(); };
  const oilVal = () => { const v = +yo.value; return Math.abs(v) < 3 ? 0 : v; };   // a detent at zero

  /* the statement of the year, if the record has one */
  function onRecord() {
    const R = window.SALT_STATEMENTS || []; const card = $('record');
    const s = R.find(x => x.year === w.year);
    if (!s || (!s.quote && !s.fact)) { if (w.year > 2026) { card.hidden = false; $('rec-date').textContent = String(w.year); $('rec-quote').textContent = 'The record ends in 2026. What Washington says from here is yours to imagine.'; $('rec-quote').className = 'rec-quote fact'; $('rec-who').innerHTML = ''; $('rec-ctx').textContent = ''; } else card.hidden = true; return; }
    card.hidden = false; $('rec-date').textContent = s.date || String(s.year);
    $('rec-quote').textContent = s.quote ? `“${s.quote}”` : s.fact; $('rec-quote').className = 'rec-quote' + (s.quote ? '' : ' fact');
    $('rec-who').innerHTML = s.quote ? `${s.speaker}, ${s.title}<a href="${s.source_url}" target="_blank" rel="noopener">${s.source_name} ↗</a>` : `<a href="${s.source_url}" target="_blank" rel="noopener" style="margin-left:0">${s.source_name} ↗</a>`;
    $('rec-ctx').textContent = s.context || '';
  }

  function yearPanel() {
    $('p-year').hidden = false; $('p-crisis').hidden = true; onRecord();
    const era = w.domes.every(d => d.plant === 'none') ? 'No dome has pumps. Nothing you hold can come out until you build them.' : w.year < 1986 ? 'Congress is generous while the embargo is fresh. Build.' : w.year < 1992 ? 'Money is tightening. Finish the domes and fill them.' : w.year < 2000 ? 'The nineties: no money, cheap oil, and Congress eyeing your barrels.' : w.year < 2015 ? 'Oil from federal leases trickles in. Keep the wells alive.' : w.year < 2023 ? 'Congress sells your oil to pay for other things. Hold what you can.' : 'Refill years. Every barrel you buy now is one you can pump later.';
    let realNote = '';
    if (real) { const row = real.monthly.find(r => r[0].startsWith(`${w.year}-01`)) || real.weekly.find(r => r[0].startsWith(`${w.year}-01`)); if (row) realNote = ` The real reserve held ${f0(row[1])} mb at the start of ${w.year}; you hold ${f0(S.inv(w))}.`; }
    $('y-brief').textContent = era + realNote;
    $('y-budget').textContent = bn(Math.max(0, w.budget));
    siteCards(); yearOut();
  }

  /* the four site cards: each dome orders its own pumps, caverns and repairs */
  function siteCards() {
    const host = $('sites'); host.innerHTML = '';
    w.domes.forEach(d => {
      const card = document.createElement('div'); card.className = 'site-card'; card.dataset.key = d.key;
      const shut = d.cav.filter(c => c.offline > 0 && !c.retired).length, slots = d.maxCav - d.cav.length - d.building.length, live = d.cav.filter(c => !c.retired).length;
      const plant = d.plant === 'ready' ? `<span class="good">pumps ready · ${Math.round(d.rate * 1000)} kb/d</span>` : typeof d.plant === 'number' ? `<span class="warn">pumps in ${d.plant} yr</span>` : `<span class="bad">no pumps</span>`;
      card.innerHTML = `<h4>${d.name}<i>${f0(S.domeOil(d))}/${f0(S.domeCap(d))} mb</i></h4>
        <div class="st">${plant} · ${live} cavern${live === 1 ? '' : 's'}${d.building.length ? `, ${d.building.length} leaching` : ''}${shut ? ` · <span class="bad">${shut} shut</span>` : ''}</div>
        <div class="ctl"></div><div class="fx"></div>`;
      const ctl = card.querySelector('.ctl');
      if (d.plant === 'none') { const b = document.createElement('button'); b.className = 'sc-btn pumps' + (plan.pumps.has(d.key) ? ' on' : ''); b.innerHTML = `${plan.pumps.has(d.key) ? '✓ pumps ordered' : 'build pumps'}<small>$350m · ready ${w.year + S.PLANT_YEARS}</small>`; b.onclick = () => { plan.pumps.has(d.key) ? plan.pumps.delete(d.key) : plan.pumps.add(d.key); siteCards(); yearOut(); }; ctl.appendChild(b); }
      if (slots > 0) { const wrap = document.createElement('div'); wrap.className = 'stepper-wrap'; const n = plan.build[d.key] || 0; wrap.innerHTML = `<div class="stepper"><button data-d="-1" ${n <= 0 ? 'disabled' : ''}>−</button><output>${n}</output><button data-d="1" ${n >= slots ? 'disabled' : ''}>+</button></div><span>dig<br>$40m · ${slots} slot${slots > 1 ? 's' : ''}</span>`; wrap.querySelectorAll('button').forEach(b => b.onclick = () => { plan.build[d.key] = clamp((plan.build[d.key] || 0) + (+b.dataset.d), 0, slots); siteCards(); yearOut(); }); ctl.appendChild(wrap); }
      if (shut) { const b = document.createElement('button'); b.className = 'sc-btn' + (plan.repairShut.has(d.key) ? ' on' : ''); b.innerHTML = `${plan.repairShut.has(d.key) ? '✓ repair ordered' : `repair ${shut} shut`}<small>$2m each · reopens this year</small>`; b.onclick = () => { plan.repairShut.has(d.key) ? plan.repairShut.delete(d.key) : plan.repairShut.add(d.key); siteCards(); yearOut(); }; ctl.appendChild(b); }
      if (!ctl.children.length) ctl.innerHTML = '<span class="st" style="margin:0">built out and pumping</span>';
      host.appendChild(card);
    });
  }

  /* what this year's settings would do, computed without touching the world */
  function project() {
    const v = oilVal(), buy = Math.max(0, v), sell = Math.max(0, -v), p = w.price, share = REPAIR[Math.round(+ym.value)].share;
    const cavs = w.domes.flatMap(d => d.cav.map(c => ({ c, d })));
    const drain = new Map(); let left = sell;
    cavs.filter(o => o.d.plant === 'ready' && !o.c.retired && o.c.offline <= 0 && o.c.oil > o.c.cap * S.HEEL).sort((a, b) => a.c.oil - b.c.oil).forEach(o => { if (left <= 1e-9) return; const avail = o.c.oil - o.c.cap * S.HEEL, t = Math.min(avail, left); drain.set(o.c, o.c.oil - t); left -= t; });
    const sold = sell - left, cashIn = sold * p / 1000;
    const fill = new Map(); let room = 0; left = buy;
    cavs.filter(o => !o.c.retired && o.c.offline <= 0).sort((a, b) => (b.c.left - a.c.left) || (b.c.health - a.c.health)).forEach(o => { const cur = drain.has(o.c) ? drain.get(o.c) : o.c.oil; const rm = Math.max(0, o.c.cap - cur); room += rm; if (left <= 1e-9) return; const t = Math.min(rm, left); if (t > 0.01) fill.set(o.c, cur + t); left -= t; });
    const bought = buy - left, cBuy = bought * p / 1000;
    const newCav = { ...plan.build }; const dug = Object.values(newCav).reduce((a, b) => a + b, 0), cBuild = dug * S.BUILD_COST;
    const pumpDomes = new Set(plan.pumps); let addRate = 0;
    pumpDomes.forEach(k => { const d = w.domes.find(x => x.key === k); addRate += d.rate * Math.min(1, d.cav.filter(c => !c.retired && c.oil > c.cap * S.HEEL).length / Math.max(1, d.maxCav * 0.6)); });
    const cP = pumpDomes.size * S.PLANT_COST;
    const wellsAll = cavs.filter(o => !o.c.retired); const shutAll = wellsAll.filter(o => o.c.offline > 0);
    const picks = new Set(wellsAll.slice().sort((a, b) => ((b.c.offline > 0) - (a.c.offline > 0)) || (a.c.health - b.c.health)).slice(0, Math.round(wellsAll.length * share)).map(o => o.c));
    shutAll.forEach(o => { if (plan.repairShut.has(o.d.key)) picks.add(o.c); });
    const nRep = picks.size, cM = nRep * S.WORKOVER, reopen = shutAll.filter(o => picks.has(o.c)).length;
    const reopenRate = shutAll.filter(o => picks.has(o.c)).reduce((a, o) => a + (o.d.plant === 'ready' ? o.d.rate / Math.max(1, o.d.maxCav * 0.6) : 0), 0);
    return { buy, sell, sold, cashIn, fill, drain, bought, cBuy, newCav, dug, cBuild, pumpDomes, addRate, cP, nRep, cM, shut: shutAll.length, reopen, reopenRate, room, share, left: w.budget + cashIn - cBuy - cBuild - cP - cM };
  }

  function yearOut() {
    const sellMax = Math.floor(S.maxSell(w)), buyMax = Math.floor(Math.min(S.roomFor(w), S.fillCap(w) * 365));
    yo.min = -sellMax; yo.max = buyMax; if (+yo.value > buyMax) yo.value = buyMax; if (+yo.value < -sellMax) yo.value = -sellMax;
    if (Math.abs(+yo.value) < 3 && +yo.value !== 0) yo.value = 0;
    const P = project(); const p = w.price, m$ = v => `$${Math.round(v * 1000)}m`, sep = '<i>·</i>', fillKbd = Math.round(S.fillCap(w) * 1000);
    const inv0 = S.inv(w), cap0 = S.capacity(w), draw0 = S.drawCap(w);
    /* throttle */
    $('th-mode').textContent = P.buy > 0 ? `buying ${f0(P.bought)} mb` : P.sell > 0 ? `selling ${f0(P.sold)} mb` : 'hold';
    const months = P.bought > 0 ? Math.max(1, Math.round(P.bought / (S.fillCap(w) * 30.4))) : 0, ab = S.avgBuy(w);
    $('y-spec-oil').innerHTML = P.sell > 0
      ? `<b>$${f0(p)}/bbl</b>${sep}cash this year${sep}max ${sellMax} mb${ab ? `${sep}your cost $${f0(ab)} → <span class="${p >= ab ? 'good' : 'bad'}">${p >= ab ? 'gain' : 'loss'} $${f0(Math.abs(p - ab))}/bbl</span>` : ''}`
      : `<b>$${f0(p)}/bbl</b>${sep}pours in at ${fillKbd} kb/d${sep}${P.buy > 0 ? `arrives over <b>${months} mo</b>` : `buy up to <b>${buyMax} mb</b>${sellMax ? `, sell up to ${sellMax}` : ''}`}${P.room < buyMax + 1 && buyMax > 0 ? `${sep}<span class="warn">room is the limit</span>` : ''}`;
    const fx = (cost, effect, none) => `<span class="cost">${cost}</span><span class="fx${none ? ' none' : ''}">${effect}</span>`;
    $('y-oil-o').innerHTML = P.buy > 0 ? fx(`${f0(P.bought)} mb · ${bn(P.cBuy)}`, `+${f0(P.bought)} mb in the ground${P.bought < P.buy - 0.5 ? ', room ran out' : ''}`) : P.sell > 0 ? fx(`${f0(P.sold)} mb · +${bn(P.cashIn)}`, `−${f0(P.sold)} mb in the ground · +${bn(P.cashIn)} to spend now`) : fx('hold', 'no oil bought or sold', true);
    /* repairs switch */
    const R = REPAIR[Math.round(+ym.value)]; $('sw-pos').textContent = R.name; kMaint.refresh();
    const wells = w.domes.flatMap(d => d.cav).filter(c => !c.retired).length;
    $('y-spec-maint').innerHTML = `<b>${m$(S.WORKOVER)}/well</b>${sep}${R.note}${P.shut ? `${sep}<span class="bad">${P.shut} cavern${P.shut > 1 ? 's' : ''} shut</span>` : ''}`;
    $('y-maint-o').innerHTML = P.nRep ? fx(`${P.nRep} of ${wells} wells · ${bn(P.cM)}`, `${P.nRep} wells made safer${P.reopen ? ` · ${P.reopen} shut cavern${P.reopen > 1 ? 's' : ''} reopen${P.reopen > 1 ? '' : 's'}` : ''}`) : fx(`0 of ${wells} wells · $0.00bn`, 'nothing repaired', true);
    /* site card impact lines */
    document.querySelectorAll('.site-card').forEach(card => { const d = w.domes.find(x => x.key === card.dataset.key); const parts = []; if (P.pumpDomes.has(d.key)) parts.push(`+${f1(d.rate * Math.min(1, d.cav.filter(c => !c.retired && c.oil > c.cap * S.HEEL).length / Math.max(1, d.maxCav * 0.6)))} mb/day of flow in ${w.year + S.PLANT_YEARS} · $350m`); const n = P.newCav[d.key] || 0; if (n) parts.push(`+${f1(n * S.CAV_MB)} mb of space in ${w.year + S.BUILD_YEARS} · ${bn(n * S.BUILD_COST)}`); if (plan.repairShut.has(d.key)) { const k = d.cav.filter(c => c.offline > 0 && !c.retired).length; parts.push(`${k} cavern${k > 1 ? 's' : ''} back this year · ${bn(k * S.WORKOVER)}`); } card.querySelector('.fx').innerHTML = parts.join('<br>'); });
    /* the appropriation bar */
    const total = w.budget + P.cashIn, over = P.left < 0;
    const seg = (cls, v) => `<i class="${cls}" style="width:${clamp(v / Math.max(total, 1e-9) * 100, 0, 100).toFixed(1)}%"></i>`;
    $('ap-bar').innerHTML = seg('buy', P.cBuy) + seg('dig', P.cBuild) + seg('pumps', P.cP) + seg('rep', P.cM) + (over ? seg('over', -P.left) : seg('left', P.left));
    $('ap-legend').innerHTML = `<span><b style="background:#6b5b3e"></b>oil ${bn(P.cBuy)}</span><span><b style="background:#8b8474"></b>caverns ${bn(P.cBuild)}</span><span><b style="background:#5f7d93"></b>pumps ${bn(P.cP)}</span><span><b style="background:#b08a3c"></b>repairs ${bn(P.cM)}</span><span><b style="background:rgba(233,226,208,0.2)"></b>${over ? `<span style="color:var(--danger)">over by ${bn(-P.left)}</span>` : `left ${bn(P.left)}`}</span>${P.cashIn > 0.005 ? `<span class="sale">+${bn(P.cashIn)} from the sale is in the total</span>` : ''}<span>of ${bn(total)}</span>`;
    /* ghost needles and odometer deltas */
    const inv1 = inv0 + P.bought - P.sold;
    gFuel.setGhost(cap0 > 0 && Math.abs(inv1 - inv0) > 0.5 ? inv1 / cap0 : null, Math.abs(inv1 - inv0) > 0.5 ? `${inv1 > inv0 ? '+' : '−'}${f0(Math.abs(inv1 - inv0))} mb` : '');
    oInv.setDelta(Math.abs(inv1 - inv0) > 0.5 ? `${inv1 > inv0 ? '+' : '−'}${f0(Math.abs(inv1 - inv0))}` : '', inv1 < inv0 ? 'neg' : '');
    oCap.setDelta(P.dug ? `+${f0(P.dug * S.CAV_MB)} in ${w.year + S.BUILD_YEARS}` : (Math.abs(inv1 - inv0) > 0.5 ? `${inv1 > inv0 ? '−' : '+'}${f0(Math.abs(inv1 - inv0))}` : ''), inv1 > inv0 && !P.dug ? 'neg' : '');
    const draw1 = draw0 + P.addRate + P.reopenRate;
    gFlow.setGhost(draw1 - draw0 > 0.02 ? draw1 : null, P.addRate > 0.02 ? `+${f1(P.addRate)} in ${w.year + S.PLANT_YEARS}` : P.reopenRate > 0.02 ? `+${f1(P.reopenRate)} now` : '');
    oBudget.setDelta(Math.abs(w.budget - Math.max(0, P.left)) > 0.005 ? `→ ${bn(Math.max(0, P.left))} left` : '', over ? 'neg' : '');
    gMood.setGhost(P.sold > 0.5 ? clamp(w.mood + P.sold / 40, 5, 100) : null, P.sold > 0.5 ? 'sale' : '');
    scene.preview = (P.fill.size || P.drain.size || P.dug || P.pumpDomes.size) ? { fill: P.fill, drain: P.drain, newCav: P.newCav, pumpDomes: P.pumpDomes } : null;
    /* money line and the button */
    const nextGrant = S.budgetFor(w.year + 1) * (0.8 + w.mood / 250);
    $('y-money').innerHTML = `Money: unspent cash carries over, but Congress cuts next year’s grant by half of it. Next year’s grant looks like about <b>${bn(nextGrant)}</b>${P.left > 0.05 ? `; carrying ${bn(P.left)} would make it about <b>${bn(Math.max(0, nextGrant - P.left * 0.5) + P.left)}</b> in hand` : ''}.`;
    const L = $('y-left'); L.textContent = bn(Math.abs(P.left)) + (over ? ' short' : ''); L.style.color = over ? 'var(--danger)' : 'var(--ink)';
    $('y-go').disabled = over;
    $('y-budget').textContent = bn(Math.max(0, w.budget)) + (P.cashIn > 0.005 ? ` + ${bn(P.cashIn)} from the sale` : '');
  }
  const clearGhosts = () => { scene.preview = null; [gFuel, gFlow, gMood].forEach(g => g.setGhost(null)); [oInv, oCap, oBudget].forEach(o => o.setDelta('')); };
  yo.addEventListener('input', yearOut); ym.addEventListener('input', yearOut);

  async function turnYear() {
    $('y-go').disabled = true; clearGhosts();
    const snap = { year: w.year, inv: S.inv(w), cap: S.capacity(w), draw: S.drawCap(w), budget: w.budget, mood: w.mood, price: w.price, gas: S.gasPrice(w) };
    const v = oilVal();
    const dec = { buy: Math.max(0, v), sell: Math.max(0, -v), maintain: REPAIR[Math.round(+ym.value)].share, buildAt: { ...plan.build }, pumpsAt: [...plan.pumps], repairShut: [...plan.repairShut] };
    const before = new Map(w.domes.flatMap(d => d.cav).map(c => [c, c.oil]));
    const out = S.yearDecisions(w, dec);
    const poured = w.domes.flatMap(d => d.cav).filter(c => c.oil - (before.get(c) ?? c.oil) > 0.05).map(c => ({ cv: c, from: before.get(c), to: c.oil }));
    if (poured.length) { const dur = Math.min(4000, 700 + poured.length * 550); scene.flow.in = Math.min(0.8, out.bought / 100); scene.animateFill(poured, dur); $('y-brief').textContent = `Pouring ${f1(out.bought)} million barrels into ${poured.length} cavern${poured.length > 1 ? 's' : ''}…`; await wait(dur + 150); scene.flow.in = 0; }
    out.notes.forEach(n => w.log.unshift({ year: w.year, week: 0, text: n, cls: 'bad' }));
    if (out.sold > 0.05) { const ab = S.avgBuy(w); w.log.unshift({ year: w.year, week: 0, text: `Sold ${f1(out.sold)} mb at $${f0(w.price)}: ${bn(out.saleCash)} into your account${ab ? ` (your oil cost $${f0(ab)} a barrel on average)` : ''}.`, cls: 'good' }); }
    if (out.bought > 0.05 && w.soldCash > 0 && w.price < S.avgSell(w)) w.log.unshift({ year: w.year, week: 0, text: `Buying back at $${f0(w.price)} what you sold at an average of $${f0(S.avgSell(w))}: the buy-low, sell-high argument both administrations made.`, cls: 'good' });
    if (out.bought > 0.05) w.log.unshift({ year: w.year, week: 0, text: `Bought ${f1(out.bought)} mb at $${f0(w.price)} for ${bn(out.bought * w.price / 1000)}${out.built ? `; started ${out.built} cavern${out.built > 1 ? 's' : ''}` : ''}${out.maintained ? `; repaired ${out.maintained} wells` : ''}.` });
    else if (out.built || out.maintained) w.log.unshift({ year: w.year, week: 0, text: `${out.built ? `Started ${out.built} cavern${out.built > 1 ? 's' : ''}` : ''}${out.built && out.maintained ? '; ' : ''}${out.maintained ? `repaired ${out.maintained} wells` : ''}.` });
    if (out.plants) w.log.unshift({ year: w.year, week: 0, text: `Began building pumps at ${out.plantAt.join(' and ')}. Ready in ${S.PLANT_YEARS} years.`, cls: 'good' });
    const r = S.advanceYear(w);
    scene.say(String(w.year), r.crisis ? r.crisis.name : r.card ? r.card.name : '');
    resetPlan();
    hud(); renderLog(); yearPanel();
    const next = () => { if (r.end) return endGame(); if (r.card) return showCard(r.card); if (r.crisis) return crisisIntro(r.crisis); $('y-go').disabled = false; };
    receipt(snap, dec, out, r, next);
  }

  /* ---------- the year-end receipt: what you spent, what you got, what moved ---------- */
  function receipt(snap, dec, out, r, next) {
    const now = { inv: S.inv(w), cap: S.capacity(w), draw: S.drawCap(w), budget: w.budget, mood: w.mood, price: w.price, gas: S.gasPrice(w) };
    const d = (a, b, fmt, unit = '') => { const x = b - a; if (Math.abs(x) < (fmt === f1 ? 0.05 : 0.5)) return `<span class="flat">no change</span>`; return `<span class="${x > 0 ? 'up' : 'down'}">${x > 0 ? '+' : '−'}${fmt(Math.abs(x))}${unit}</span>`; };
    const spent = [];
    if (out.sold > 0.05) spent.push(['sold oil', `${f1(out.sold)} mb`, `+${bn(out.saleCash)}`]);
    if (out.bought > 0.05) spent.push(['bought oil', `${f1(out.bought)} mb at $${f0(snap.price)}`, bn(out.bought * snap.price / 1000)]);
    if (out.built) spent.push(['caverns started', `${Object.entries(out.builtAt || {}).map(([k, n]) => `${n} at ${w.domes.find(d => d.key === k).name.split(' ')[0]}`).join(', ')} · ready ${snap.year + S.BUILD_YEARS}`, bn(out.built * S.BUILD_COST)]);
    if (out.plants) spent.push(['pumps started', `${out.plantAt.join(', ')} · ready ${snap.year + S.PLANT_YEARS}`, bn(out.plants * S.PLANT_COST)]);
    if (out.maintained) spent.push(['wells repaired', `${out.maintained}`, bn(out.maintained * S.WORKOVER)]);
    const spentRows = spent.length ? spent.map(([a, b, c]) => `<tr><td>${a}</td><td>${b}</td><td class="num">${c}</td></tr>`).join('') : `<tr><td colspan="3" class="flat">You spent nothing.</td></tr>`;
    const notes = (out.notes || []).map(n => `<div class="bad">${n}</div>`).join('');
    const events = (r.events || []).map(e => `<div class="${e.cls || ''}">${e.text}</div>`).join('') || '<div class="flat">A quiet year underground.</div>';
    const grant = now.budget;
    modal(`<div class="kicker">${snap.year} → ${w.year} · the receipt</div><h2>${snap.year} in the books</h2>
      <table class="receipt"><thead><tr><th>you did</th><th></th><th class="num">cost</th></tr></thead><tbody>${spentRows}</tbody></table>${notes}
      <div class="kicker" style="margin-top:12px">what happened</div><div class="events">${events}</div>
      <div class="kicker" style="margin-top:12px">the dials</div>
      <table class="receipt dials"><tbody>
        <tr><td>barrels in the ground</td><td class="num">${f0(snap.inv)} → ${f0(now.inv)} mb</td><td class="num">${d(snap.inv, now.inv, f0, ' mb')}</td></tr>
        <tr><td>room to fill</td><td class="num">${f0(snap.cap - snap.inv)} → ${f0(now.cap - now.inv)} mb</td><td class="num">${d(snap.cap - snap.inv, now.cap - now.inv, f0, ' mb')}</td></tr>
        <tr><td>wells can flow</td><td class="num">${f1(snap.draw)} → ${f1(now.draw)} mb/day</td><td class="num">${d(snap.draw, now.draw, f1, ' mb/d')}</td></tr>
        <tr><td>crude</td><td class="num">$${f0(snap.price)} → $${f0(now.price)}</td><td class="num">${d(snap.price, now.price, f0, '')}</td></tr>
        <tr><td>congress</td><td class="num">${f0(snap.mood)} → ${f0(now.mood)}</td><td class="num">${d(snap.mood, now.mood, f0, '')}</td></tr>
        <tr><td>money for ${w.year}</td><td class="num">${bn(Math.max(0, grant))}</td><td class="num"><span class="flat">grant + what you carried</span></td></tr>
      </tbody></table>
      <div class="foot"><label class="skip mono"><input type="checkbox" id="m-skip"> skip receipts</label><button class="btn primary" id="m-ok">${r.crisis ? 'there is news →' : r.card ? 'a decision waits →' : `on to ${w.year} →`}</button></div>`);
    if (skipReceipts || (params.get('bot') && !params.get('receipt'))) { closeModal(); return next(); }
    $('m-skip').onchange = e => { skipReceipts = e.target.checked; };
    $('m-ok').onclick = () => { closeModal(); next(); };
  }
  let skipReceipts = false;
  $('y-go').onclick = turnYear;

  /* ---------- cards ---------- */
  function modal(html) { $('modal-card').innerHTML = html; $('modal').classList.add('show'); }
  function closeModal() { $('modal').classList.remove('show'); }
  function showCard(card) {
    modal(`<div class="kicker">${w.year} · a decision</div><h2>${card.name}</h2><p>${card.text}</p><div class="choices">${card.choices.map((c, i) => `<button class="btn" data-i="${i}">${c.label}</button>`).join('')}</div><div class="result" id="m-result"></div><div class="foot" id="m-foot"></div>`);
    $('modal-card').querySelectorAll('.choices button').forEach(b => b.onclick = () => {
      const out = S.resolveCard(w, card, card.choices[+b.dataset.i]);
      $('modal-card').querySelectorAll('.choices button').forEach(x => { x.disabled = true; if (x === b) x.classList.add('primary'); });
      $('m-result').innerHTML = out.join('<br>') || 'Done.'; $('m-result').className = 'result' + (out.some(t => /did not|lost|flood|says no/.test(t)) ? ' bad' : '');
      $('m-foot').innerHTML = '<button class="btn primary" id="m-ok">continue →</button>'; $('m-ok').onclick = () => { closeModal(); hud(); renderLog(); yearPanel(); $('y-go').disabled = false; };
    });
  }

  /* ---------- crises ---------- */
  function crisisIntro(s) {
    pendingCrisis = s;
    modal(`<div class="kicker">${w.year} · emergency</div><h2>${s.name}</h2><p>${s.text}</p><p class="mono" style="font-size:12px;color:var(--ink-60)">World short about ${f1(s.shortfall)} mb/d. ${s.iea ? `Allies cover their part; your share is about ${f1(s.shortfall * 0.44)} mb/d.` : `Most of this lands on you: about ${f1(s.shortfall * 0.7)} mb/d.`} Your wells can flow ${f1(S.drawCap(w))} mb/d${S.drawCap(w) <= 0 ? ' — nothing. No dome has a pumping plant.' : ''}. You hold ${f0(S.inv(w))} mb.</p>
      <div class="kicker" style="margin-top:8px">how the desk works</div>
      <div class="desk-list">
        <div><b>The year stops.</b> Time now moves one week at a time. Press <b>next week</b> for one week, or flip the <b>clock</b> to run and watch.</div>
        <div><b>The knob sets your release</b> in millions of barrels a day. Its ceiling is what your wells can flow${S.drawCap(w) <= 0 ? ', which is nothing yet: no dome has pumps, so the knob is dead and you can only watch' : ''}.</div>
        <div><b>The goal: keep the country humming.</b> The world is short; allies cover some; what is left uncovered sets the price of crude, and so the price at the pump, the queue at the station and the lights in the city. Your barrels fill the gap. Every barrel you release now is one you will not have for the next shock.</div>
      </div>
      <div class="foot"><button class="btn primary" id="m-ok">take the desk →</button></div>`);
    $('m-ok').onclick = () => { closeModal(); clearGhosts(); S.startCrisis(w, s); lastWeek = null; scene.say(s.name, 'emergency'); crisisPanel(); hud(); renderLog(); };
  }
  /* ---------- the country: a filling station, a skyline, the bill ---------- */
  const country = (() => {
    const host = $('country'); const W = 640, H = 96; let built = false, wins = [], cars = [], txt = {};
    const NS = 'http://www.w3.org/2000/svg'; const el = (tag, a, p) => { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
    function build() {
      host.innerHTML = ''; const svg = el('svg', { viewBox: `0 0 ${W} ${H}` }, host);
      // road
      el('rect', { x: 0, y: 72, width: W, height: 24, fill: '#14130f' }, svg); el('line', { x1: 0, x2: W, y1: 84, y2: 84, stroke: 'rgba(233,226,208,0.25)', 'stroke-dasharray': '10 10' }, svg);
      // station: canopy, pump, sign
      el('rect', { x: 250, y: 30, width: 90, height: 6, fill: '#c9c2b4' }, svg); el('rect', { x: 256, y: 36, width: 3, height: 36, fill: '#9a958a' }, svg); el('rect', { x: 331, y: 36, width: 3, height: 36, fill: '#9a958a' }, svg);
      el('rect', { x: 290, y: 52, width: 10, height: 20, fill: '#8a877f' }, svg);
      el('rect', { x: 350, y: 18, width: 44, height: 26, rx: 3, fill: '#15130f', stroke: '#9a958a' }, svg); el('rect', { x: 371, y: 44, width: 2, height: 28, fill: '#9a958a' }, svg);
      txt.gasLab = el('text', { x: 372, y: 28, 'text-anchor': 'middle', 'font-size': 6.5, fill: 'rgba(233,226,208,0.6)' }, svg); txt.gasLab.textContent = 'REGULAR';
      txt.gas = el('text', { x: 372, y: 40, 'text-anchor': 'middle', 'font-size': 10, fill: '#f0a058' }, svg);
      // cars in the queue, right to left
      for (let i = 0; i < 12; i++) { const g = el('g', { class: 'car', transform: `translate(${236 - i * 20},0)` }, svg); el('rect', { x: 0, y: 60, width: 16, height: 8, rx: 2, fill: i % 3 ? '#8a877f' : '#c9c2b4' }, g); el('rect', { x: 3, y: 56, width: 9, height: 5, rx: 1, fill: '#5a5852' }, g); el('circle', { cx: 4, cy: 69, r: 2.2, fill: '#15130f' }, g); el('circle', { cx: 12, cy: 69, r: 2.2, fill: '#15130f' }, g); cars.push(g); }
      // skyline with windows
      const bl = [[420, 34, 22], [446, 50, 18], [468, 26, 26], [498, 42, 20], [522, 30, 24], [550, 46, 16], [570, 22, 30], [604, 38, 28]];
      bl.forEach(([x, h, wdt]) => { el('rect', { x, y: 72 - h, width: wdt, height: h, fill: '#23211c' }, svg); for (let yy = 72 - h + 4; yy < 68; yy += 6) for (let xx = x + 3; xx < x + wdt - 3; xx += 5) wins.push(el('rect', { class: 'win', x: xx, y: yy, width: 2.4, height: 3, fill: '#ffd27a', opacity: 0.9 }, svg)); });
      // factory
      el('rect', { x: 20, y: 44, width: 60, height: 28, fill: '#23211c' }, svg); el('rect', { x: 28, y: 20, width: 6, height: 24, fill: '#2f2c26' }, svg); el('rect', { x: 44, y: 26, width: 6, height: 18, fill: '#2f2c26' }, svg);
      txt.smoke = el('g', {}, svg); for (let i = 0; i < 3; i++) el('circle', { cx: 31 + i * 5, cy: 16 - i * 5, r: 3 + i, fill: 'rgba(233,226,208,0.18)' }, txt.smoke);
      txt.fac = el('text', { x: 50, y: 66, 'text-anchor': 'middle', 'font-size': 6.5, fill: 'rgba(233,226,208,0.5)' }, svg); txt.fac.textContent = 'REFINERY';
      // captions
      txt.hum = el('text', { x: 636, y: 12, 'text-anchor': 'end', 'font-size': 8, fill: 'rgba(233,226,208,0.7)' }, svg);
      txt.bill = el('text', { x: 6, y: 12, 'font-size': 8, fill: 'rgba(233,226,208,0.7)' }, svg);
      txt.bill2 = el('text', { x: 6, y: 92, 'font-size': 7.5, fill: 'rgba(233,226,208,0.45)' }, svg);
      built = true;
    }
    function set(st) {
      if (!built) build();
      const hum = S.hum(w), lit = Math.round(wins.length * hum / 100);
      wins.forEach((r, i) => r.setAttribute('opacity', i < lit ? 0.9 : 0.06));
      const q = Math.min(12, Math.round(w.spike / 3));
      cars.forEach((g, i) => { g.setAttribute('opacity', i < q ? 1 : 0); });
      txt.gas.textContent = `$${S.gasPrice(w).toFixed(2)}`;
      txt.smoke.setAttribute('opacity', (hum / 100).toFixed(2));
      txt.hum.textContent = `the country · ${f0(hum)}% humming`;
      const c = w.crisis;
      txt.bill.textContent = c ? `this week Americans paid ${st && st.weekPain != null ? bn(st.weekPain) : '$0.00bn'} extra · so far ${bn(c.pain)}` : '';
      txt.bill2.textContent = c ? `without your barrels it would be ${bn(c.noRelPain)} · your releases have saved ${bn(Math.max(0, c.noRelPain - c.pain))}` : '';
    }
    return { set, reset: () => { built = false; } };
  })();

  const cr = $('c-rate');
  const knob = new I.Knob($('k-rate'), cr, { label: 'release · mb/day', detents: 22, fmt: v => v.toFixed(2) });
  const tgRun = new I.Toggle($('tg-run'), { label: 'clock', off: 'hold', on: 'run', onchange: on => { if (on) { if (!autorun) autorun = setInterval(week, S.drawCap(w) <= 0 ? 220 : 700); } else stopRun(); } });
  function crisisPanel() {
    $('p-year').hidden = true; $('p-crisis').hidden = false;
    const c = w.crisis, cap = S.drawCap(w);
    $('c-name').textContent = c.name; $('c-week').textContent = `week ${c.week + 1}`;
    $('c-short').innerHTML = `${f1(c.ceasefire > 0 ? 0 : c.shortfall)}<small>mb/d</small>`; $('c-share').innerHTML = `${f1((c.ceasefire > 0 ? 0 : c.shortfall) * (c.allies ? 0.44 : 0.7))}<small>mb/d</small>`; $('c-cap').innerHTML = `${f1(cap)}<small>mb/d</small>`;
    cr.max = Math.max(0.05, cap).toFixed(2); if (+cr.value > cap) cr.value = cap.toFixed(2); knob.refresh();
    $('c-note').textContent = cap <= 0 ? 'no pumps: you can only watch' : c.week === 0 ? 'first barrels reach the market in about two weeks' : `${f0(S.inv(w))} mb left · crude $${f0(w.price)}`;
    $('k-rate').classList.toggle('dead', cap <= 0);
    country.set(lastWeek);
    $('c-help').innerHTML = cap <= 0
      ? `<b>You cannot pump.</b> No dome has a pumping plant, so the knob does nothing. Flip the <b>clock</b> to run and let the weeks pass, or press <b>next week</b>. The lesson of 1979 is the one the real reserve learned: oil in the ground is not oil at the pump.`
      : `<b>Knob:</b> how much to release each day, up to the ${f1(cap)} mb/day your wells can flow. Turn it by dragging around the dial, scrolling on it, or pressing − and +. <b>Next week</b> runs one week; the <b>clock</b> keeps running them. The world is short ${f1(c.ceasefire > 0 ? 0 : c.shortfall)} mb/day and your share to cover is ${f1((c.ceasefire > 0 ? 0 : c.shortfall) * (c.allies ? 0.44 : 0.7))}; release that much and the price spike mostly goes away. Release less and Americans pay more; release more and you run dry sooner.`;
  }
  let lastWeek = null;
  function week() {
    if (w.phase !== 'crisis') return;
    const r = S.crisisWeek(w, +cr.value); lastWeek = r;
    scene.flow.out = r.over ? 0 : Math.min(4.4, r.perDay);
    hud(); renderLog();
    if (r.over) { stopRun(); scene.flow.out = 0; return crisisEnd(r.summary); }
    crisisPanel();
  }
  function stopRun() { if (autorun) { clearInterval(autorun); autorun = null; } tgRun.set(false); }
  $('c-week-btn').onclick = week;
  function crisisEnd(s) {
    modal(`<div class="kicker">${w.year} · after ${s.weeks} weeks</div><h2>${s.name} is over.</h2><div class="stats"><div class="stat2"><div class="l">released</div><div class="v">${f1(s.released)}<small>mb</small></div></div><div class="stat2"><div class="l">extra fuel cost to americans</div><div class="v">${bn(s.pain)}</div></div><div class="stat2"><div class="l">your releases saved</div><div class="v">${bn(s.avoided)}</div></div><div class="stat2"><div class="l">to the treasury</div><div class="v">${bn(s.revenue)}</div></div><div class="stat2"><div class="l">left in the ground</div><div class="v">${f0(s.inv)}<small>mb</small></div></div><div class="stat2"><div class="l">congress</div><div class="v">${f0(w.mood)}<small>/100</small></div></div></div><p>${verdictLine(s)}</p><div class="foot"><button class="btn primary" id="m-ok">back to the year →</button></div>`);
    $('m-ok').onclick = () => { closeModal(); hud(); renderLog(); yearPanel(); $('y-go').disabled = false; };
  }
  function verdictLine(s) {
    if (s.released < 1) return 'You did not pump. Whether that was prudence or paralysis depends on what comes next.';
    if (s.avoided > s.pain) return 'Your barrels did more good than the shock did harm. That is the reserve working as designed.';
    if (s.inv < 150) return 'You blunted the shock, but the vault is nearly empty. The next one will find you with fewer wells to run.';
    return 'You helped, and you kept most of the oil. The price still bit, because one country’s reserve cannot replace the world’s.';
  }

  /* ---------- the end ---------- */
  function endGame() {
    const R = S.report(w);
    const chart = compareChart();
    modal(`<div class="kicker">2036 · the report</div><div class="grade">your title</div><div class="big">${R.title}</div>
      <div class="stats"><div class="stat2"><div class="l">in the ground</div><div class="v">${f0(R.inv)}<small>of ${f0(R.cap)} mb</small></div></div><div class="stat2"><div class="l">caverns</div><div class="v">${R.caverns}<small>avg ${f1(R.leftAvg)} drawdowns left</small></div></div><div class="stat2"><div class="l">well health</div><div class="v">${f0(R.health * 100)}<small>%</small></div></div>
      <div class="stat2"><div class="l">saved americans</div><div class="v">${bn(R.avoided)}</div></div><div class="stat2"><div class="l">they still paid extra</div><div class="v">${bn(R.pain)}</div></div><div class="stat2"><div class="l">you spent</div><div class="v">${bn(R.spent)}</div></div>
      <div class="stat2"><div class="l">to the treasury</div><div class="v">${bn(R.treasury)}</div></div><div class="stat2"><div class="l">bought · released</div><div class="v">${f0(R.bought)}<small>· ${f0(R.released)} mb</small></div></div><div class="stat2"><div class="l">score</div><div class="v">${R.score}</div></div></div>
      <figure>${chart}<div class="legend"><span><i style="background:var(--gold)"></i>your reserve</span><span><i style="background:rgba(239,232,216,0.7)"></i>what really happened (EIA)</span></div></figure>
      <p style="margin-top:12px">${R.inv > 500 ? 'You leave a full vault. The real reserve never held more than 727 million barrels, and holds 287 today.' : R.inv > 280 ? 'You leave the reserve about where the real one stands in 2026.' : 'You leave less than the real reserve held at its 2026 low.'} ${R.avoided > 100 ? 'Your releases spared Americans more than the real ones did.' : ''}</p>
      <div class="foot"><a class="btn" href="/spr/">read how it works</a><button class="btn primary" id="m-again">play again</button></div>`);
    $('m-again').onclick = () => location.reload();
  }
  function compareChart() {
    const W = 580, H = 220, L = 40, R = 12, T = 14, B = 24;
    const x = y => L + (y - 1977) / (2037 - 1977) * (W - L - R), yv = v => H - B - v / 800 * (H - T - B);
    let s = `<svg viewBox="0 0 ${W} ${H}">`;
    for (let v = 0; v <= 800; v += 200) s += `<line x1="${L}" x2="${W - R}" y1="${yv(v)}" y2="${yv(v)}" stroke="rgba(239,232,216,0.1)"/><text x="${L - 6}" y="${yv(v) + 3}" fill="rgba(239,232,216,0.45)" font-size="9" font-family="IBM Plex Mono, monospace" text-anchor="end">${v}</text>`;
    for (let y = 1980; y <= 2035; y += 5) s += `<text x="${x(y)}" y="${H - 8}" fill="rgba(239,232,216,0.45)" font-size="9" font-family="IBM Plex Mono, monospace" text-anchor="middle">${y}</text>`;
    if (real) { const pts = real.monthly.concat(real.weekly.filter(r => r[0] > real.monthly[real.monthly.length - 1][0])).filter((r, i) => i % 3 === 0); s += `<path d="${pts.map((r, i) => `${i ? 'L' : 'M'}${x(+r[0].slice(0, 4) + (+r[0].slice(5, 7) - 1) / 12).toFixed(1)},${yv(r[1]).toFixed(1)}`).join('')}" fill="none" stroke="rgba(239,232,216,0.7)" stroke-width="1.4"/>`; }
    s += `<path d="${w.history.map((h, i) => `${i ? 'L' : 'M'}${x(h.year).toFixed(1)},${yv(h.inv).toFixed(1)}`).join('')}" fill="none" stroke="var(--gold)" stroke-width="2"/>`;
    s += `<path d="${w.history.map((h, i) => `${i ? 'L' : 'M'}${x(h.year).toFixed(1)},${yv(h.cap).toFixed(1)}`).join('')}" fill="none" stroke="var(--gold)" stroke-width="1" stroke-dasharray="3 3" opacity="0.6"/>`;
    return s + '</svg>';
  }

  /* ---------- start ---------- */
  function start() { $('title').classList.remove('show'); if (!params.get('bot')) $('intro').classList.add('show'); scene.say('1977', 'the first barrels'); w.log.unshift({ year: 1977, week: 0, text: 'July 21, 1977. 412,000 barrels of Saudi light go into West Hackberry. You have four domes, fifteen old brine caverns and about 180 million barrels of space. The pumps to get oil back out do not exist yet: build them.', cls: 'head' }); hud(); renderLog(); yearPanel(); }
  $('t-start').onclick = start;
  $('i-ok').onclick = () => $('intro').classList.remove('show');
  addEventListener('keydown', e => { if (e.code !== 'Space' || e.target.tagName === 'INPUT') return; e.preventDefault(); if ($('title').classList.contains('show')) return start(); if ($('intro').classList.contains('show')) return $('i-ok').click(); if ($('modal').classList.contains('show')) { const ok = $('m-ok') || $('m-again'); if (ok) ok.click(); return; } if (w.phase === 'crisis') week(); else if (!$('y-go').disabled) turnYear(); });
  const wait = ms => new Promise(r => setTimeout(r, ms));
  hud(); renderLog(); yearPanel();
  // idle camera drift under the title
  (function drift() { if (!$('title').classList.contains('show')) { scene.cam.tx = scene.focus == null ? 0.5 : scene.cam.tx; return; } scene.cam.tx = 0.5 + Math.sin(performance.now() / 6000) * 0.04; scene.cam.tz = 1.08; requestAnimationFrame(drift); })();
  const unDrift = () => { scene.cam.tx = 0.5; scene.cam.tz = 1; }; $('t-start').addEventListener('click', unDrift);

  /* ---------- test hooks: ?skip=1 skips the title; ?bot=YEAR plays sensibly to that year; ?bot=YEAR&stop=crisis stops inside the first crisis after it ---------- */
  if (params.get('skip') || params.get('bot')) { document.documentElement.style.setProperty('--t', '0s'); document.querySelectorAll('.overlay').forEach(o => o.style.transition = 'none'); start(); unDrift(); }
  if (params.get('receipt')) { setTimeout(() => { yo.value = Math.floor(+yo.max / 2); ym.value = 1; const d = w.domes.find(x => x.plant === 'none'); if (d) plan.pumps.add(d.key); const d2 = w.domes.find(x => x.maxCav - x.cav.length - x.building.length > 1); if (d2) plan.build[d2.key] = 2; turnYear(); }, 2500); }
  if (params.get('preview')) { setTimeout(() => { yo.value = params.get('preview') === 'sell' ? -20 : Math.floor(+yo.max / 2); ym.value = 1; const d = w.domes.find(x => x.plant === 'none'); if (d) plan.pumps.add(d.key); const d2 = w.domes.find(x => x.maxCav - x.cav.length - x.building.length > 2); if (d2) plan.build[d2.key] = 3; siteCards(); yearOut(); }, 2500); }
  if (params.get('bot')) {
    const target = +params.get('bot'); const stopAt = params.get('stop');
    (function botStep() {
      if (w.phase === 'end') return;
      if (w.year >= target && !(stopAt === 'crisis' && w.phase !== 'crisis')) { if (w.phase === 'crisis') { for (let i = 0; i < 3; i++) week(); } return; }
      if (w.phase === 'crisis') { if (stopAt === 'crisis' && w.year >= target) return; const r = S.crisisWeek(w, Math.min(1.0, S.drawCap(w))); if (r.over) { closeModal(); yearPanel(); } hud(); renderLog(); return setTimeout(botStep, 0); }
      const buy = Math.min(S.roomFor(w), Math.max(0, (w.budget - 0.2) * 1000 / w.price));
      S.yearDecisions(w, { buy, build: w.year < 1991 ? 4 : 0, maintain: 0.2, pumps: w.year >= 1982 && w.year <= 1985 ? 1 : 0 });
      const r = S.advanceYear(w); hud(); renderLog(); yearPanel();
      if (r.end) return endGame();
      if (r.card) { S.resolveCard(w, r.card, r.card.choices[0]); }
      if (r.crisis) { S.startCrisis(w, r.crisis); if (stopAt === 'crisis' && w.year >= target) { scene.say(r.crisis.name, 'emergency'); crisisPanel(); hud(); renderLog(); for (let i = 0; i < 2; i++) week(); if (r.crisis.hurricane) w.hurricane = w.hurricane || { weeks: 2, x: 0.3 }; return; } }
      setTimeout(botStep, 0);
    })();
  }
})();
