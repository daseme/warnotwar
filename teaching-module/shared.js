// state: persisted per-tab and mirrored into the URL hash so a
// teacher can link a specific view (e.g. lab2-buffer.html#g=12&d=3)
function _fromHash(key) {
  const m = location.hash.match(new RegExp('[#&]' + key + '=(\\d+)'));
  return m ? +m[1] : null;
}
let grade = _fromHash('g') ?? +(sessionStorage.getItem('hl.grade') || 5);
let dateIdx = _fromHash('d') ?? +(sessionStorage.getItem('hl.dateIdx') ?? 2);
function persistState() {
  sessionStorage.setItem('hl.grade', grade);
  sessionStorage.setItem('hl.dateIdx', dateIdx);
  history.replaceState(null, '', '#g=' + grade + '&d=' + dateIdx);
}


const $ = id => document.getElementById(id);
const fmt$ = v => '$'+v.toFixed(2);
const pct = v => Math.round(v)+'%';

function figNum(it){ return it.lo===it.hi ? it.lo.toFixed(it.lo%1?1:0) : it.lo.toFixed(0)+'–'+it.hi.toFixed(0); }
function figText(it){ const u={mbd:'million barrels per day',tankers_per_night:'tankers per night',mbbl_single_day:'million barrels in one day'}; return figNum(it)+' '+u[it.unit]; }

function renderHeader() {
  const strip = $('date-strip');
  if (!strip) return;
  strip.innerHTML = dates.map((d,i) =>
    `<button class="date-pill${i===dateIdx?' on':''}" data-idx="${i}"><span class="dp-label">${d.label}</span><span class="dp-brent">Brent ${fmt$(d.brent)}</span></button>`
  ).join('');
  strip.querySelectorAll('.date-pill').forEach(b => {
    b.onclick = () => { dateIdx = +b.dataset.idx; persistState(); onDateChange(); };
  });
}

function renderGradeSwitch() {
  const el = $('grade-switch');
  if (!el) return;
  // initial state comes from persisted grade, never from hardcoded markup
  el.querySelectorAll('button').forEach(x => x.classList.toggle('on', +x.dataset.g === grade));
  el.querySelectorAll('button').forEach(b => {
    b.onclick = () => {
      grade = +b.dataset.g;
      el.querySelectorAll('button').forEach(x => x.classList.toggle('on', +x.dataset.g === grade));
      persistState();
      onGradeChange();
    };
  });
}

function renderLabNav() {
  const nav = $('lab-nav');
  if (!nav) return;
  const path = window.location.pathname;
  const current = path.split('/').pop() || 'index.html';
  const labs = [
    {file:'index.html', label:'Overview', num:''},
    {file:'lab1-flow.html', label:'Follow the Oil', num:'1'},
    {file:'lab2-buffer.html', label:'The Cushion', num:'2'},
    {file:'lab3-expectations.html', label:'Market Guesses', num:'3'},
    {file:'lab4-brent.html', label:'Meet Brent', num:'4'},
    {file:'lab5-bno.html', label:'Inside BNO', num:'5'},
    {file:'lab6-explain.html', label:'Explain This Day', num:'6'},
    {file:'lab7-story.html', label:'Story Mode', num:'7'},
    {file:'lab8-challenge.html', label:'Challenge', num:'8'},
  ];
  nav.innerHTML = labs.map(l => {
    const isActive = l.file === current;
    const label = l.num ? `${l.num}. ${l.label}` : l.label;
    return `<a href="${l.file}" class="lab-tab${isActive?' on':''}">${label}</a>`;
  }).join('');
}

document.addEventListener('keydown', (e) => {
  const path = window.location.pathname;
  const current = path.split('/').pop() || 'index.html';
  const isStory = current === 'lab7-story.html';
  if (isStory) {
    if (e.key === 'ArrowLeft' && typeof storyPrev === 'function') { e.preventDefault(); storyPrev(); }
    if (e.key === 'ArrowRight' && typeof storyNext === 'function') { e.preventDefault(); storyNext(); }
    if (e.key === ' ' && typeof storyPlay === 'function') { e.preventDefault(); storyPlay(); }
  } else {
    if (e.key === 'ArrowLeft' && dateIdx > 0) { dateIdx--; persistState(); onDateChange(); }
    if (e.key === 'ArrowRight' && dateIdx < dates.length - 1) { dateIdx++; persistState(); onDateChange(); }
  }
});

function renderSeriesBanner() {
  const header = document.querySelector('.site-header-inner');
  if (!header || typeof SERIES === 'undefined' || document.querySelector('.series-banner')) return;
  const b = document.createElement('div');
  b.className = 'series-banner' + (SERIES.kind === 'simulation' ? ' sim' : '');
  b.textContent = SERIES.label;
  b.title = SERIES.note;
  header.appendChild(b);
}

function renderEpilogue() {
  const page = (location.pathname.split('/').pop() || '');
  if (!['lab6-explain.html', 'lab7-story.html', 'lab8-challenge.html'].includes(page)) return;
  if (document.querySelector('.sim-epilogue')) return;
  const host = document.querySelector('main') || document.body;
  const div = document.createElement('div');
  div.className = 'detail-panel sim-epilogue';
  div.innerHTML = '<h4>This scenario is one path — the real 2026 took another</h4>' +
    '<p>In this simulation, a collapsed flow and a thin cushion send the price steadily higher. ' +
    'The live record did not follow that script. Compare it against the sourced, current data at ' +
    '<a href="/oilflows.html">warnotwar.com/oilflows</a> — explaining prices is hard, and that is the lesson.</p>';
  host.appendChild(div);
}

function initShared() {
  renderGradeSwitch();
  renderLabNav();
  renderHeader();
  renderSeriesBanner();
  renderEpilogue();
}

function onDateChange() { renderHeader(); }
function onGradeChange() {}

// one boot path for every page: define onPageInit() in the page script
function _boot() {
  initShared();
  if (typeof onPageInit === 'function') onPageInit();
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _boot);
} else {
  _boot();
}
