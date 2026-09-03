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
  const gFuel = new I.Gauge($('g-fuel'), { min: 0, max: 1, ticks: 4, minor: 2, label: 'reserve', labels: ['E', '¼', '½', '¾', 'F'], zones: [{ from: 0, to: 0.25, color: '#c0392b' }] });
  const gFlow = new I.Gauge($('g-flow'), { min: 0, max: 5, ticks: 5, minor: 4, label: 'wells · mb/day', zones: [{ from: 4.4, to: 5, color: '#c0392b' }, { from: 0, to: 1, color: '#7a6a2a' }] });
  const gMood = new I.Gauge($('g-mood'), { min: 0, max: 100, ticks: 4, minor: 5, label: 'congress', zones: [{ from: 0, to: 30, color: '#c0392b' }, { from: 70, to: 100, color: '#2e8b6e' }] });
  const oInv = new I.Counter($('o-inv'), { digits: 3 }), oCap = new I.Counter($('o-cap'), { digits: 3 }), oBudget = new I.Counter($('o-budget'), { digits: 2, decimals: 2, prefix: '$' }), oTreas = new I.Counter($('o-treasury'), { digits: 3, decimals: 1, prefix: '$' }), oYear = new I.Counter($('o-year'), { digits: 4 });
  const lStorm = new I.Lamp($('l-storm'), { color: 'amber', label: 'storm' }), lWell = new I.Lamp($('l-well'), { color: 'red', label: 'well fail' }), lPumps = new I.Lamp($('l-pumps'), { color: 'green', label: 'pumps' }), lEmerg = new I.Lamp($('l-emerg'), { color: 'red', label: 'emergency' });
  let lastWellFail = -99;

  /* ---------- HUD ---------- */
  function hud() {
    oYear.set(w.year); $('h-phase').textContent = w.phase === 'crisis' ? w.crisis.name : 'the year';
    gPrice.set(w.price, `$${f0(w.price)}`);
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
  const yb = $('y-buy'), ybd = $('y-build'), ym = $('y-maint'), yp = $('y-pumps');
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
    const noPlant = w.domes.filter(d => d.plant === 'none').length; yp.max = noPlant; if (pumps > noPlant) yp.value = noPlant;
    const wells = w.domes.flatMap(d => d.cav).filter(c => !c.retired).length, n = Math.round(wells * share);
    const cBuy = buy * w.price / 1000, cBuild = build * S.BUILD_COST, cM = n * S.WORKOVER, cP = +yp.value * S.PLANT_COST;
    $('y-pumps-o').innerHTML = noPlant ? `${+yp.value} · <small>ready ${w.year + S.PLANT_YEARS}</small> · ${bn(cP)}` : 'every dome has pumps';
    $('y-buy-o').innerHTML = `${f0(buy)} mb · ${bn(cBuy)}`; $('y-build-o').innerHTML = `${build} · <small>ready ${w.year + 3}</small> · ${bn(cBuild)}`; $('y-maint-o').innerHTML = `${n} wells · ${bn(cM)}`;
    const left = w.budget - cBuy - cBuild - cM - cP; const L = $('y-left'); L.textContent = bn(Math.abs(left)) + (left < 0 ? ' short' : ''); L.style.color = left < -1e-9 ? 'var(--danger)' : 'var(--ink)';
    $('y-go').disabled = left < -1e-9;
  }
  [yb, ybd, ym, yp].forEach(el => el.addEventListener('input', yearOut));

  async function turnYear() {
    $('y-go').disabled = true;
    const dec = { buy: +yb.value, build: +ybd.value, maintain: +ym.value / 100, pumps: +yp.value };
    const before = new Map(w.domes.flatMap(d => d.cav).map(c => [c, c.oil]));
    const out = S.yearDecisions(w, dec);
    const poured = w.domes.flatMap(d => d.cav).filter(c => c.oil - (before.get(c) ?? c.oil) > 0.05).map(c => ({ cv: c, from: before.get(c), to: c.oil }));
    if (poured.length) { const dur = Math.min(4000, 700 + poured.length * 550); scene.flow.in = Math.min(0.8, out.bought / 100); scene.animateFill(poured, dur); $('y-brief').textContent = `Pouring ${f1(out.bought)} million barrels into ${poured.length} cavern${poured.length > 1 ? 's' : ''}…`; await wait(dur + 150); scene.flow.in = 0; }
    out.notes.forEach(n => w.log.unshift({ year: w.year, week: 0, text: n, cls: 'bad' }));
    if (out.bought > 0.05) w.log.unshift({ year: w.year, week: 0, text: `Bought ${f1(out.bought)} mb at $${f0(w.price)} for ${bn(out.bought * w.price / 1000)}${out.built ? `; started ${out.built} cavern${out.built > 1 ? 's' : ''}` : ''}${out.maintained ? `; worked over ${out.maintained} wells` : ''}.` });
    else if (out.built || out.maintained) w.log.unshift({ year: w.year, week: 0, text: `${out.built ? `Started ${out.built} cavern${out.built > 1 ? 's' : ''}` : ''}${out.built && out.maintained ? '; ' : ''}${out.maintained ? `worked over ${out.maintained} wells` : ''}.` });
    if (out.plants) w.log.unshift({ year: w.year, week: 0, text: `Began building pumps at ${out.plantAt.join(' and ')}. Ready in ${S.PLANT_YEARS} years.`, cls: 'good' });
    const r = S.advanceYear(w);
    scene.say(String(w.year), r.crisis ? r.crisis.name : r.card ? r.card.name : '');
    yb.value = 0; ybd.value = 0; ym.value = 0; yp.value = 0;
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
    modal(`<div class="kicker">${w.year} · emergency</div><h2>${s.name}</h2><p>${s.text}</p><p class="mono" style="font-size:12px;color:var(--ink-60)">World short about ${f1(s.shortfall)} mb/d. ${s.iea ? `Allies cover their part; your share is about ${f1(s.shortfall * 0.44)} mb/d.` : `Most of this lands on you: about ${f1(s.shortfall * 0.7)} mb/d.`} Your wells can flow ${f1(S.drawCap(w))} mb/d${S.drawCap(w) <= 0 ? ' — nothing. No dome has a pumping plant.' : ''}. You hold ${f0(S.inv(w))} mb.</p><div class="foot"><button class="btn primary" id="m-ok">take the desk →</button></div>`);
    $('m-ok').onclick = () => { closeModal(); S.startCrisis(w, s); scene.say(s.name, 'emergency'); crisisPanel(); hud(); renderLog(); };
  }
  const cr = $('c-rate');
  const knob = new I.Knob($('k-rate'), cr, { label: 'release · mb/day', detents: 22, fmt: v => v.toFixed(2) });
  const tgRun = new I.Toggle($('tg-run'), { label: 'clock', off: 'hold', on: 'run', onchange: on => { if (on) { if (!autorun) autorun = setInterval(week, 700); } else stopRun(); } });
  function crisisPanel() {
    $('p-year').hidden = true; $('p-crisis').hidden = false;
    const c = w.crisis, cap = S.drawCap(w);
    $('c-name').textContent = c.name; $('c-week').textContent = `week ${c.week + 1}`;
    $('c-short').innerHTML = `${f1(c.ceasefire > 0 ? 0 : c.shortfall)}<small>mb/d</small>`; $('c-share').innerHTML = `${f1((c.ceasefire > 0 ? 0 : c.shortfall) * (c.allies ? 0.44 : 0.7))}<small>mb/d</small>`; $('c-cap').innerHTML = `${f1(cap)}<small>mb/d</small>`;
    cr.max = Math.max(0.05, cap).toFixed(2); if (+cr.value > cap) cr.value = cap.toFixed(2); knob.refresh();
    $('c-note').textContent = cap <= 0 ? 'no pumps: you can only watch' : c.week === 0 ? 'first barrels reach the market in about two weeks' : `${f0(S.inv(w))} mb left · crude $${f0(w.price)}`;
  }
  function week() {
    if (w.phase !== 'crisis') return;
    const r = S.crisisWeek(w, +cr.value);
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
