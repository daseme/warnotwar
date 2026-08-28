// Real-tape mode for labs 6 and 8: replay the dated 2026 record on
// rule-derived checkpoints. Loaded after shared.js, before page script.
//
// Red-team constraints encoded here:
// - Values after the selected vantage stay masked until the reader
//   commits and reveals; the chart axis scales to revealed data only.
//   (The full tape is one static JSON, so devtools can read ahead —
//   masking is a pedagogy device, not a secrecy device.)
// - Direction outcomes are reported neutrally and never graded; only
//   factual freeze-frame reads (verifiable at prediction time) score.
// - Peak markers are hindsight: drawn only at reveal, never origins.
// - Provenance lives inside the rendered chart in BOTH modes so a
//   cropped screenshot still says what it shows.
// - Vantage state keys by checkpoint date id and pins to the tape's
//   generated_at, so a weekly data update never silently moves a
//   reader's in-progress exercise.

function _tapeFromHash() {
  const m = location.hash.match(/[#&]t=([a-z]+)/);
  return m ? m[1] : null;
}
let tape = _tapeFromHash() || sessionStorage.getItem('hl.tape') || 'sim';
if (tape !== 'real') tape = 'sim';
window._tape = tape;

let TAPE = null;
let tapeUpdatedNote = false;

const TAPE_MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function tapeDay(iso) {
  const p = iso.split('-');
  return TAPE_MONTHS[+p[1] - 1] + ' ' + (+p[2]);
}
function tapeDayFull(iso) {
  return tapeDay(iso) + ', ' + iso.split('-')[0];
}

function tapePersist() {
  sessionStorage.setItem('hl.tape', tape);
  window._tape = tape;
  const h = location.hash.replace(/[#&]t=[a-z]+/, '').replace(/^#?&?/, '');
  history.replaceState(null, '', '#' + (h ? h + '&' : '') + 't=' + tape);
}

async function tapeLoad() {
  if (TAPE) return TAPE;
  const r = await fetch('/data/hormuz_checkpoints.json');
  if (!r.ok) throw new Error('checkpoint fetch failed: ' + r.status);
  TAPE = await r.json();
  const prevGen = sessionStorage.getItem('hl.tapeGen');
  if (prevGen && prevGen !== TAPE.generated_at_utc) tapeUpdatedNote = true;
  sessionStorage.setItem('hl.tapeGen', TAPE.generated_at_utc);
  return TAPE;
}

// vantage: which checkpoint the reader stands on, keyed by date id
function tapeVantageIdx() {
  const cps = TAPE.checkpoints;
  // a shared link can pin the vantage: #t=real&cp=3
  const m = location.hash.match(/[#&]cp=(\d+)/);
  if (m) return Math.min(+m[1], cps.length - 1);
  const saved = sessionStorage.getItem('hl.realCp');
  const i = cps.findIndex(c => c.id === saved);
  return i >= 0 ? i : 1;
}
function tapeClearVantagePin() {
  const h = location.hash.replace(/[#&]cp=\d+/, '');
  history.replaceState(null, '', h || '#');
}
function tapeSetVantage(i) {
  tapeClearVantagePin();
  sessionStorage.setItem('hl.realCp', TAPE.checkpoints[i].id);
}

function tapeReadEval(read, cp) {
  const v = cp[read.field];
  if (v === null || v === undefined) return null; // no reading published
  return read.op === 'lt' ? v < read.threshold : v > read.threshold;
}

function tapeAnnotationsBetween(a, b) {
  return (TAPE.annotations || []).filter(x => x.date > a.date && x.date <= b.date);
}

// mode toggle + chrome (banner, epilogue, tab title)
function renderTapeToggle(onChange) {
  const el = $('tape-toggle');
  if (!el) return;
  el.innerHTML = `<div class="mode-toggle">
    <button data-t="sim" class="${tape === 'sim' ? 'on' : ''}">Simulation</button>
    <button data-t="real" class="${tape === 'real' ? 'on' : ''}">Real tape — dated record</button>
  </div>${tape === 'real' && tapeUpdatedNote ? '<div class="tape-note">The tape has updated since your last visit — new checkpoints may have been added by the weekly data refresh.</div>' : ''}`;
  el.querySelectorAll('button').forEach(b => {
    b.onclick = async () => {
      if (b.dataset.t === tape) return;
      tape = b.dataset.t;
      tapePersist();
      if (tape === 'real') await tapeLoad();
      tapeChrome();
      renderTapeToggle(onChange);
      onChange();
    };
  });
}

function tapeChrome() {
  const b = document.querySelector('.series-banner');
  if (b) {
    if (tape === 'real' && TAPE) {
      const last = TAPE.checkpoints[TAPE.checkpoints.length - 1];
      b.classList.remove('sim');
      b.classList.add('real');
      b.textContent = 'Real record — updated weekly · latest observation ' + tapeDay(last.date);
      b.title = TAPE.revision_note;
    } else {
      b.classList.add('sim');
      b.classList.remove('real');
      b.textContent = SERIES.label;
      b.title = SERIES.note;
    }
  }
  const ep = document.querySelector('.sim-epilogue');
  if (ep) {
    if (!ep.dataset.simHtml) ep.dataset.simHtml = ep.innerHTML;
    if (tape === 'real' && TAPE) {
      const cps = TAPE.checkpoints;
      const atEnd = tapeVantageIdx() === cps.length - 1;
      if (!atEnd) {
        // no spoilers: the dated comparison waits until the reader has
        // walked the tape to its end
        ep.innerHTML = '<h4>The simulation is one script — you are stepping through the dated record</h4>' +
          '<p>Later checkpoints stay hidden until you stand on them. Walk the tape to its end to compare the two paths, or see the sourced current data at <a href="/oilflows.html">warnotwar.com/oilflows</a>.</p>';
      } else {
        const last = cps[cps.length - 1];
        const peaks = (TAPE.annotations || [])
          .map(a => `the ${a.label} of ${fmt$(a.value)} on ${tapeDay(a.date)} (${a.note})`)
          .join(' and ');
        ep.innerHTML = '<h4>The simulation is one script — this is the dated record</h4>' +
          `<p>In the simulation, a collapsed flow and a thin cushion send the price steadily higher. The record you just stepped through ran its own way: it contains ${peaks}, and by ${tapeDayFull(last.date)} Brent stood at ${fmt$(last.brent)}. Why it ran that way is an open question — bypass volumes, demand, strategic releases, and the official flow figures being accurate are all candidate explanations, laid out with their evidence on <a href="/oilflows.html">the oilflows page</a>.</p>`;
      }
    } else {
      ep.innerHTML = ep.dataset.simHtml;
    }
  }
  document.title = document.title
    .replace('(simulated scenario)', tape === 'real' ? '(real record)' : '(simulated scenario)');
  if (tape === 'sim') {
    document.title = document.title.replace('(real record)', '(simulated scenario)');
  } else {
    document.title = document.title.replace('(simulated scenario)', '(real record)');
  }
}

// date strip over checkpoints: values visible only up to the vantage
function renderTapeStrip(vi, onSelect) {
  const strip = $('date-strip');
  if (!strip) return;
  strip.innerHTML = TAPE.checkpoints.map((c, i) => {
    const masked = i > vi;
    return `<button class="date-pill${i === vi ? ' on' : ''}${masked ? ' masked' : ''}" data-idx="${i}" title="${masked ? 'later checkpoint — values hidden until you stand here' : c.why}"><span class="dp-label">${tapeDay(c.date)}</span><span class="dp-brent">${masked ? 'ahead' : 'Brent ' + fmt$(c.brent)}</span></button>`;
  }).join('');
  strip.querySelectorAll('.date-pill').forEach(b => {
    b.onclick = () => onSelect(+b.dataset.idx);
  });
}

// shared freeze-frame vocabulary for both labs
function tapeFieldCards(cp) {
  return [
    { key: 'flow', label: 'Flow', value: cp.hormuz === null ? 'no reading' : cp.hormuz,
      sub: 'Hormuz activity index', asof: cp.hormuz_asof },
    { key: 'buffer', label: 'Buffer', value: cp.buffer === null ? 'no reading' : cp.buffer + ' days',
      sub: 'U.S. crude cushion', asof: cp.buffer_week_end ? 'week ending ' + tapeDay(cp.buffer_week_end) : null },
    { key: 'brent', label: 'Brent', value: fmt$(cp.brent), sub: 'spot, last close', asof: cp.brent_asof },
    { key: 'bno', label: 'BNO', value: fmt$(cp.bno), sub: 'share price, last close', asof: cp.bno_asof },
  ];
}

function tapeSourcesLine(cp) {
  return `<div class="tape-src">As published by ${tapeDayFull(cp.date)} — each figure carries its own date. Flow and bypass: ${TAPE.sources.flow_and_bypass}. Buffer: ${TAPE.sources.buffer}. ${TAPE.revision_note}</div>`;
}

function tapeOutcomeLine(d, next) {
  const chg = (next.bno - d.bno) / d.bno * 100;
  return `BNO moved from ${fmt$(d.bno)} (${tapeDay(d.bno_asof)}) to ${fmt$(next.bno)} (${tapeDay(next.bno_asof)}) — <strong>${chg > 0 ? '+' : ''}${chg.toFixed(1)}%</strong> over the ${d.days_to_next} days between checkpoints.`;
}

const TAPE_DIRS = [
  { key: 'down10', label: '↓ more than 10%' },
  { key: 'down5', label: '↓ 0–10%' },
  { key: 'flat', label: 'roughly flat' },
  { key: 'up5', label: '↑ 0–10%' },
  { key: 'up10', label: '↑ more than 10%' },
];
function tapeDirLabel(key) {
  const d = TAPE_DIRS.find(x => x.key === key);
  return d ? d.label : key;
}
