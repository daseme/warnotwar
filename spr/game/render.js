/* SALT — the scene. Canvas cross-section of the Gulf Coast: sea and tanker at left, four salt domes with their caverns,
   refineries at right. Oil and water move as particles. Weather comes in from the Gulf. */
'use strict';
(function (root) {
  const S = root.SALT;
  const lerp = (a, b, t) => a + (b - a) * t;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const C = {
    skyTop: '#0b1220', skyBot: '#243b53', sea: '#173a55', seaLight: '#2b5f80', land: '#2c2418', land2: '#3a3020', cap: '#4a4640', salt: '#8b8474', salt2: '#6e685a',
    oil: '#08070a', oil2: '#26211c', brine: '#4f86ad', brine2: '#3a6a8e', steel: '#9a958a', fire: '#e0894a', text: 'rgba(239,232,216,0.85)', dim: 'rgba(239,232,216,0.45)', bad: '#d06a5c', good: '#4ec9b0', gold: '#c9a94f', water: '#a9d3ef',
  };
  const SURF = 0.36;   // surface y as a fraction of scene height

  class Scene {
    constructor(canvas, world) {
      this.c = canvas; this.ctx = canvas.getContext('2d'); this.w = world;
      this.cam = { x: 0.5, y: 0.5, z: 1, tx: 0.5, ty: 0.5, tz: 1 };
      this.parts = []; this.clouds = Array.from({ length: 7 }, (_, i) => ({ x: Math.random(), y: 0.05 + Math.random() * 0.16, s: 0.05 + Math.random() * 0.08, v: 0.004 + Math.random() * 0.006 }));
      this.flash = null; this.flow = { out: 0, in: 0 }; this.hover = null; this.focus = null; this.t0 = performance.now();
      this.chain = null;   // in a crisis: { flows: {key: {pumps, pipe, take, flow, bind}}, cap, wells, held: {key: mb/d asked for that cannot get out} }
      this.tanker = 0.02; this.shown = new Map(); this.anim = null; this.preview = null;   // preview: { fill: Map, drain: Map, newCav: {key: n}, pumpDomes: Set }
      this.resize(); addEventListener('resize', () => this.resize());
      canvas.addEventListener('mousemove', e => this.onMove(e)); canvas.addEventListener('mouseleave', () => { this.hover = null; });
      canvas.addEventListener('click', e => this.onClick(e));
      requestAnimationFrame(t => this.frame(t));
    }
    resize() { const r = this.c.getBoundingClientRect(); const dpr = devicePixelRatio || 1; this.W = r.width; this.H = r.height; this.c.width = r.width * dpr; this.c.height = r.height * dpr; this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0); }
    /* scene → screen */
    sx(x) { return (x - this.cam.x) * this.cam.z * this.W + this.W / 2; }
    sy(y) { return (y - this.cam.y) * this.cam.z * this.H + this.H / 2; }
    ux(px) { return (px - this.W / 2) / (this.cam.z * this.W) + this.cam.x; }
    uy(py) { return (py - this.H / 2) / (this.cam.z * this.H) + this.cam.y; }
    zoomTo(i) { if (i == null || this.focus === i) { this.focus = null; this.cam.tx = 0.5; this.cam.ty = 0.5; this.cam.tz = 1; return; } this.focus = i; const d = this.w.domes[i]; this.cam.tx = d.x; this.cam.ty = 0.62; this.cam.tz = 2.4; }
    onMove(e) { const r = this.c.getBoundingClientRect(); const x = this.ux(e.clientX - r.left), y = this.uy(e.clientY - r.top); this.hover = null; this.mouse = { px: e.clientX - r.left, py: e.clientY - r.top }; this.w.domes.forEach((d, i) => { if (Math.abs(x - d.x) < 0.1 && y > SURF && y < 0.98) this.hover = i; }); this.c.style.cursor = this.hover != null ? 'pointer' : 'default'; }
    onClick() { if (this.hover != null) { this.zoomTo(this.hover); this.onFocus && this.onFocus(this.focus); } else if (this.focus != null) { this.zoomTo(null); this.onFocus && this.onFocus(null); } }
    say(text, sub) { this.flash = { text, sub, t: performance.now() }; }
    /* pour oil into caverns one after another; items = [{cv, from, to}] */
    animateFill(items, dur) { if (!items.length) return 0; this.anim = { items, t0: performance.now(), dur }; return dur; }
    animLevel(cv, t) {
      const a = this.anim; if (!a) return null;
      const i = a.items.findIndex(it => it.cv === cv); if (i < 0) return null;
      const n = a.items.length, p = clamp((t - a.t0) / a.dur, 0, 1) * n;
      const seg = clamp(p - i, 0, 1), it = a.items[i];
      return { level: it.from + (it.to - it.from) * seg, active: seg > 0 && seg < 1 };
    }
    /* cavern layout inside a dome: rows of capsules */
    layout(d) {
      const extra = this.preview && this.preview.newCav ? (this.preview.newCav[d.key] || 0) : 0;
      const n = d.cav.length + d.building.length + extra; const cols = Math.min(7, Math.max(3, Math.ceil(n / 3))); const rows = Math.max(1, Math.ceil(n / cols));
      const cw = 0.018, ch = 0.11, gap = 0.006; const totalW = cols * cw + (cols - 1) * gap;
      const top = SURF + 0.19; const items = [];
      for (let i = 0; i < n; i++) { const r = Math.floor(i / cols), c = i % cols; items.push({ x: d.x - totalW / 2 + c * (cw + gap), y: top + r * (ch + 0.02), w: cw, h: ch }); }
      return { items, cols, rows, top, bottom: top + rows * (ch + 0.02), halfW: totalW / 2 + 0.03 };
    }
    frame(t) {
      const dt = Math.min(50, t - (this.last || t)); this.last = t;
      const k = 1 - Math.pow(0.001, dt / 1000);
      this.cam.x = lerp(this.cam.x, this.cam.tx, k); this.cam.y = lerp(this.cam.y, this.cam.ty, k); this.cam.z = lerp(this.cam.z, this.cam.tz, k);
      this.draw(t, dt); requestAnimationFrame(tt => this.frame(tt));
    }
    draw(t, dt) {
      const { ctx, W, H, w } = this; ctx.clearRect(0, 0, W, H);
      const sx = x => this.sx(x), sy = y => this.sy(y), z = this.cam.z;
      const storm = w.hurricane ? 1 : 0;
      /* sky */
      const g = ctx.createLinearGradient(0, sy(0), 0, sy(SURF)); g.addColorStop(0, storm ? '#0a0d14' : C.skyTop); g.addColorStop(1, storm ? '#2a2f36' : C.skyBot); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      // stars
      ctx.fillStyle = 'rgba(255,255,255,0.35)'; for (let i = 0; i < 40; i++) { const x = (i * 97.3) % 1, y = ((i * 41.7) % 1) * 0.18; ctx.fillRect(sx(x), sy(y), 1, 1); }
      // clouds
      this.clouds.forEach(c => { c.x += c.v * dt / 1000 * (storm ? 4 : 1); if (c.x > 1.15) c.x = -0.15; ctx.fillStyle = storm ? 'rgba(90,95,105,0.6)' : 'rgba(255,255,255,0.08)'; const cx = sx(c.x), cy = sy(c.y), r = c.s * W * z; ctx.beginPath(); ctx.ellipse(cx, cy, r, r * 0.35, 0, 0, 7); ctx.fill(); });
      /* sea and land */
      const seaR = 0.10;
      ctx.fillStyle = C.land; ctx.fillRect(sx(seaR), sy(SURF), sx(1.2) - sx(seaR), sy(SURF + 0.10) - sy(SURF));
      const lg = ctx.createLinearGradient(0, sy(SURF + 0.10), 0, sy(SURF + 0.19)); lg.addColorStop(0, C.land2); lg.addColorStop(1, C.cap); ctx.fillStyle = lg; ctx.fillRect(sx(seaR), sy(SURF + 0.10), sx(1.2) - sx(seaR), sy(SURF + 0.19) - sy(SURF + 0.10));
      ctx.fillStyle = C.cap; ctx.fillRect(sx(-0.2), sy(SURF + 0.19), sx(1.2) - sx(-0.2), sy(1.2) - sy(SURF + 0.19));
      // sea
      const sg = ctx.createLinearGradient(0, sy(SURF), 0, sy(1)); sg.addColorStop(0, storm ? '#1c2e3d' : C.seaLight); sg.addColorStop(1, C.sea); ctx.fillStyle = sg; ctx.fillRect(sx(-0.2), sy(SURF), sx(seaR) - sx(-0.2), sy(1.2) - sy(SURF));
      ctx.strokeStyle = 'rgba(255,255,255,0.18)'; ctx.lineWidth = 1; for (let i = 0; i < 5; i++) { const y = SURF + 0.02 + i * 0.03; ctx.beginPath(); for (let x = -0.2; x <= seaR; x += 0.01) { const yy = y + Math.sin(x * 60 + t / 700 + i) * 0.003 * (1 + storm * 2); x === -0.2 ? ctx.moveTo(sx(x), sy(yy)) : ctx.lineTo(sx(x), sy(yy)); } ctx.stroke(); }
      // tanker
      const tk = this.tanker; ctx.fillStyle = '#1e1a16'; ctx.fillRect(sx(tk), sy(SURF - 0.012), 0.05 * W * z, 0.012 * H * z); ctx.fillStyle = '#c9c2b4'; ctx.fillRect(sx(tk + 0.036), sy(SURF - 0.028), 0.01 * W * z, 0.016 * H * z);
      /* salt domes */
      w.domes.forEach((d, i) => {
        const L = this.layout(d); const hw = Math.max(L.halfW, 0.075), top = SURF + 0.15;
        const dg = ctx.createLinearGradient(0, sy(top), 0, sy(1.2)); dg.addColorStop(0, C.salt); dg.addColorStop(1, C.salt2); ctx.fillStyle = dg;
        ctx.beginPath(); ctx.moveTo(sx(d.x - hw * 1.4), sy(1.25)); ctx.bezierCurveTo(sx(d.x - hw * 1.3), sy(top + 0.15), sx(d.x - hw * 0.9), sy(top), sx(d.x), sy(top)); ctx.bezierCurveTo(sx(d.x + hw * 0.9), sy(top), sx(d.x + hw * 1.3), sy(top + 0.15), sx(d.x + hw * 1.4), sy(1.25)); ctx.closePath(); ctx.fill();
        if (this.hover === i || this.focus === i) { ctx.strokeStyle = 'rgba(239,232,216,0.35)'; ctx.lineWidth = 1.5; ctx.stroke(); }
        if (this.preview && this.preview.pumpDomes && this.preview.pumpDomes.has(d.key)) { ctx.save(); ctx.shadowColor = 'rgba(255,217,160,0.9)'; ctx.shadowBlur = 22; ctx.strokeStyle = 'rgba(255,217,160,0.9)'; ctx.lineWidth = 2; ctx.setLineDash([6, 4]); ctx.stroke(); ctx.restore(); const lab = `PUMPS HERE · READY ${w.year + 2}`; ctx.font = `${10.5 * Math.min(z, 1.6)}px IBM Plex Mono, monospace`; ctx.textAlign = 'center'; const tw = ctx.measureText(lab).width; ctx.fillStyle = 'rgba(10,9,8,0.85)'; roundRect(ctx, sx(d.x) - tw / 2 - 8, sy(top + 0.05) - 12, tw + 16, 18, 4); ctx.fill(); ctx.fillStyle = 'rgba(255,217,160,0.95)'; ctx.fillText(lab, sx(d.x), sy(top + 0.05) + 1); }
        // flow lines in the salt
        ctx.strokeStyle = 'rgba(0,0,0,0.08)'; for (let k = 1; k < 6; k++) { const yy = top + k * 0.11; ctx.beginPath(); ctx.moveTo(sx(d.x - hw * 1.1), sy(yy + 0.01)); ctx.quadraticCurveTo(sx(d.x), sy(yy - 0.02), sx(d.x + hw * 1.1), sy(yy + 0.01)); ctx.stroke(); }
        // caverns
        L.items.forEach((it, k) => {
          const cv = d.cav[k]; const x = sx(it.x), y = sy(it.y), cw = it.w * W * z, ch = it.h * H * z, r = cw / 2;
          if (!cv && k >= d.cav.length + d.building.length) { // previewed: would be dug this year
            ctx.setLineDash([2, 4]); ctx.strokeStyle = 'rgba(255,217,160,0.8)'; ctx.lineWidth = 1.2; roundRect(ctx, x, y, cw, ch, r); ctx.stroke(); ctx.setLineDash([]);
            ctx.fillStyle = 'rgba(255,217,160,0.9)'; ctx.font = `${11 * Math.max(1, z / 2)}px IBM Plex Mono, monospace`; ctx.textAlign = 'center'; ctx.fillText('+', x + cw / 2, y + ch / 2 + 4); return;
          }
          if (!cv) { // under construction
            const left = d.building[k - d.cav.length]; ctx.setLineDash([3, 3]); ctx.strokeStyle = 'rgba(239,232,216,0.5)'; ctx.lineWidth = 1; roundRect(ctx, x, y, cw, ch, r); ctx.stroke(); ctx.setLineDash([]);
            const prog = 1 - left / 3; ctx.fillStyle = 'rgba(169,211,239,0.35)'; roundRect(ctx, x, y + ch * (1 - prog), cw, ch * prog, Math.min(r, ch * prog / 2)); ctx.fill();
            if (z > 1.8) { ctx.fillStyle = C.dim; ctx.font = `${9 * z / 2.4}px IBM Plex Mono, monospace`; ctx.textAlign = 'center'; ctx.fillText(`${left}y`, x + cw / 2, y - 4); }
            return;
          }
          // shown level eases toward the real one
          const key = cv; const shown = this.shown.get(key) ?? cv.oil; const al = this.animLevel(cv, t);
          const ns = al ? al.level : lerp(shown, cv.oil, 1 - Math.pow(0.02, dt / 1000)); this.shown.set(key, ns);
          if (al && al.active) { ctx.save(); ctx.shadowColor = 'rgba(224,137,74,0.9)'; ctx.shadowBlur = 18 * z; ctx.strokeStyle = 'rgba(224,137,74,0.9)'; ctx.lineWidth = 2; roundRect(ctx, x - 2, y - 2, cw + 4, ch + 4, r + 2); ctx.stroke(); ctx.restore(); }
          const f = clamp(ns / cv.cap, 0, 1);
          if (cv.retired) { ctx.fillStyle = 'rgba(70,66,60,0.9)'; roundRect(ctx, x, y, cw, ch, r); ctx.fill(); ctx.strokeStyle = 'rgba(239,232,216,0.25)'; ctx.beginPath(); for (let q = 0; q < ch; q += 6) { ctx.moveTo(x, y + q); ctx.lineTo(x + cw, y + q + 4); } ctx.stroke(); return; }
          ctx.fillStyle = C.brine; roundRect(ctx, x, y, cw, ch, r); ctx.fill();
          const og = ctx.createLinearGradient(0, y, 0, y + ch * f); og.addColorStop(0, C.oil2); og.addColorStop(1, C.oil); ctx.fillStyle = og; roundRect(ctx, x, y, cw, Math.max(0, ch * f), Math.min(r, ch * f / 2)); ctx.fill();
          // preview: translucent rise or drain to where this year's decisions would leave the cavern
          if (this.preview) {
            const nf = this.preview.fill && this.preview.fill.has(cv) ? clamp(this.preview.fill.get(cv) / cv.cap, 0, 1) : null;
            const df = this.preview.drain && this.preview.drain.has(cv) ? clamp(this.preview.drain.get(cv) / cv.cap, 0, 1) : null;
            if (nf != null && nf > f + 0.005) { ctx.fillStyle = 'rgba(255,217,160,0.45)'; roundRect(ctx, x, y + ch * f, cw, ch * (nf - f), 2); ctx.fill(); ctx.setLineDash([2, 2]); ctx.strokeStyle = 'rgba(255,217,160,0.95)'; ctx.beginPath(); ctx.moveTo(x, y + ch * nf); ctx.lineTo(x + cw, y + ch * nf); ctx.stroke(); ctx.setLineDash([]); }
            if (df != null && df < f - 0.005) { ctx.fillStyle = 'rgba(208,106,92,0.5)'; roundRect(ctx, x, y + ch * df, cw, ch * (f - df), 2); ctx.fill(); ctx.setLineDash([2, 2]); ctx.strokeStyle = 'rgba(208,106,92,0.95)'; ctx.beginPath(); ctx.moveTo(x, y + ch * df); ctx.lineTo(x + cw, y + ch * df); ctx.stroke(); ctx.setLineDash([]); }
          }
          if (f > 0.02 && f < 0.98) { ctx.strokeStyle = 'rgba(255,255,255,0.45)'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x + 1, y + ch * f + Math.sin(t / 400 + k) * 0.8); ctx.lineTo(x + cw - 1, y + ch * f + Math.sin(t / 400 + k + 2) * 0.8); ctx.stroke(); }
          ctx.lineWidth = 1; ctx.strokeStyle = cv.offline > 0 ? `rgba(208,106,92,${0.5 + 0.5 * Math.sin(t / 200)})` : cv.acquired ? 'rgba(201,169,79,0.6)' : 'rgba(239,232,216,0.28)'; roundRect(ctx, x, y, cw, ch, r); ctx.stroke();
          // well to surface
          ctx.strokeStyle = C.steel; ctx.lineWidth = Math.max(1, 1.2 * z / 2); ctx.beginPath(); ctx.moveTo(x + cw / 2, y); ctx.lineTo(x + cw / 2, sy(SURF)); ctx.stroke();
          if (z > 1.8) { ctx.fillStyle = C.dim; ctx.font = `${8 * z / 2.4}px IBM Plex Mono, monospace`; ctx.textAlign = 'center'; ctx.fillText(`${ns.toFixed(1)}`, x + cw / 2, y + ch + 10 * z / 2.4); ctx.fillText(`${Math.max(0, cv.left - cv.used).toFixed(1)}×`, x + cw / 2, y + ch + 19 * z / 2.4); }
        });
        // surface plant: pump house, tank, wellhead row
        ctx.fillStyle = '#5b544a'; ctx.fillRect(sx(d.x - 0.03), sy(SURF - 0.02), 0.02 * W * z, 0.02 * H * z);
        ctx.fillStyle = '#3b3630'; ctx.fillRect(sx(d.x + 0.012), sy(SURF - 0.028), 0.016 * W * z, 0.028 * H * z);
        ctx.fillStyle = d.plant === 'ready' ? C.good : typeof d.plant === 'number' ? C.gold : C.bad; ctx.beginPath(); ctx.arc(sx(d.x + 0.02), sy(SURF - 0.034), 2 * z, 0, 7); ctx.fill();
        // label
        ctx.fillStyle = C.text; ctx.font = `${11 * Math.min(z, 1.6)}px IBM Plex Mono, monospace`; ctx.textAlign = 'center'; ctx.fillText(d.name.toUpperCase(), sx(d.x), sy(SURF - 0.045));
        ctx.fillStyle = C.dim; ctx.font = `${10 * Math.min(z, 1.6)}px IBM Plex Mono, monospace`; ctx.fillText(`${S.domeOil(d).toFixed(0)} / ${S.domeCap(d).toFixed(0)} mb${d.plant === 'none' ? ' · no pumps' : typeof d.plant === 'number' ? ` · pumps in ${d.plant}y` : ''}`, sx(d.x), sy(SURF - 0.045) + 13 * Math.min(z, 1.6));
      });
      /* pipeline along the surface to the refineries; raw water line from the sea */
      ctx.strokeStyle = '#6a635a'; ctx.lineWidth = Math.max(1.5, 2 * z / 1.5); ctx.beginPath(); ctx.moveTo(sx(0.08), sy(SURF - 0.006)); ctx.lineTo(sx(0.985), sy(SURF - 0.006)); ctx.stroke();
      // each dome's own line to the system: thin at half the design rate, full when the bigger line is in; red where it is the link that binds
      const ch = this.chain, pulse = 0.75 + 0.25 * Math.sin(t / 220);
      w.domes.forEach(d => {
        const f = ch && ch.flows[d.key], y = SURF - 0.006, x0 = d.x + 0.028, x1 = d.x + 0.075;
        const boundHere = f && f.bind === 'pipe' && f.pumps > f.flow * 1.05 + 0.02 && ch.held[d.key] > 0.02;
        ctx.strokeStyle = boundHere ? `rgba(224,96,80,${pulse})` : d.pipe >= 1 ? '#8a8378' : '#5a544a'; ctx.lineWidth = Math.max(1, (boundHere ? 5 : d.pipe >= 1 ? 4 : 2) * z / 1.5);
        if (boundHere) { ctx.save(); ctx.shadowColor = 'rgba(224,96,80,1)'; ctx.shadowBlur = 18 * z; }
        ctx.beginPath(); ctx.moveTo(sx(x0), sy(y)); ctx.lineTo(sx(x1), sy(y)); ctx.stroke(); if (boundHere) ctx.restore();
        if (d.pipeWork > 0) { ctx.setLineDash([3, 3]); ctx.strokeStyle = 'rgba(255,217,160,0.7)'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(sx(x0), sy(y - 0.012)); ctx.lineTo(sx(x1), sy(y - 0.012)); ctx.stroke(); ctx.setLineDash([]); }
      });
      // the shared stretch to the docks and the refiners; red when they are what holds the release back
      const takeBound = ch && w.domes.some(d => { const f = ch.flows[d.key]; return f.bind === 'takeaway' && f.pumps > f.flow * 1.05 + 0.02 && ch.held[d.key] > 0.02; });
      if (takeBound) { ctx.save(); ctx.shadowColor = 'rgba(224,96,80,1)'; ctx.shadowBlur = 20 * z; ctx.strokeStyle = `rgba(224,96,80,${pulse})`; ctx.lineWidth = Math.max(3, 6 * z / 1.5); ctx.beginPath(); ctx.moveTo(sx(0.855), sy(SURF - 0.006)); ctx.lineTo(sx(0.985), sy(SURF - 0.006)); ctx.stroke(); ctx.restore(); }
      // docks: a pier and a ship at the far right, one mark per system that has any dock at all
      const nDocks = Object.keys(S.SYSTEMS).filter(k => S.takeawayOf(w, k) - S.SYSTEMS[k].refiners * (w.hurricane ? 0.5 : 1) > 0.01).length;
      ctx.fillStyle = '#4a4238'; ctx.fillRect(sx(0.965), sy(SURF - 0.012), 0.03 * W * z, 0.006 * H * z);
      for (let k = 0; k < 3; k++) { ctx.fillStyle = k < nDocks ? '#c9c2b4' : 'rgba(201,194,180,0.2)'; ctx.fillRect(sx(0.968 + k * 0.009), sy(SURF - 0.03), 0.005 * W * z, 0.018 * H * z); }
      ctx.fillStyle = C.dim; ctx.font = `${10 * Math.min(z, 1.6)}px IBM Plex Mono, monospace`; ctx.textAlign = 'center'; ctx.fillText(`DOCKS ${nDocks}/3`, sx(0.982), sy(SURF - 0.045));
      // refineries
      for (let k = 0; k < 4; k++) { const x = 0.895 + k * 0.018; ctx.fillStyle = '#4a4238'; ctx.fillRect(sx(x), sy(SURF - 0.05 - k * 0.012), 0.008 * W * z, (0.05 + k * 0.012) * H * z); ctx.fillStyle = 'rgba(224,137,74,0.8)'; ctx.beginPath(); ctx.arc(sx(x + 0.004), sy(SURF - 0.052 - k * 0.012) - Math.abs(Math.sin(t / 150 + k)) * 3, 2.5 * z, 0, 7); ctx.fill(); }
      ctx.fillStyle = C.dim; ctx.font = `${10 * Math.min(z, 1.6)}px IBM Plex Mono, monospace`; ctx.textAlign = 'center'; ctx.fillText('REFINERIES', sx(0.922), sy(SURF - 0.095)); ctx.fillText('GULF OF MEXICO', sx(0.05), sy(SURF + 0.06));
      if (this.anim && t - this.anim.t0 > this.anim.dur + 200) this.anim = null;
      /* particles */
      this.spawn(dt); this.parts = this.parts.filter(p => p.life > 0);
      this.parts.forEach(p => { p.life -= dt / 1000; if (p.stopX != null && p.x >= p.stopX) { if (!p.stopped) { p.stopped = true; p.col = '#d06a5c'; p.y += (Math.random() - 0.5) * 0.02; p.life = Math.min(p.life, 2.4); } p.vx = 0; p.vy = 0; } p.x += p.vx * dt / 1000; p.y += p.vy * dt / 1000; ctx.fillStyle = p.col; ctx.globalAlpha = clamp(p.life, 0, 1); ctx.beginPath(); ctx.arc(sx(p.x), sy(p.y), p.r * z, 0, 7); ctx.fill(); }); ctx.globalAlpha = 1;
      /* hurricane */
      if (w.hurricane) { w.hurricane.x = (w.hurricane.x ?? -0.1) + dt / 1000 * 0.03; const hx = sx(w.hurricane.x), hy = sy(0.12), R = 0.09 * W * z; ctx.strokeStyle = 'rgba(200,210,220,0.55)'; ctx.lineWidth = 2; for (let a = 0; a < 3; a++) { ctx.beginPath(); for (let q = 0; q < 40; q++) { const ang = q / 8 + t / 900 + a * 2.1, rr = R * (0.15 + q / 40 * 0.85); q ? ctx.lineTo(hx + Math.cos(ang) * rr, hy + Math.sin(ang) * rr * 0.6) : ctx.moveTo(hx + Math.cos(ang) * rr, hy + Math.sin(ang) * rr * 0.6); } ctx.stroke(); }
        ctx.strokeStyle = 'rgba(169,211,239,0.35)'; ctx.lineWidth = 1; for (let i = 0; i < 60; i++) { const x = ((i * 0.137 + t / 3000) % 1.2) - 0.1, y = ((i * 0.071 + t / 700) % 0.34); ctx.beginPath(); ctx.moveTo(sx(x), sy(y)); ctx.lineTo(sx(x - 0.004), sy(y + 0.02)); ctx.stroke(); } }
      /* hover */
      if (this.hover != null && this.mouse) { const d = w.domes[this.hover]; const lines = [d.name, `${S.domeOil(d).toFixed(1)} of ${S.domeCap(d).toFixed(0)} mb`, `${d.cav.filter(c => !c.retired).length} caverns${d.building.length ? `, ${d.building.length} being leached` : ''}`, d.plant === 'ready' ? `wells can flow ${Math.round(S.domeRate(w, d) * 1000)} kb/d` : typeof d.plant === 'number' ? `pumps ready in ${d.plant} year${d.plant > 1 ? 's' : ''}` : 'no pumps: oil cannot come out', this.focus === this.hover ? 'click to zoom out' : 'click to zoom in']; ctx.font = '11px IBM Plex Mono, monospace'; const bw = Math.max(...lines.map(l => ctx.measureText(l).width)) + 20, bh = lines.length * 16 + 12; const bx = clamp(this.mouse.px + 14, 0, W - bw), by = clamp(this.mouse.py - bh - 8, 0, H - bh); ctx.fillStyle = 'rgba(23,20,15,0.92)'; roundRect(ctx, bx, by, bw, bh, 6); ctx.fill(); ctx.strokeStyle = 'rgba(239,232,216,0.2)'; ctx.stroke(); ctx.textAlign = 'left'; lines.forEach((l, i) => { ctx.fillStyle = i ? C.dim : C.text; ctx.fillText(l, bx + 10, by + 18 + i * 16); }); }
      /* flash */
      if (this.flash) { const age = (t - this.flash.t) / 1000; if (age > 4.2) this.flash = null; else { const a = age < 0.5 ? age * 2 : age > 3.4 ? (4.2 - age) / 0.8 : 1; ctx.globalAlpha = a; ctx.fillStyle = 'rgba(10,9,8,0.55)'; ctx.fillRect(0, H * 0.38, W, H * 0.24); ctx.fillStyle = '#efe8d8'; ctx.textAlign = 'center'; ctx.font = `500 ${Math.min(44, W / 18)}px Newsreader, Georgia, serif`; ctx.fillText(this.flash.text, W / 2, H * 0.5); if (this.flash.sub) { ctx.font = '12px IBM Plex Mono, monospace'; ctx.fillStyle = C.gold; ctx.fillText(this.flash.sub.toUpperCase(), W / 2, H * 0.5 + 26); } ctx.globalAlpha = 1; } }
    }
    /* particle spawning follows this.flow: out = mb/d leaving, in = mb/d arriving */
    spawn(dt) {
      const w = this.w, n = this.parts.length; if (n > 700) return;
      const outRate = this.flow.out, inRate = this.flow.in;
      const ch = this.chain;
      w.domes.forEach(d => {
        if (d.plant !== 'ready' && outRate > 0) return;
        const share = ch && ch.cap > 1e-9 ? ch.flows[d.key].flow / ch.cap : S.domeRate(w, d) / Math.max(1e-9, S.drawCap(w));
        // barrels the knob asked for that this dome cannot get out: they run to the link that binds and pile up there
        const held = ch ? ch.held[d.key] : 0;
        if (held > 0.02 && Math.random() < dt / 1000 * 50 * held) { const f = ch.flows[d.key]; const stopX = f.bind === 'pipe' ? d.x + 0.072 : 0.86 + Math.random() * 0.02; this.parts.push({ x: d.x, y: SURF - 0.006, vx: (0.9 - d.x) / 1.8, vy: 0, life: 1.8, r: 1.4, col: '#c9c2b4', stopX }); }
        if (outRate > 0 && Math.random() < dt / 1000 * 60 * outRate * share) {
          // water from the sea to the dome, down; oil up and along the pipeline to the right
          this.parts.push({ x: 0.09, y: SURF - 0.006, vx: (d.x - 0.09) / 1.6, vy: 0, life: 1.6, r: 1.2, col: C.water });
          this.parts.push({ x: d.x, y: SURF - 0.006, vx: 0, vy: 0.5 / 1.2, life: 1.2, r: 1.2, col: C.water });
          this.parts.push({ x: d.x + 0.004, y: SURF + 0.25, vx: 0, vy: -0.25 / 0.9, life: 0.9, r: 1.3, col: '#c9c2b4' });
          this.parts.push({ x: d.x, y: SURF - 0.006, vx: (0.9 - d.x) / 1.8, vy: 0, life: 1.8, r: 1.3, col: '#c9c2b4' });
        }
        const filling = this.anim && this.anim.items.some(it => d.cav.includes(it.cv) && this.animLevel(it.cv, performance.now())?.active);
        if (inRate > 0 && (filling || !this.anim) && Math.random() < dt / 1000 * 40 * inRate / 0.8) {
          this.parts.push({ x: 0.05, y: SURF - 0.006, vx: (d.x - 0.05) / 1.6, vy: 0, life: 1.6, r: 1.3, col: '#c9c2b4' });
          this.parts.push({ x: d.x, y: SURF, vx: 0, vy: 0.25 / 1.0, life: 1.0, r: 1.3, col: '#c9c2b4' });
          this.parts.push({ x: d.x + 0.006, y: SURF + 0.3, vx: 0, vy: -0.3 / 1.1, life: 1.1, r: 1.1, col: C.brine });
        }
      });
    }
  }
  function roundRect(ctx, x, y, w, h, r) { r = Math.min(r, w / 2, h / 2); ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
  root.SALTScene = Scene;
})(window);
