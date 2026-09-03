/* SALT — the interface */
'use strict';
(function () {
  const S = window.SALT; const $ = id => document.getElementById(id);
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

  /* ---------- year panel ---------- */
  const yb = $('y-buy'), ybd = $('y-build'), ym = $('y-maint'), yp = $('y-pumps'), ys = $('y-sell');
  function yearPanel() {
    $('p-year').hidden = false; $('p-crisis').hidden = true;
    const room = S.roomFor(w), maxBuy = Math.min(room, S.fillCap(w) * 365);
    yb.max = Math.max(0, Math.floor(maxBuy)); yb.value = Math.min(+yb.value, +yb.max);
    $('y-budget').textContent = bn(Math.max(0, w.budget));
    const era = w.domes.every(d => d.plant === 'none') ? 'No dome has pumps. Nothing you hold can come out until you build them.' : w.year < 1986 ? 'Congress is generous while the embargo is fresh. Build.' : w.year < 1992 ? 'Money is tightening. Finish the domes and fill them.' : w.year < 2000 ? 'The nineties: no money, cheap oil, and Congress eyeing your barrels.' : w.year < 2015 ? 'Oil from federal leases trickles in. Keep the wells alive.' : w.year < 2023 ? 'Congress sells your oil to pay for other things. Hold what you can.' : 'Refill years. Every barrel you buy now is one you can pump later.';
    let realNote = '';
    if (real) { const row = real.monthly.find(r => r[0].startsWith(`${w.year}-01`)) || real.weekly.find(r => r[0].startsWith(`${w.year}-01`)); if (row) realNote = ` The real reserve held ${f0(row[1])} mb at the start of ${w.year}; you hold ${f0(S.inv(w))}.`; }
    $('y-brief').textContent = era + realNote;
    yearOut();
  }
  function yearOut() {
    const buy = +yb.value, build = +ybd.value, share = +ym.value / 100, pumps = +yp.value;
    const sellMax = Math.floor(S.maxSell(w)); ys.max = sellMax; if (+ys.value > sellMax) ys.value = sellMax; const sell = +ys.value, cashIn = sell * w.price / 1000;
    const noPlant = w.domes.filter(d => d.plant === 'none').length; yp.max = noPlant; if (pumps > noPlant) yp.value = noPlant;
    const wells = w.domes.flatMap(d => d.cav).filter(c => !c.retired).length, n = Math.round(wells * share);
    const cBuy = buy * w.price / 1000, cBuild = build * S.BUILD_COST, cM = n * S.WORKOVER, cP = +yp.value * S.PLANT_COST;
    $('y-pumps-o').innerHTML = noPlant ? `${+yp.value} · ${bn(cP)}` : '—';
    $('y-buy-o').innerHTML = `${f0(buy)} mb · ${bn(cBuy)}`; $('y-build-o').innerHTML = `${build} · ${bn(cBuild)}`; $('y-maint-o').innerHTML = `${n} wells · ${bn(cM)}`;
    // spec line under every lever: cost · time · limit
    const p = w.price, m$ = v => `$${Math.round(v * 1000)}m`, fillKbd = Math.round(S.fillCap(w) * 1000), sep = '<i>·</i>';
    const maxBuy = +yb.max, roomAll = S.roomFor(w);
    const months = buy > 0 ? Math.max(1, Math.round(buy / (S.fillCap(w) * 30.4))) : 0;
    $('y-spec-buy').innerHTML = `<b>$${f0(p)}/bbl</b>${sep}pours in at ${fillKbd} kb/d${sep}${buy > 0 ? `yours arrive in <b>${months} mo</b>` : `max <b>${f0(maxBuy)} mb</b> this year`}${roomAll < maxBuy + 1 ? `${sep}<span class="warn">room is the limit</span>` : ''}`;
    const open = w.domes.reduce((a, d) => a + (d.maxCav - d.cav.length - d.building.length), 0), leaching = w.domes.reduce((a, d) => a + d.building.length, 0);
    $('y-spec-build').innerHTML = `<b>${m$(S.BUILD_COST)} each</b>${sep}3 yr, ready <b>${w.year + S.BUILD_YEARS}</b>${sep}10.5 mb each${sep}${open} slots left${leaching ? `${sep}<span class="good">${leaching} leaching</span>` : ''}`;
    $('y-spec-pumps').innerHTML = noPlant ? `<b>${m$(S.PLANT_COST)}/dome</b>${sep}2 yr, ready <b>${w.year + S.PLANT_YEARS}</b>${sep}<span class="bad">${noPlant} dome${noPlant > 1 ? 's' : ''} without pumps</span>` : `<span class="good">every dome has pumps</span>`;
    const shut = w.domes.reduce((a, d) => a + d.cav.filter(c => c.offline > 0 && !c.retired).length, 0);
    $('y-spec-maint').innerHTML = `<b>${m$(S.WORKOVER)}/well</b>${sep}done this year${sep}${wells} wells${shut ? `${sep}<span class="bad">${shut} cavern${shut > 1 ? 's' : ''} shut, repairs reopen</span>` : ''}`;
    $('y-sell-o').innerHTML = `${f0(sell)} mb · +${bn(cashIn)}`;
    const ab = S.avgBuy(w);
    $('y-spec-sell').innerHTML = sellMax > 0 ? `<b>$${f0(p)}/bbl</b>${sep}cash this year${sep}max <b>${sellMax} mb</b>${ab ? `${sep}your cost $${f0(ab)} → <span class="${p >= ab ? 'good' : 'bad'}">${p >= ab ? 'gain' : 'loss'} $${f0(Math.abs(p - ab))}/bbl</span>` : ''}` : `<span class="warn">needs pumps and oil above the roof blanket</span>`;
    const nextGrant = S.budgetFor(w.year + 1) * (0.8 + w.mood / 250);
    const leftover = w.budget + cashIn - cBuy - cBuild - cM - cP;
    $('y-money').innerHTML = `Money: unspent cash carries over, but Congress cuts next year’s grant by half of it. Next year’s grant looks like about <b>${bn(nextGrant)}</b>${leftover > 0.05 ? `; carrying ${bn(leftover)} would make it about <b>${bn(Math.max(0, nextGrant - leftover * 0.5) + leftover)}</b> in hand` : ''}.`;
    const left = leftover; const L = $('y-left'); L.textContent = bn(Math.abs(left)) + (left < 0 ? ' short' : ''); L.style.color = left < -1e-9 ? 'var(--danger)' : 'var(--ink)';
    $('y-go').disabled = left < -1e-9;
    $('y-budget').textContent = bn(Math.max(0, w.budget)) + (cashIn > 0.005 ? ` + ${bn(cashIn)} from the sale` : '');
  }
  [yb, ybd, ym, yp, ys].forEach(el => el.addEventListener('input', yearOut));

  async function turnYear() {
    $('y-go').disabled = true;
    const dec = { buy: +yb.value, build: +ybd.value, maintain: +ym.value / 100, pumps: +yp.value, sell: +ys.value };
    const before = new Map(w.domes.flatMap(d => d.cav).map(c => [c, c.oil]));
    const out = S.yearDecisions(w, dec);
    const poured = w.domes.flatMap(d => d.cav).filter(c => c.oil - (before.get(c) ?? c.oil) > 0.05).map(c => ({ cv: c, from: before.get(c), to: c.oil }));
    if (poured.length) { const dur = Math.min(4000, 700 + poured.length * 550); scene.flow.in = Math.min(0.8, out.bought / 100); scene.animateFill(poured, dur); $('y-brief').textContent = `Pouring ${f1(out.bought)} million barrels into ${poured.length} cavern${poured.length > 1 ? 's' : ''}…`; await wait(dur + 150); scene.flow.in = 0; }
    out.notes.forEach(n => w.log.unshift({ year: w.year, week: 0, text: n, cls: 'bad' }));
    if (out.sold > 0.05) { const as = S.avgSell(w), ab = S.avgBuy(w); w.log.unshift({ year: w.year, week: 0, text: `Sold ${f1(out.sold)} mb at $${f0(w.price)}: ${bn(out.saleCash)} into your account${ab ? ` (your oil cost $${f0(ab)} a barrel on average)` : ''}.`, cls: 'good' }); }
    if (out.bought > 0.05 && w.soldCash > 0 && w.price < S.avgSell(w)) w.log.unshift({ year: w.year, week: 0, text: `Buying back at $${f0(w.price)} what you sold at an average of $${f0(S.avgSell(w))}: the buy-low, sell-high argument both administrations made.`, cls: 'good' });
    if (out.bought > 0.05) w.log.unshift({ year: w.year, week: 0, text: `Bought ${f1(out.bought)} mb at $${f0(w.price)} for ${bn(out.bought * w.price / 1000)}${out.built ? `; started ${out.built} cavern${out.built > 1 ? 's' : ''}` : ''}${out.maintained ? `; repaired ${out.maintained} wells` : ''}.` });
    else if (out.built || out.maintained) w.log.unshift({ year: w.year, week: 0, text: `${out.built ? `Started ${out.built} cavern${out.built > 1 ? 's' : ''}` : ''}${out.built && out.maintained ? '; ' : ''}${out.maintained ? `repaired ${out.maintained} wells` : ''}.` });
    if (out.plants) w.log.unshift({ year: w.year, week: 0, text: `Began building pumps at ${out.plantAt.join(' and ')}. Ready in ${S.PLANT_YEARS} years.`, cls: 'good' });
    const r = S.advanceYear(w);
    scene.say(String(w.year), r.crisis ? r.crisis.name : r.card ? r.card.name : '');
    yb.value = 0; ybd.value = 0; ym.value = 0; yp.value = 0; ys.value = 0;
    hud(); renderLog(); yearPanel();
    if (r.end) return endGame();
    if (r.card) return showCard(r.card);
    if (r.crisis) return crisisIntro(r.crisis);
    $('y-go').disabled = false;
  }
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
    $('m-ok').onclick = () => { closeModal(); S.startCrisis(w, s); lastWeek = null; scene.say(s.name, 'emergency'); crisisPanel(); hud(); renderLog(); };
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
      : `<b>Knob:</b> how much to release each day, up to the ${f1(cap)} mb/day your wells can flow. <b>Next week</b> runs one week; the <b>clock</b> keeps running them. The world is short ${f1(c.ceasefire > 0 ? 0 : c.shortfall)} mb/day and your share to cover is ${f1((c.ceasefire > 0 ? 0 : c.shortfall) * (c.allies ? 0.44 : 0.7))}; release that much and the price spike mostly goes away. Release less and Americans pay more; release more and you run dry sooner.`;
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
