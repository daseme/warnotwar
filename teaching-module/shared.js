let grade = 5, dateIdx = 2;

const dates = [
  { id:'feb23', label:'Feb 23', brent:71.90, bno:32.15, hormuz:123, buffer:58, news:'Normal traffic', yanbu:105, fujairah:98 },
  { id:'mar02', label:'Mar 2',  brent:77.24, bno:34.80, hormuz:72,  buffer:55, news:'Traffic falling', yanbu:118, fujairah:85 },
  { id:'mar07', label:'Mar 7',  brent:95.74, bno:43.95, hormuz:2.8, buffer:42, news:'Near-total halt', yanbu:137, fujairah:62 },
  { id:'mar12', label:'Mar 12', brent:102.38,bno:47.20, hormuz:0.9, buffer:40, news:'Still blocked',   yanbu:142, fujairah:55 },
  { id:'apr07', label:'Apr 7',  brent:138.21,bno:62.50, hormuz:8,   buffer:38, news:'Partial reopen',  yanbu:125, fujairah:78 },
];

const items = [
  { id:'c1', speaker:'U.S. officials', date:'2026-03-07', lo:9, hi:10, unit:'mbd', scope:'hormuz_outbound', period:'unspecified', commodity:'unspecified', evidence:'government_estimate', quote:'Approximately 9 to 10 million barrels per day of oil flow through the Strait of Hormuz', source:'Reuters', url:'#', kind:'claim', attribution:'anonymous' },
  { id:'c2', speaker:'Commercial trackers', date:'2026-03-07', lo:4.5, hi:5.5, unit:'mbd', scope:'hormuz_outbound', period:'seven_day_average', commodity:'crude_condensate', evidence:'commercial_tracker_model', quote:'Model-based estimate of Hormuz outbound crude plus condensate', source:'Kpler/Vortexa', url:'#', kind:'estimate', attribution:'named' },
  { id:'c3', speaker:'PortWatch', date:'2026-03-07', lo:2.8, hi:2.8, unit:'tankers_per_night', scope:'ship_transits_in_and_out', period:'nightly', commodity:'unspecified', evidence:'activity_index', quote:'AIS-visible tanker transits through Hormuz corridor', source:'World Bank', url:'#', kind:'claim', attribution:'named' },
  { id:'c4', speaker:'Analyst, Axios', date:'2026-03-07', lo:15, hi:15, unit:'mbbl_single_day', scope:'hormuz_outbound', period:'single_day', commodity:'all_liquids', evidence:'government_estimate', quote:'15 million barrels moved on March 6', source:'Axios', url:'#', kind:'claim', attribution:'named' },
];

const SCOPE = { hormuz_outbound:'through the Strait of Hormuz only', regional_total_including_bypass:'the whole region, including bypass pipelines', ship_transits_in_and_out:'ship movements at the strait, in both directions' };
const WINDOW = { seven_day_average:'a 7-day average', single_day:'one single day', nightly:'per night', unspecified:'the speaker did not state a time window' };
const COMM = { crude:'crude oil', crude_condensate:'crude oil plus condensate', all_liquids:'all petroleum liquids', unspecified:'oil flow — commodity not stated' };
const EVIDENCE = { government_estimate:'U.S. government estimate — underlying observations not public', commercial_tracker_model:'commercial tracker model — reaches us secondhand via press', activity_index:'ship-signal activity index — never barrels' };

