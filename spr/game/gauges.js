/* SALT — instruments. Analog dials, odometer counters, jewel lamps, a rotary knob, a toggle. No dependencies. */
'use strict';
(function (root) {
  const NS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const polar = (cx, cy, r, deg) => { const a = (deg - 90) * Math.PI / 180; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
  const arcPath = (cx, cy, r, a0, a1) => { const [x0, y0] = polar(cx, cy, r, a0), [x1, y1] = polar(cx, cy, r, a1); return `M${x0.toFixed(2)},${y0.toFixed(2)} A${r},${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1.toFixed(2)},${y1.toFixed(2)}`; };

  /* ---- round dial: sweep 270°, from -135° to +135° ---- */
  class Gauge {
    constructor(host, o) {
      this.o = Object.assign({ min: 0, max: 100, label: '', units: '', ticks: 5, minor: 4, zones: [], labels: null, size: 104, fmt: v => String(Math.round(v)) }, o);
      this.v = this.o.min; this.shown = this.o.min; this.vel = 0;
      const s = this.o.size, c = s / 2, R = c - 3;
      const svg = el('svg', { viewBox: `0 0 ${s} ${s}`, class: 'dial' }, host);
      const defs = el('defs', {}, svg);
      const g = el('radialGradient', { id: `bz${Gauge.n++}`, cx: '35%', cy: '30%' }, defs); el('stop', { offset: '0', 'stop-color': '#f3f1ea' }, g); el('stop', { offset: '0.45', 'stop-color': '#9a978f' }, g); el('stop', { offset: '0.7', 'stop-color': '#5a5852' }, g); el('stop', { offset: '1', 'stop-color': '#c9c6bd' }, g);
      el('circle', { cx: c, cy: c, r: R, fill: `url(#${g.id})` }, svg);                    // chrome bezel
      el('circle', { cx: c, cy: c, r: R - 5, fill: '#15130f' }, svg);                       // face
      el('circle', { cx: c, cy: c, r: R - 6, fill: 'none', stroke: 'rgba(255,255,255,0.06)' }, svg);
      const rT = R - 12;
      // zones
      this.o.zones.forEach(z => el('path', { d: arcPath(c, c, rT - 3, this.ang(z.from), this.ang(z.to)), fill: 'none', stroke: z.color, 'stroke-width': 4, opacity: 0.85 }, svg));
      // ticks
      const N = this.o.ticks;
      for (let i = 0; i <= N; i++) {
        const a = -135 + 270 * i / N; const [x0, y0] = polar(c, c, rT, a), [x1, y1] = polar(c, c, rT - 7, a);
        el('line', { x1: x0, y1: y0, x2: x1, y2: y1, stroke: '#e9e2d0', 'stroke-width': 1.6 }, svg);
        const lab = this.o.labels ? this.o.labels[i] : this.o.fmt(this.o.min + (this.o.max - this.o.min) * i / N);
        const [tx, ty] = polar(c, c, rT - 15, a); const t = el('text', { x: tx, y: ty + 2.5, 'text-anchor': 'middle', fill: '#e9e2d0', 'font-size': 7.5, 'font-family': 'IBM Plex Mono, monospace' }, svg); t.textContent = lab;
        if (i < N) for (let m = 1; m < this.o.minor; m++) { const am = a + 270 / N * m / this.o.minor; const [p0, q0] = polar(c, c, rT, am), [p1, q1] = polar(c, c, rT - 4, am); el('line', { x1: p0, y1: q0, x2: p1, y2: q1, stroke: 'rgba(233,226,208,0.6)', 'stroke-width': 0.8 }, svg); }
      }
      const L = el('text', { x: c, y: c + R * 0.5, 'text-anchor': 'middle', fill: 'rgba(233,226,208,0.75)', 'font-size': 6.5, 'letter-spacing': 1, 'font-family': 'IBM Plex Mono, monospace' }, svg); L.textContent = this.o.label.toUpperCase();
      this.read = el('text', { x: c, y: c + R * 0.72, 'text-anchor': 'middle', fill: '#f0a058', 'font-size': 9, 'font-family': 'IBM Plex Mono, monospace' }, svg);
      this.needle = el('g', { transform: `rotate(-135 ${c} ${c})` }, svg);
      el('polygon', { points: `${c - 1.6},${c + 8} ${c + 1.6},${c + 8} ${c + 0.5},${c - rT + 4} ${c - 0.5},${c - rT + 4}`, fill: '#f0a058' }, this.needle);
      el('circle', { cx: c, cy: c, r: 4.5, fill: '#2a2621', stroke: '#9a978f', 'stroke-width': 1.2 }, svg);
      el('ellipse', { cx: c - R * 0.3, cy: c - R * 0.45, rx: R * 0.45, ry: R * 0.22, fill: 'rgba(255,255,255,0.05)' }, svg);  // glass
      this.c = c; requestAnimationFrame(t => this.tick(t));
    }
    ang(v) { return -135 + 270 * clamp((v - this.o.min) / (this.o.max - this.o.min), 0, 1); }
    set(v, text) { this.v = v; if (text != null) this.read.textContent = text; }
    tick(t) {
      // a moving-coil needle: springy, slightly under-damped
      const dt = Math.min(0.05, (t - (this.last || t)) / 1000); this.last = t;
      const k = 60, d = 9; const a = k * (this.v - this.shown) - d * this.vel; this.vel += a * dt; this.shown += this.vel * dt;
      this.needle.setAttribute('transform', `rotate(${this.ang(this.shown).toFixed(2)} ${this.c} ${this.c})`);
      requestAnimationFrame(tt => this.tick(tt));
    }
  }
  Gauge.n = 0;

  /* ---- odometer: rolling digit drums ---- */
  class Counter {
    constructor(host, o) { this.o = Object.assign({ digits: 4, decimals: 0, prefix: '', suffix: '' }, o); this.host = host; host.classList.add('odo'); this.cells = []; this.build(); }
    build() {
      const h = this.host; h.innerHTML = '';
      if (this.o.prefix) { const p = document.createElement('span'); p.className = 'odo-sym'; p.textContent = this.o.prefix; h.appendChild(p); }
      const total = this.o.digits + this.o.decimals;
      for (let i = 0; i < total; i++) {
        if (i === this.o.digits && this.o.decimals) { const d = document.createElement('span'); d.className = 'odo-sym'; d.textContent = '.'; h.appendChild(d); }
        const cell = document.createElement('span'); cell.className = 'odo-cell' + (i >= this.o.digits ? ' dec' : ''); const strip = document.createElement('span'); strip.className = 'odo-strip'; strip.innerHTML = '0123456789'.split('').map(d => `<i>${d}</i>`).join(''); cell.appendChild(strip); h.appendChild(cell); this.cells.push(strip);
      }
      if (this.o.suffix) { const p = document.createElement('span'); p.className = 'odo-sym'; p.textContent = this.o.suffix; h.appendChild(p); }
    }
    set(v) {
      const s = Math.max(0, v).toFixed(this.o.decimals).replace('.', '').padStart(this.o.digits + this.o.decimals, '0').slice(-(this.o.digits + this.o.decimals));
      let lead = true;
      [...s].forEach((ch, i) => { const d = +ch; const strip = this.cells[i]; const blank = lead && d === 0 && i < this.o.digits - 1; if (!blank) lead = false; strip.style.transform = `translateY(${-d}em)`; strip.parentElement.classList.toggle('blank', blank); });
    }
  }

  /* ---- jewel lamp ---- */
  class Lamp {
    constructor(host, o) { this.o = Object.assign({ color: 'red', label: '' }, o); host.classList.add('lamp', this.o.color); host.innerHTML = `<i></i><span>${this.o.label}</span>`; this.host = host; }
    set(on, blink) { this.host.classList.toggle('on', !!on); this.host.classList.toggle('blink', !!blink); }
  }

  /* ---- rotary knob wrapping a range input: drag up/down or across, wheel, keyboard on the input ---- */
  class Knob {
    constructor(host, input, o) {
      this.o = Object.assign({ label: '', detents: 20, fmt: v => v }, o); this.host = host; this.input = input; host.classList.add('knob-wrap');
      host.innerHTML = `<div class="knob"><div class="knob-ticks"></div><div class="knob-cap"><i></i></div></div><div class="knob-label">${this.o.label}</div><output class="knob-out"></output>`;
      this.cap = host.querySelector('.knob-cap'); this.out = host.querySelector('.knob-out'); this.knob = host.querySelector('.knob');
      const ticks = host.querySelector('.knob-ticks'); for (let i = 0; i <= this.o.detents; i++) { const t = document.createElement('b'); t.style.transform = `rotate(${-135 + 270 * i / this.o.detents}deg)`; if (i % 5 === 0) t.className = 'major'; ticks.appendChild(t); }
      let drag = null;
      this.knob.addEventListener('pointerdown', e => { drag = { y: e.clientY, x: e.clientX, v: +input.value }; this.knob.setPointerCapture(e.pointerId); this.knob.classList.add('grab'); });
      this.knob.addEventListener('pointermove', e => { if (!drag) return; const range = +input.max - +input.min; const dv = ((drag.y - e.clientY) + (e.clientX - drag.x)) / 160 * range; this.setValue(drag.v + dv); });
      const up = () => { drag = null; this.knob.classList.remove('grab'); }; this.knob.addEventListener('pointerup', up); this.knob.addEventListener('pointercancel', up);
      this.knob.addEventListener('wheel', e => { e.preventDefault(); this.setValue(+input.value + (e.deltaY < 0 ? 1 : -1) * +input.step * 2); }, { passive: false });
      input.addEventListener('input', () => this.render());
      this.render();
    }
    setValue(v) { const i = this.input; const step = +i.step || 0.01; v = clamp(Math.round(v / step) * step, +i.min, +i.max); if (Math.abs(v - +i.value) < 1e-9) return; i.value = v.toFixed(4); i.dispatchEvent(new Event('input', { bubbles: true })); this.knob.classList.remove('click'); void this.knob.offsetWidth; this.knob.classList.add('click'); }
    render() { const i = this.input; const f = (+i.value - +i.min) / Math.max(1e-9, +i.max - +i.min); this.cap.style.transform = `rotate(${-135 + 270 * clamp(f, 0, 1)}deg)`; this.out.textContent = this.o.fmt(+i.value); }
    refresh() { this.render(); }
  }

  /* ---- toggle switch wrapping a button-like state ---- */
  class Toggle {
    constructor(host, o) { this.o = Object.assign({ label: '', on: 'ON', off: 'OFF' }, o); host.classList.add('toggle'); host.innerHTML = `<span class="tg-lab">${this.o.off}</span><div class="tg-track"><div class="tg-lever"></div></div><span class="tg-lab">${this.o.on}</span><div class="tg-name">${this.o.label}</div>`; this.host = host; this.state = false; host.addEventListener('click', () => { this.set(!this.state); this.o.onchange && this.o.onchange(this.state); }); }
    set(s) { this.state = !!s; this.host.classList.toggle('on', this.state); }
  }

  root.Instruments = { Gauge, Counter, Lamp, Knob, Toggle };
})(window);
