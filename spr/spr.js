/* the reserve — engine
   cavern sim (canvas), cross-section, history chart, capability curve, floor gauge, wear diagram, schedule chart */
'use strict';

/* ---------- theme (shared with the rest of the site) ---------- */
const rootEl = document.documentElement;
const themeBtn = document.getElementById('theme-toggle');
function applyTheme(t) { rootEl.dataset.theme = t; themeBtn.textContent = t === 'paper' ? '◑ ink' : '◐ paper'; }
applyTheme((() => { try { const s = localStorage.getItem('ww-theme'); if (s) return s; } catch (e) {} return matchMedia('(prefers-color-scheme: dark)').matches ? 'ink' : 'paper'; })());
themeBtn.onclick = () => { const t = rootEl.dataset.theme === 'paper' ? 'ink' : 'paper'; applyTheme(t); try { localStorage.setItem('ww-theme', t); } catch (e) {} };

const css = name => getComputedStyle(rootEl).getPropertyValue(name).trim();
const fmt1 = n => (Math.round(n * 10) / 10).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const fmt0 = n => Math.round(n).toLocaleString('en-US');
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const monthName = d => new Date(d + 'T00:00:00Z').toLocaleDateString('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' });
const shortDate = d => new Date(d + 'T00:00:00Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });

/* ---------- constants (every figure is sourced in the page's notes) ---------- */
const SPR = {
  designCapacity: 713.5,      // million barrels, DOE Long-Term Strategic Review 2016, Table 1
  maxDrawdown: 4.415,         // million barrels per day, design
  designFill: 0.785,          // million barrels per day, design fill (225 kb/d per site, 110 at Bayou Choctaw)
  effectiveDrawdown: 2.7,     // GAO-26-106918, December 2025 (Big Hill offline for construction)
  effectiveFill: 0.44,
  roofOil: 12,                // million barrels kept on cavern roofs system-wide, LTSR 2016
  sites: [
    { key: 'bm', name: 'Bryan Mound',    where: 'Freeport, Texas',          caverns: 19, capacity: 247.1, draw: 1.500, fill: 0.225, now: 142.5, system: 'Seaway',  avail: 1 },
    { key: 'bh', name: 'Big Hill',       where: 'Winnie, Texas',            caverns: 14, capacity: 170.0, draw: 1.100, fill: 0.225, now: 89.1,  system: 'Texoma',  avail: 0 },
    { key: 'wh', name: 'West Hackberry', where: 'near Lake Charles, Louisiana', caverns: 21, capacity: 220.4, draw: 1.300, fill: 0.225, now: 30.5, system: 'Texoma', avail: 1 },
    { key: 'bc', name: 'Bayou Choctaw',  where: 'near Baton Rouge, Louisiana', caverns: 6, capacity: 76.0,  draw: 0.515, fill: 0.110, now: 32.0,  system: 'Capline', avail: 1 },
  ],
  siteDate: 'Aug 20, 2026',   // DOE Quick Facts date for the per-site inventories above
};
const HEEL = 0.02;            // roof oil + brine allowance per cavern, about 1 % each (Sandia)

/* ---------- capability model ----------
   Each cavern flows through its own well at roughly (site design rate ÷ caverns). Oil is held cavern by cavern,
   so as inventory falls, fewer caverns hold oil and fewer wells can run. Rate = Σ site rate × (caverns with oil ÷ caverns) × availability. */
function drawCapability(inventoryMb, allAvailable = true) {
  let total = 0;
  SPR.sites.forEach(s => {
    const share = s.capacity / SPR.designCapacity;
    const inv = inventoryMb * share, cavCap = s.capacity / s.caverns;
    const withOil = Math.min(s.caverns, Math.ceil(Math.max(0, inv - s.caverns * cavCap * HEEL) / cavCap - 1e-9));
    total += s.draw * (withOil / s.caverns) * (allAvailable ? 1 : s.avail);
  });
  return total;
}
function capabilityToday() {
  // uses DOE's actual per-site inventories, not a proportional split
  let total = 0;
  SPR.sites.forEach(s => { const cavCap = s.capacity / s.caverns; const withOil = Math.min(s.caverns, Math.ceil(Math.max(0, s.now - s.caverns * cavCap * HEEL) / cavCap - 1e-9)); total += s.draw * (withOil / s.caverns) * s.avail; });
  return total;
}

/* =====================================================================
   CAVERN SIM — one cavern, cross-section, oil on brine, two pipe strings
   ===================================================================== */
class Cavern {
  constructor(canvas, opts = {}) {
    this.c = canvas; this.ctx = canvas.getContext('2d');
    this.capacity = opts.capacity || 10;            // million barrels
    this.oil = opts.oil ?? this.capacity * 0.8;
    this.heel = this.capacity * HEEL;               // roof oil that never comes out
    this.mode = 'idle';                             // idle | draw | fill | empty | full
    this.rate = opts.rate || 0.08;                  // million barrels per sim-day (a single well runs ~60–90 kb/d)
    this.dayLength = opts.dayLength || 700;         // ms per sim-day
    this.day = 0; this.water = 0; this.salt = 0; this.brineOut = 0; this.leach = 0; this.drawdowns = 0; this.lastMode = 'idle';
    this.t0 = performance.now(); this.last = this.t0;
    this.onchange = opts.onchange || (() => {});
    this.resize(); addEventListener('resize', () => this.resize());
    requestAnimationFrame(t => this.frame(t));
  }
  resize() {
    const r = this.c.getBoundingClientRect(); const dpr = devicePixelRatio || 1;
    this.w = r.width; this.h = Math.max(300, r.width * 0.78); this.c.height = this.h * dpr; this.c.width = r.width * dpr;
    this.c.style.height = this.h + 'px'; this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  set(mode) { this.mode = mode; }
  step(dt) {
    const days = dt / this.dayLength;
    if (this.mode === 'draw') {
      const avail = Math.max(0, this.oil - this.heel);
      const take = Math.min(avail, this.rate * days);
      this.oil -= take; this.water += take;
      this.salt += take * 0.15; this.leach += (take * 0.15) / this.capacity;   // Sandia: 15 % of injected water's volume in salt
      this.drawdowns = this.leach / 0.15;                                      // a 15 % growth = one drawdown spent
      if (avail <= 1e-9) this.mode = 'empty';
    } else if (this.mode === 'fill') {
      const room = Math.max(0, this.capacity * (1 + this.leach) - this.oil);
      const put = Math.min(room, this.rate * 0.4 * days);                     // fill runs slower: brine disposal limits it
      this.oil += put; this.brineOut += put; if (room <= 1e-9) this.mode = 'full';
    }
    if (this.mode === 'draw' || this.mode === 'fill') this.day += days;
    this.onchange(this);
  }
  frame(t) {
    const dt = Math.min(50, t - this.last); this.last = t;
    this.step(dt); this.draw(t); requestAnimationFrame(tt => this.frame(tt));
  }
  geo() {
    const w = this.w, h = this.h;
    return { w, h, ground: h * 0.17, top: h * 0.38, bot: h * 0.965, cx: w * 0.5, cw: w * 0.13, capY: h * 0.30 };
  }
  draw(t) {
    const { ctx } = this; const g = this.geo(); const { w, h } = g; const mono = css('--mono');
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = css('--sky'); ctx.fillRect(0, 0, w, g.ground);
    const soil = ctx.createLinearGradient(0, g.ground, 0, g.capY); soil.addColorStop(0, css('--soil')); soil.addColorStop(1, css('--soil-2'));
    ctx.fillStyle = soil; ctx.fillRect(0, g.ground, w, g.capY - g.ground);
    const capH = h * 0.03;
    ctx.fillStyle = css('--caprock'); ctx.fillRect(0, g.capY, w, capH);
    const salt = ctx.createLinearGradient(0, g.capY + capH, 0, h); salt.addColorStop(0, css('--salt')); salt.addColorStop(1, css('--salt-2'));
    ctx.fillStyle = salt; ctx.fillRect(0, g.capY + capH, w, h - g.capY);
    ctx.strokeStyle = css('--ink-06'); ctx.lineWidth = 1;
    for (let i = 0; i < 10; i++) { const y = g.capY + capH + 8 + i * (h - g.capY - capH) / 10; ctx.beginPath(); ctx.moveTo(0, y); ctx.bezierCurveTo(w * 0.3, y - 7, w * 0.6, y + 7, w, y); ctx.stroke(); }

    // cavern outline; the leach growth is drawn exaggerated four times so it can be seen
    const cw = g.cw * (1 + this.leach * 4);
    const path = () => {
      ctx.beginPath(); ctx.moveTo(g.cx - cw * 0.5, g.top);
      ctx.bezierCurveTo(g.cx - cw * 0.95, g.top + 6, g.cx - cw, g.top + 30, g.cx - cw, g.top + 50);
      ctx.lineTo(g.cx - cw * 0.96, g.bot - 26); ctx.quadraticCurveTo(g.cx - cw * 0.9, g.bot, g.cx - cw * 0.5, g.bot);
      ctx.lineTo(g.cx + cw * 0.5, g.bot); ctx.quadraticCurveTo(g.cx + cw * 0.9, g.bot, g.cx + cw * 0.96, g.bot - 26);
      ctx.lineTo(g.cx + cw, g.top + 50); ctx.bezierCurveTo(g.cx + cw, g.top + 30, g.cx + cw * 0.95, g.top + 6, g.cx + cw * 0.5, g.top); ctx.closePath();
    };
    const cap = this.capacity * (1 + this.leach);
    const frac = clamp(this.oil / cap, 0, 1);
    const iy = g.top + (g.bot - g.top) * (1 - frac);           // oil–brine interface
    ctx.save(); path(); ctx.clip();
    ctx.fillStyle = css('--brine'); ctx.fillRect(g.cx - cw - 2, g.top, cw * 2 + 4, g.bot - g.top);
    ctx.fillStyle = css('--brine-2'); ctx.globalAlpha = 0.35;
    for (let i = 0; i < 7; i++) { const y = iy + 10 + i * (g.bot - iy) / 7; ctx.fillRect(g.cx - cw, y + Math.sin(t / 900 + i) * 2, cw * 2, 1.2); }
    ctx.globalAlpha = 1;
    const oilG = ctx.createLinearGradient(0, g.top, 0, Math.max(iy, g.top + 1)); oilG.addColorStop(0, css('--oil-2')); oilG.addColorStop(1, css('--oil'));
    ctx.fillStyle = oilG; ctx.fillRect(g.cx - cw - 2, g.top, cw * 2 + 4, Math.max(0, iy - g.top));
    // sump of insolubles at the bottom
    ctx.fillStyle = css('--caprock'); ctx.globalAlpha = 0.6; ctx.fillRect(g.cx - cw, g.bot - 10, cw * 2, 10); ctx.globalAlpha = 1;
    ctx.strokeStyle = 'rgba(255,255,255,0.4)'; ctx.lineWidth = 1.2; ctx.beginPath();
    const active = this.mode === 'draw' || this.mode === 'fill';
    for (let x = g.cx - cw; x <= g.cx + cw; x += 4) { const y = iy + Math.sin(x / 14 + t / 500) * (active ? 1.6 : 0.6); x === g.cx - cw ? ctx.moveTo(x, y) : ctx.lineTo(x, y); }
    ctx.stroke(); ctx.restore();
    ctx.strokeStyle = css('--ink-30'); ctx.lineWidth = 1.5; path(); ctx.stroke();

    // the well: cemented casing to the roof, hanging string to the sump
    const pw = Math.max(5, w * 0.012);
    ctx.fillStyle = css('--steel'); ctx.fillRect(g.cx - pw, g.ground - 6, pw * 2, g.top - g.ground + 8);
    ctx.fillStyle = css('--bg-raise'); ctx.fillRect(g.cx - pw * 0.42, g.ground - 6, pw * 0.84, g.top - g.ground + 8);
    ctx.fillStyle = css('--steel'); ctx.fillRect(g.cx - pw * 0.5, g.top, pw, g.bot - 22 - g.top);
    ctx.fillRect(g.cx - pw * 2.4, g.ground - 14, pw * 4.8, 8); ctx.fillRect(g.cx - pw * 1.2, g.ground - 26, pw * 2.4, 12);
    ctx.strokeStyle = css('--steel'); ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(w * 0.10, g.ground - 20); ctx.lineTo(g.cx - pw * 2.4, g.ground - 20); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(g.cx + pw * 2.4, g.ground - 20); ctx.lineTo(w * 0.90, g.ground - 20); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(w * 0.70, g.ground - 20); ctx.lineTo(w * 0.70, g.ground - 8); ctx.stroke();
    // surface: raw water intake (left), brine pond (right of well), oil tank and pipeline (far right)
    ctx.fillStyle = css('--water'); ctx.fillRect(w * 0.02, g.ground - 12, w * 0.10, 12);
    ctx.fillStyle = css('--brine-2'); ctx.globalAlpha = 0.7; ctx.fillRect(w * 0.64, g.ground - 8, w * 0.12, 8); ctx.globalAlpha = 1;
    ctx.fillStyle = css('--oil'); ctx.fillRect(w * 0.86, g.ground - 30, w * 0.08, 30);
    ctx.fillStyle = css('--ink-60'); ctx.font = `9.5px ${mono}`; ctx.textAlign = 'center';
    ctx.fillText('raw water', w * 0.07, g.ground - 30); ctx.fillText('brine pond', w * 0.70, g.ground - 32); ctx.fillText('oil · to pipeline', w * 0.90, g.ground - 36);
    this.flow(t, g, pw, cw);
    ctx.fillStyle = css('--ink-60'); ctx.font = `10.5px ${mono}`; ctx.textAlign = 'left';
    ctx.fillText('surface', w * 0.14, g.ground + 12); ctx.fillText('caprock', 6, g.capY + 11); ctx.fillText('salt', 6, g.capY + capH + 14);
    ctx.textAlign = 'right'; ctx.fillStyle = css('--ink-80');
    if (iy - g.top > 26) ctx.fillText('oil', g.cx - cw - 8, (g.top + iy) / 2 + 4);
    if (g.bot - iy > 26) ctx.fillText('brine', g.cx - cw - 8, (iy + g.bot) / 2 + 4);
    ctx.textAlign = 'left'; ctx.fillStyle = css('--ink-45'); ctx.font = `9px ${mono}`;
    ctx.fillText('roof ≈ 2,500 ft down', g.cx + cw + 10, g.top + 4); ctx.fillText('floor ≈ 4,500 ft down', g.cx + cw + 10, g.bot - 2);
    ctx.fillText('≈ 200 ft across', g.cx + cw + 10, (g.top + g.bot) / 2);
    ctx.fillText('hanging string', g.cx + pw + 6, g.top + 60); ctx.fillText('casing', g.cx + pw + 6, (g.ground + g.top) / 2);
  }
  flow(t, g, pw, cw) {
    const { ctx } = this; if (!(this.mode === 'draw' || this.mode === 'fill')) return;
    const n = 14, speed = 0.00035 * (this.rate / 0.08); const W = this.w;
    const dot = (x, y, col) => { ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y, 1.7, 0, 7); ctx.fill(); };
    const water = css('--water'), oil = css('--oil-2');
    for (let i = 0; i < n; i++) {
      const ph = ((t * speed) + i / n) % 1;
      if (this.mode === 'draw') {
        dot(W * 0.07 + ph * (g.cx - pw * 2.4 - W * 0.07), g.ground - 20, water);                     // water along the surface line
        dot(g.cx, g.ground - 20 + ph * (g.bot - 22 - (g.ground - 20)), water);                       // down the hanging string
        dot(g.cx + pw * 0.7, g.top - ph * (g.top - (g.ground - 20)), oil);                           // oil up the annulus
        dot(g.cx + pw * 2.4 + ph * (W * 0.86 - g.cx - pw * 2.4), g.ground - 20, oil);                // out to the pipeline
        ctx.fillStyle = 'rgba(255,255,255,0.22)'; ctx.beginPath(); ctx.arc(g.cx, g.bot - 22, 4 + ph * 18, 0, 7); ctx.fill();
      } else {
        dot(W * 0.90 - ph * (W * 0.90 - g.cx - pw * 2.4), g.ground - 20, oil);                       // oil in from the pipeline
        dot(g.cx + pw * 0.7, g.ground - 20 + ph * (g.top - (g.ground - 20)), oil);                   // down the annulus onto the roof
        dot(g.cx, g.bot - 22 - ph * (g.bot - 22 - (g.ground - 20)), css('--brine'));                 // brine up the hanging string
        dot(g.cx + pw * 2.4 + ph * (W * 0.70 - g.cx - pw * 2.4), g.ground - 20, css('--brine'));     // to the pond
      }
    }
  }
}

/* ---------- SVG helpers ---------- */
const svgNS = 'http://www.w3.org/2000/svg';
function el(tag, attrs = {}, parent) { const e = document.createElementNS(svgNS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function txt(parent, x, y, s, attrs = {}) { const t = el('text', Object.assign({ x, y }, attrs), parent); t.textContent = s; return t; }
function tipFor(host) { const tip = document.createElement('div'); tip.className = 'tip'; host.appendChild(tip); return tip; }
function placeTip(tip, host, e, html) { const b = host.getBoundingClientRect(); tip.innerHTML = html; tip.style.left = clamp(e.clientX - b.left + 14, 0, b.width - 220) + 'px'; tip.style.top = Math.max(0, e.clientY - b.top - 44) + 'px'; tip.classList.add('show'); }

/* =====================================================================
   CROSS-SECTION — true scale, feet. Three caverns, a tower for scale.
   ===================================================================== */
function crossSection(host) {
  host.innerHTML = '';
  const FT = 5000, SKY = 1900, WFT = 3400;          // depth shown, sky shown, width shown, all in feet
  const W = 640, s = W / WFT;                        // px per foot, same both ways
  const H = (FT + SKY) * s;
  const x = ft => 74 + ft * s, y = ft => 8 + (SKY + ft) * s;
  const svg = el('svg', { viewBox: `0 0 ${W + 90} ${H + 40}`, role: 'img', 'aria-label': 'Cross-section of a salt dome with storage caverns, to scale' }, host);
  const F = (size) => `font-family:var(--mono);font-size:${size}px`;
  el('rect', { x: x(0), y: y(-SKY), width: WFT * s, height: SKY * s, fill: 'var(--sky)' }, svg);
  el('rect', { x: x(0), y: y(0), width: WFT * s, height: 1500 * s, fill: 'var(--soil)' }, svg);
  el('rect', { x: x(0), y: y(1500), width: WFT * s, height: 400 * s, fill: 'var(--caprock)' }, svg);
  el('rect', { x: x(0), y: y(1900), width: WFT * s, height: (FT - 1900) * s, fill: 'var(--salt)' }, svg);
  for (let d = 2100; d < FT; d += 220) el('path', { d: `M${x(0)},${y(d)} C${x(900)},${y(d - 40)} ${x(1800)},${y(d + 40)} ${x(WFT)},${y(d)}`, fill: 'none', stroke: 'var(--ink-06)' }, svg);
  for (let d = 0; d <= 5000; d += 1000) { el('line', { x1: x(0) - 6, x2: x(0), y1: y(d), y2: y(d), stroke: 'var(--ink-45)' }, svg); txt(svg, x(0) - 10, y(d) + 4, d === 0 ? 'surface' : `${fmt0(d)} ft`, { style: F(12), fill: 'var(--ink-60)', 'text-anchor': 'end' }); }
  const cav = (cx, top, bot, wft, label, note, fill) => {
    const g = el('g', { class: 'cav' }, svg);
    const r = wft / 2 * s;
    el('path', { d: `M${x(cx) - r * 0.5},${y(top)} Q${x(cx) - r},${y(top)} ${x(cx) - r},${y(top) + r} L${x(cx) - r * 0.9},${y(bot) - r} Q${x(cx) - r * 0.9},${y(bot)} ${x(cx) - r * 0.4},${y(bot)} L${x(cx) + r * 0.4},${y(bot)} Q${x(cx) + r * 0.9},${y(bot)} ${x(cx) + r * 0.9},${y(bot) - r} L${x(cx) + r},${y(top) + r} Q${x(cx) + r},${y(top)} ${x(cx) + r * 0.5},${y(top)} Z`, fill, stroke: 'var(--ink-30)', 'stroke-width': 1 }, g);
    el('line', { x1: x(cx), x2: x(cx), y1: y(0) - 8, y2: y(top), stroke: 'var(--steel)', 'stroke-width': 2 }, g);
    el('rect', { x: x(cx) - 5, y: y(0) - 14, width: 10, height: 8, fill: 'var(--steel)' }, g);
    el('title', {}, g).textContent = `${label}: ${note}`;
    return g;
  };
  cav(1250, 2500, 4500, 200, 'A DOE-built cavern', 'about 200 feet across and 2,000 feet tall, roof 2,500 feet down. Holds about 10 million barrels.', 'var(--oil)');
  cav(2000, 2500, 4500, 200, 'Its neighbour', '750 feet away, centre to centre. About 550 feet of salt stands between them.', 'var(--oil)');
  const g3 = el('g', {}, svg);
  el('path', { d: `M${x(2700)},${y(3200)} c ${60 * s},${-40 * s} ${300 * s},${-30 * s} ${380 * s},${20 * s} c ${60 * s},${60 * s} ${20 * s},${180 * s} ${-40 * s},${220 * s} c ${-120 * s},${80 * s} ${-300 * s},${60 * s} ${-360 * s},${-20 * s} c ${-40 * s},${-60 * s} ${-60 * s},${-140 * s} ${20 * s},${-220 * s} z`, fill: 'var(--oil)', stroke: 'var(--ink-30)' }, g3);
  el('line', { x1: x(2900), x2: x(2900), y1: y(0) - 8, y2: y(3200), stroke: 'var(--steel)', 'stroke-width': 2 }, g3);
  el('rect', { x: x(2900) - 5, y: y(0) - 14, width: 10, height: 8, fill: 'var(--steel)' }, g3);
  el('title', {}, g3).textContent = 'An acquired cavern: leached for brine in the 1940s, before the reserve existed. Wide, shallow and irregular. Most of these can be drawn down only once more.';
  // Willis Tower, 1,451 ft to the roof, 1,729 ft to the antenna tips, about 225 ft wide at the base
  const tw = 225 * s, tx = x(430);
  const gT = el('g', {}, svg);
  el('rect', { x: tx - tw / 2, y: y(-1451), width: tw, height: 1451 * s, fill: 'var(--ink-30)' }, gT);
  el('rect', { x: tx - tw * 0.25, y: y(-1729), width: 1.5, height: 278 * s, fill: 'var(--ink-30)' }, gT);
  el('rect', { x: tx + tw * 0.15, y: y(-1729), width: 1.5, height: 278 * s, fill: 'var(--ink-30)' }, gT);
  el('title', {}, gT).textContent = 'Willis Tower, Chicago: 1,451 feet to the roof. Stand it in a cavern and 550 feet of oil would sit above it.';
  txt(svg, tx, y(-1729) - 10, 'Willis Tower · 1,451 ft', { style: F(12), fill: 'var(--ink-60)', 'text-anchor': 'middle' });
  // the same tower ghosted inside the first cavern
  el('rect', { x: x(1250) - tw / 2, y: y(4500) - 1451 * s, width: tw, height: 1451 * s, fill: 'none', stroke: 'var(--bg)', 'stroke-dasharray': '3 3', opacity: 0.8 }, svg);
  el('line', { x1: x(1250) - tw * 0.25, x2: x(1250) - tw * 0.25, y1: y(4500) - 1729 * s, y2: y(4500) - 1451 * s, stroke: 'var(--bg)', opacity: 0.8 }, svg);
  const lab = (fx, fy, t, size = 12, anchor = 'start', fill = 'var(--ink-60)') => txt(svg, x(fx), y(fy), t, { style: F(size), fill, 'text-anchor': anchor });
  lab(40, 750, 'sand, clay, gravel');
  lab(40, 1740, 'caprock · anhydrite, gypsum, limestone', 11);
  lab(40, 2150, 'salt · Louann · Jurassic · about 160 million years old', 11);
  lab(1250, 2380, 'DOE-built, 1980s', 11, 'middle');
  lab(2000, 2380, '750 ft apart', 11, 'middle');
  lab(2900, 3060, 'acquired, 1940s', 11, 'middle');
  el('line', { x1: x(1350), x2: x(1900), y1: y(3500), y2: y(3500), stroke: 'var(--ink-45)', 'stroke-dasharray': '2 3' }, svg);
  lab(1625, 3460, '550 ft of salt', 11, 'middle');
  lab(WFT - 20, FT - 40, 'to scale · depths are West Hackberry’s', 10.5, 'end', 'var(--ink-45)');
  const tip = tipFor(host);
  svg.querySelectorAll('g').forEach(g => { const t = g.querySelector('title'); if (!t) return; const text = t.textContent; t.remove(); g.style.cursor = 'help'; g.addEventListener('mousemove', e => placeTip(tip, host, e, text.replace(/^([^:]+): /, '<b>$1</b><br>').replace(/(.{58,}?)\s/g, '$1<br>'))); g.addEventListener('mouseleave', () => tip.classList.remove('show')); });
}

/* =====================================================================
   HISTORY CHART — one series, annotated events, crosshair tooltip
   ===================================================================== */
function historyChart(host, data, events) {
  const W = 960, H = 410, L = 50, R = 20, T = 40, B = 40;
  host.innerHTML = '';
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Strategic Petroleum Reserve inventory since 1977' }, host);
  const wk = data.weekly, mo = data.monthly.filter(r => r[0] < wk[0][0]);
  const pts = mo.concat(wk).map(r => ({ t: Date.parse(r[0] + 'T00:00:00Z'), v: r[1], d: r[0] }));
  const t0 = Date.UTC(1977, 0, 1), t1 = pts[pts.length - 1].t + 86400000 * 150;
  const yMax = 760;
  const x = t => L + (t - t0) / (t1 - t0) * (W - L - R);
  const y = v => H - B - v / yMax * (H - T - B);
  for (let v = 0; v <= 750; v += 250) { el('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: 'var(--ink-10)' }, svg); txt(svg, L - 8, y(v) + 3.5, v ? fmt0(v) : '0', { class: 'svg-small', 'text-anchor': 'end' }); }
  txt(svg, 4, T - 12, 'million barrels', { class: 'svg-small' });
  el('line', { x1: L, x2: W - R, y1: y(SPR.designCapacity), y2: y(SPR.designCapacity), stroke: 'var(--ink-30)', 'stroke-dasharray': '4 4' }, svg);
  txt(svg, L + 6, y(SPR.designCapacity) - 6, 'what it can hold · 714', { class: 'svg-small' });
  for (let yr = 1980; yr <= 2025; yr += 5) { const xx = x(Date.UTC(yr, 0, 1)); el('line', { x1: xx, x2: xx, y1: H - B, y2: H - B + 4, stroke: 'var(--ink-30)' }, svg); txt(svg, xx, H - B + 16, String(yr), { class: 'svg-small', 'text-anchor': 'middle' }); }
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join('');
  el('path', { d: d + `L${x(pts[pts.length - 1].t).toFixed(1)},${y(0)}L${x(pts[0].t).toFixed(1)},${y(0)}Z`, fill: 'var(--oil)', opacity: 0.08 }, svg);
  el('path', { d, fill: 'none', stroke: 'var(--ink)', 'stroke-width': 1.6, 'stroke-linejoin': 'round' }, svg);
  events.forEach(ev => {
    const tt = Date.parse(ev.date + 'T00:00:00Z');
    const near = pts.reduce((a, p) => Math.abs(p.t - tt) < Math.abs(a.t - tt) ? p : a, pts[0]);
    const xx = x(tt), yy = y(near.v), lift = ev.lift || 34;
    el('line', { x1: xx, x2: xx, y1: yy, y2: yy - lift, stroke: 'var(--gold)' }, svg);
    el('circle', { cx: xx, cy: yy, r: 3.5, fill: 'var(--gold)', stroke: 'var(--bg)', 'stroke-width': 2 }, svg);
    txt(svg, xx + (ev.anchor === 'end' ? -4 : 4), lift >= 0 ? yy - lift - 4 : yy - lift + 10, ev.label, { class: 'svg-label', 'text-anchor': ev.anchor || 'start' });
  });
  const lp = pts[pts.length - 1];
  el('circle', { cx: x(lp.t), cy: y(lp.v), r: 4, fill: 'var(--danger)', stroke: 'var(--bg)', 'stroke-width': 2 }, svg);
  txt(svg, x(lp.t) - 8, y(lp.v) + 44, `${fmt1(lp.v)} · ${shortDate(lp.d)}`, { class: 'svg-label strong', 'text-anchor': 'end' });
  const cross = el('line', { y1: T, y2: H - B, stroke: 'var(--ink-30)', opacity: 0 }, svg);
  const dot = el('circle', { r: 4, fill: 'var(--ink)', stroke: 'var(--bg)', 'stroke-width': 2, opacity: 0 }, svg);
  const tip = tipFor(host);
  const hit = el('rect', { x: L, y: T, width: W - L - R, height: H - T - B, fill: 'transparent' }, svg);
  hit.addEventListener('mousemove', e => {
    const b = svg.getBoundingClientRect(); const mx = (e.clientX - b.left) / b.width * W;
    const tt = t0 + (mx - L) / (W - L - R) * (t1 - t0);
    let lo = 0, hi = pts.length - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; pts[m].t < tt ? lo = m : hi = m; }
    const p = Math.abs(pts[lo].t - tt) < Math.abs(pts[hi].t - tt) ? pts[lo] : pts[hi];
    cross.setAttribute('x1', x(p.t)); cross.setAttribute('x2', x(p.t)); cross.setAttribute('opacity', 1);
    dot.setAttribute('cx', x(p.t)); dot.setAttribute('cy', y(p.v)); dot.setAttribute('opacity', 1);
    placeTip(tip, host, e, `<b>${fmt1(p.v)}</b> million barrels<br>${shortDate(p.d)}`);
  });
  hit.addEventListener('mouseleave', () => { cross.setAttribute('opacity', 0); dot.setAttribute('opacity', 0); tip.classList.remove('show'); });
}

/* =====================================================================
   CAPABILITY CURVE — how fast the reserve can flow, by how much it holds
   ===================================================================== */
function capabilityChart(host, todayMb) {
  const W = 520, H = 300, L = 40, R = 16, T = 26, B = 40;
  host.innerHTML = '';
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Modelled maximum drawdown rate by inventory level' }, host);
  const x = mb => L + mb / SPR.designCapacity * (W - L - R);
  const y = r => H - B - r / 5 * (H - T - B);
  for (let r = 0; r <= 5; r++) { el('line', { x1: L, x2: W - R, y1: y(r), y2: y(r), stroke: 'var(--ink-10)' }, svg); txt(svg, L - 6, y(r) + 3, String(r), { class: 'svg-small', 'text-anchor': 'end' }); }
  txt(svg, L - 6, T - 8, 'mb/day', { class: 'svg-small', 'text-anchor': 'end' });
  for (let mb = 0; mb <= 700; mb += 100) txt(svg, x(mb), H - B + 14, String(mb), { class: 'svg-small', 'text-anchor': 'middle' });
  txt(svg, (L + W - R) / 2, H - 6, 'million barrels in the reserve', { class: 'svg-small', 'text-anchor': 'middle' });
  let d = '', d2 = '';
  for (let mb = 0; mb <= SPR.designCapacity; mb += 2) { d += `${mb ? 'L' : 'M'}${x(mb).toFixed(1)},${y(drawCapability(mb, true)).toFixed(1)}`; d2 += `${mb ? 'L' : 'M'}${x(mb).toFixed(1)},${y(drawCapability(mb, false)).toFixed(1)}`; }
  el('path', { d: d2, fill: 'none', stroke: 'var(--rate)', 'stroke-width': 1.5, 'stroke-dasharray': '4 3' }, svg);
  el('path', { d, fill: 'none', stroke: 'var(--rate)', 'stroke-width': 2 }, svg);
  txt(svg, x(700), y(4.415) - 9, 'all four sites · 4.4 design', { class: 'svg-label', 'text-anchor': 'end' });
  txt(svg, x(700), y(3.315) + 16, 'Big Hill offline · 3.3', { class: 'svg-label', 'text-anchor': 'end' });
  // GAO's measured point, Dec 2025
  el('circle', { cx: x(413), cy: y(2.7), r: 4.5, fill: 'var(--gold)', stroke: 'var(--bg)', 'stroke-width': 2 }, svg);
  txt(svg, x(413) + 10, y(2.7) + 26, 'GAO measured · 2.7 at 413', { class: 'svg-label' });
  const r = capabilityToday();
  el('line', { x1: x(todayMb), x2: x(todayMb), y1: y(r), y2: H - B, stroke: 'var(--danger)', 'stroke-dasharray': '3 3' }, svg);
  el('circle', { cx: x(todayMb), cy: y(r), r: 4.5, fill: 'var(--danger)', stroke: 'var(--bg)', 'stroke-width': 2 }, svg);
  txt(svg, x(todayMb) - 8, y(r) - 10, `today · about ${fmt1(r)}`, { class: 'svg-label strong', 'text-anchor': 'end' });
  return r;
}

/* =====================================================================
   FLOOR GAUGE — vertical, the lines people have drawn
   ===================================================================== */
function floorGauge(host, todayMb, marks) {
  const W = 560, H = 470, L = 215, T = 22, B = 22, barW = 60;
  host.innerHTML = '';
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Inventory against the floors people have named' }, host);
  const y = mb => H - B - mb / 730 * (H - T - B);
  el('rect', { x: L, y: y(713.5), width: barW, height: y(0) - y(713.5), rx: 6, fill: 'var(--brine)', opacity: 0.5 }, svg);
  el('rect', { x: L, y: y(todayMb), width: barW, height: y(0) - y(todayMb), rx: 6, fill: 'var(--oil)' }, svg);
  el('rect', { x: L, y: y(713.5), width: barW, height: y(0) - y(713.5), rx: 6, fill: 'none', stroke: 'var(--ink-30)' }, svg);
  marks.forEach(m => {
    const right = (m.side || 'right') === 'right', yy = y(m.mb), col = m.color || 'var(--ink-60)';
    el('line', { x1: right ? L + barW : L - 8, x2: right ? L + barW + 8 : L, y1: yy, y2: yy, stroke: col, 'stroke-width': 1.2 }, svg);
    el('line', { x1: L, x2: L + barW, y1: yy, y2: yy, stroke: col, 'stroke-dasharray': '2 3', opacity: 0.8 }, svg);
    const t = txt(svg, right ? L + barW + 12 : L - 12, yy + 3.5, m.label, { class: m.strong ? 'svg-label strong' : 'svg-label', 'text-anchor': right ? 'start' : 'end' });
    if (m.strong) t.setAttribute('fill', col);
  });
}

/* =====================================================================
   WEAR — one cavern growing 15 % per drawdown, five times, next to its neighbour
   ===================================================================== */
function wearDiagram(host) {
  host.innerHTML = '';
  const W = 520, H = 300, k = 0.38;                  // px per foot
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Cavern growth over five drawdowns, plan view' }, host);
  el('rect', { x: 0, y: 0, width: W, height: H, fill: 'var(--salt)' }, svg);
  const cy = 150, cx = 120, cx2 = cx + 750 * k, r0 = 100 * k;
  const rN = n => r0 * Math.pow(1.15, n / 2);          // +15 % volume per drawdown → radius × √1.15
  for (let i = 5; i >= 1; i--) el('circle', { cx, cy, r: rN(i), fill: 'none', stroke: 'var(--ink-45)', 'stroke-dasharray': '3 3' }, svg);
  el('circle', { cx, cy, r: r0, fill: 'var(--oil)', stroke: 'var(--ink-30)' }, svg);
  el('circle', { cx: cx2, cy, r: r0, fill: 'var(--oil)', stroke: 'var(--ink-30)' }, svg);
  for (let i = 1; i <= 5; i++) txt(svg, cx, cy - rN(i) + 9, String(i), { class: 'svg-small', 'text-anchor': 'middle', fill: 'var(--ink-60)' });
  el('line', { x1: cx + r0, x2: cx2 - r0, y1: cy + 60, y2: cy + 60, stroke: 'var(--ink-45)' }, svg);
  txt(svg, (cx + cx2) / 2, cy + 74, 'new: 550 ft of salt', { class: 'svg-small', 'text-anchor': 'middle' });
  el('line', { x1: cx + rN(5), x2: cx2 - r0, y1: cy, y2: cy, stroke: 'var(--danger)', 'stroke-width': 1.5 }, svg);
  txt(svg, (cx + rN(5) + cx2 - r0) / 2, cy - 8, `after five: ${fmt0(750 - 100 * Math.pow(1.15, 2.5) - 100)} ft`, { class: 'svg-small', 'text-anchor': 'middle', fill: 'var(--danger)' });
  txt(svg, cx, cy + r0 * 1.15 * 1.15 + 34, 'drawdowns spent, 1 to 5', { class: 'svg-small', 'text-anchor': 'middle' });
  txt(svg, cx2, cy + r0 + 30, 'neighbour, 750 ft away', { class: 'svg-small', 'text-anchor': 'middle' });
  txt(svg, W - 8, 16, 'plan view · to scale', { class: 'svg-small', 'text-anchor': 'end' });
  txt(svg, 8, 16, 'salt', { class: 'svg-small' });
}

/* =====================================================================
   SCHEDULE — DOE's own decline curve from a 695 mb reserve, against what 2022 and 2026 actually ran
   ===================================================================== */
function scheduleChart(host) {
  const W = 520, H = 260, L = 40, R = 16, T = 26, B = 40;
  host.innerHTML = '';
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Design drawdown schedule against actual 2022 and 2026 rates' }, host);
  const x = d => L + d / 180 * (W - L - R), y = r => H - B - r / 5 * (H - T - B);
  for (let r = 0; r <= 5; r++) { el('line', { x1: L, x2: W - R, y1: y(r), y2: y(r), stroke: 'var(--ink-10)' }, svg); txt(svg, L - 6, y(r) + 3, String(r), { class: 'svg-small', 'text-anchor': 'end' }); }
  txt(svg, L - 6, T - 8, 'mb/day', { class: 'svg-small', 'text-anchor': 'end' });
  for (let d = 0; d <= 180; d += 30) txt(svg, x(d), H - B + 14, String(d), { class: 'svg-small', 'text-anchor': 'middle' });
  txt(svg, (L + W - R) / 2, H - 6, 'days after the order', { class: 'svg-small', 'text-anchor': 'middle' });
  // design: 4.4 to day 90, 3.8 to 120, 3.4 to 150, 1.9 to 180 (LTSR 2016 Figure 15), ramp over first 15 days
  const steps = [[0, 0], [15, 4.415], [90, 4.415], [90, 3.8], [120, 3.8], [120, 3.4], [150, 3.4], [150, 1.9], [180, 1.9]];
  el('path', { d: steps.map((p, i) => `${i ? 'L' : 'M'}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join(''), fill: 'none', stroke: 'var(--rate)', 'stroke-width': 2 }, svg);
  txt(svg, x(50), y(4.415) - 8, 'design, from a full reserve', { class: 'svg-label', 'text-anchor': 'middle' });
  // actual
  el('line', { x1: x(0), x2: x(180), y1: y(1.0), y2: y(1.0), stroke: 'var(--gold)', 'stroke-width': 2 }, svg);
  txt(svg, x(178), y(1.0) - 8, '2022 · 1.0 for 180 days', { class: 'svg-label', 'text-anchor': 'end' });
  el('line', { x1: x(0), x2: x(161), y1: y(0.8), y2: y(0.8), stroke: 'var(--danger)', 'stroke-width': 2 }, svg);
  txt(svg, x(160), y(0.8) + 15, '2026 · 0.8 average, 1.4 peak week', { class: 'svg-label', 'text-anchor': 'end' });
  el('circle', { cx: x(65), cy: y(1.42), r: 3.5, fill: 'var(--danger)', stroke: 'var(--bg)', 'stroke-width': 2 }, svg);
}

/* =====================================================================
   SITE STRIP — four sites as columns of caverns, filled from DOE's per-site inventory
   ===================================================================== */
function siteStrip(host) {
  host.innerHTML = '';
  SPR.sites.forEach(s => {
    const card = document.createElement('div'); card.className = 'site';
    card.innerHTML = `<h3>${s.name}</h3><div class="where">${s.where} · ${s.system}</div>`;
    const cols = Math.min(s.caverns, 11), rows = Math.ceil(s.caverns / cols);
    const W = 220, cw = W / cols, ch = 46, H = rows * (ch + 8) + 4;
    const svg = el('svg', { viewBox: `0 0 ${W} ${H}` }, card);
    const cavCap = s.capacity / s.caverns; let inv = s.now;
    for (let i = 0; i < s.caverns; i++) {
      const cx = (i % cols) * cw + cw / 2, top = 4 + Math.floor(i / cols) * (ch + 8), w = cw * 0.52;
      const put = clamp(inv, 0, cavCap); inv -= put; const f = put / cavCap, oh = ch * f;
      el('rect', { x: cx - w / 2, y: top, width: w, height: ch, rx: w / 2, fill: 'var(--brine)', opacity: s.avail ? 0.55 : 0.3 }, svg);
      el('rect', { x: cx - w / 2, y: top, width: w, height: Math.max(0, oh), rx: Math.min(w / 2, oh / 2), fill: 'var(--oil)', opacity: s.avail ? 1 : 0.55 }, svg);
      el('rect', { x: cx - w / 2, y: top, width: w, height: ch, rx: w / 2, fill: 'none', stroke: 'var(--ink-30)' }, svg);
    }
    const dl = document.createElement('dl');
    dl.innerHTML = `<dt>caverns</dt><dd>${s.caverns}</dd><dt>holds</dt><dd>${fmt1(s.capacity)} mb</dd><dt>in it</dt><dd>${fmt1(s.now)} mb · ${fmt0(100 * s.now / s.capacity)}%</dd><dt>design flow</dt><dd>${fmt0(s.draw * 1000)} kb/d</dd><dt>status</dt><dd>${s.avail ? 'operating' : 'construction outage'}</dd>`;
    card.appendChild(dl); host.appendChild(card);
  });
}

window.SPRengine = { Cavern, crossSection, historyChart, capabilityChart, floorGauge, wearDiagram, scheduleChart, siteStrip, drawCapability, capabilityToday, SPR, HEEL, fmt0, fmt1, clamp, monthName, shortDate, el, txt, css };