const storyChapters = [
  {label:'Feb 23',title:'The Calm Before',subtitle:'Tanker traffic through Hormuz is normal. The market is relaxed.',brent:71.90,bno:32.15,hormuz:123,buffer:58,news:'Normal traffic',yanbu:105,fujairah:98,signals:[{icon:'🚢',title:'Hormuz traffic',desc:'Visible tanker transits at baseline levels',value:'123%',color:'rgba(63,185,80,0.15)',textColor:'#3fb950'},{icon:'🛢️',title:'Oil cushion',desc:'U.S. combined stocks at comfortable levels',value:'58 days',color:'rgba(63,185,80,0.15)',textColor:'#3fb950'},{icon:'📰',title:'News',desc:'No significant supply disruptions reported',value:'Calm',color:'rgba(255,255,255,0.06)',textColor:'var(--text-secondary)'}]},
  {label:'Mar 2',title:'The First Rattle',subtitle:'Traffic starts falling. Traders begin to notice.',brent:77.24,bno:34.80,hormuz:72,buffer:55,news:'Traffic falling',yanbu:118,fujairah:98,signals:[{icon:'🚢',title:'Hormuz traffic',desc:'Visible transits down sharply from baseline',value:'72%',color:'rgba(210,153,34,0.15)',textColor:'#d29922'},{icon:'🛢️',title:'Oil cushion',desc:'Still adequate but starting to thin',value:'55 days',color:'rgba(210,153,34,0.15)',textColor:'#d29922'},{icon:'📰',title:'News',desc:'Reports of escalating tensions in the Gulf',value:'Concern',color:'rgba(210,153,34,0.15)',textColor:'#d29922'}]},
  {label:'Mar 7',title:'The Halt',subtitle:'Hormuz traffic collapses. The market prices in catastrophe.',brent:95.74,bno:43.95,hormuz:2.8,buffer:42,news:'Near-total halt',yanbu:137,fujairah:62,signals:[{icon:'🚢',title:'Hormuz traffic',desc:'Near-total collapse of visible transits',value:'2.8%',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},{icon:'🛢️',title:'Oil cushion',desc:'Below 5-year average. System is tight.',value:'42 days',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},{icon:'📰',title:'News',desc:'U.S. claims 9-10 mb/d still flowing. Trackers see ~5.',value:'Crisis',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},{icon:'🔄',title:'Bypass routes',desc:'Yanbu and Fujairah increasing but insufficient',value:'+37%',color:'rgba(88,166,255,0.15)',textColor:'#58a6ff'}]},
  {label:'Mar 12',title:'The Standstill',subtitle:'The strait is effectively closed. Prices keep climbing.',brent:102.38,bno:47.20,hormuz:0.9,buffer:40,news:'Still blocked',yanbu:142,fujairah:55,signals:[{icon:'🚢',title:'Hormuz traffic',desc:'Effectively zero visible transits',value:'0.9%',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},{icon:'🛢️',title:'Oil cushion',desc:'Critically low. Markets pricing sustained scarcity.',value:'40 days',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},{icon:'📰',title:'News',desc:'Military escort operations announced. No reopening in sight.',value:'Severe',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},{icon:'🔄',title:'Bypass routes',desc:'Maxed out. Cannot replace Hormuz volumes.',value:'Max',color:'rgba(88,166,255,0.15)',textColor:'#58a6ff'}]},
  {label:'Apr 7',title:'The Peak',subtitle:'Partial reopening begins, but the damage to price is done.',brent:138.21,bno:62.50,hormuz:8,buffer:38,news:'Partial reopen',yanbu:125,fujairah:78,signals:[{icon:'🚢',title:'Hormuz traffic',desc:'Minimal traffic resuming. Very slow recovery.',value:'8%',color:'rgba(210,153,34,0.15)',textColor:'#d29922'},{icon:'🛢️',title:'Oil cushion',desc:'Depleted. Takes months to rebuild.',value:'38 days',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},{icon:'📰',title:'News',desc:'Diplomatic talks underway. Market remains skeptical.',value:'Tense',color:'rgba(210,153,34,0.15)',textColor:'#d29922'},{icon:'📈',title:'Brent peak',desc:'Highest price since the crisis began.',value:'$138.21',color:'rgba(248,81,73,0.15)',textColor:'#f85149'}]}
];

const chalReasonsList = [
  {key:'flow',label:'Hormuz disruption is severe',correct:d=>d.hormuz<15},
  {key:'bypass',label:'Bypass routes are compensating',correct:d=>d.yanbu>120},
  {key:'buffer',label:'Inventories are dangerously low',correct:d=>d.buffer<45},
  {key:'expect',label:'Market is pricing in sustained scarcity',correct:d=>d.hormuz<20&&d.buffer<50},
  {key:'brent',label:'Brent has already moved sharply',correct:d=>d.brent>90},
  {key:'calm',label:'The situation is stabilizing',correct:d=>d.hormuz>50}
];

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
    b.onclick = () => { dateIdx = +b.dataset.idx; onDateChange(); };
  });
}

function renderGradeSwitch() {
  const el = $('grade-switch');
  if (!el) return;
  el.querySelectorAll('button').forEach(b => {
    b.onclick = () => {
      grade = +b.dataset.g;
      el.querySelectorAll('button').forEach(x => x.classList.toggle('on', +x.dataset.g === grade));
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
    if (e.key === 'ArrowLeft' && dateIdx > 0) { dateIdx--; onDateChange(); }
    if (e.key === 'ArrowRight' && dateIdx < dates.length - 1) { dateIdx++; onDateChange(); }
  }
});

function initShared() {
  renderGradeSwitch();
  renderLabNav();
  renderHeader();
}

function onDateChange() { renderHeader(); }
function onGradeChange() {}